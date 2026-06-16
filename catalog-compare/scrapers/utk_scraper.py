#!/usr/bin/env python3
"""UTK (University of Tennessee Knoxville) Catalog Scraper.

Scrapes both undergraduate (catoid=56, 2026-2027) and graduate (catoid=55, 2025-2026)
course catalogs from the Acalog CMS at https://catalog.utk.edu.

Output: JSONL one course per line at catalog-compare/data/utk_courses.jsonl
Log:    catalog-compare/data/utk_scraper.log
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import requests
from bs4 import BeautifulSoup, NavigableString, Tag


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE = "https://catalog.utk.edu"
USER_AGENT = "ASU-UTK-Catalog-Comparison-Research/1.0 (contact: apratlif@asu.edu)"

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# Output path can be overridden via env var so we can run undergrad + grad
# in parallel to separate files and merge later.
OUTPUT_JSONL = Path(os.environ.get("UTK_OUTPUT_JSONL", str(DATA_DIR / "utk_courses.jsonl")))
LOG_FILE = Path(os.environ.get("UTK_LOG_FILE", str(DATA_DIR / "utk_scraper.log")))

CATALOGS = [
    {
        "catoid": 56,
        "navoid": 12117,
        "year": "2026-2027",
        "level": "undergrad",
    },
    {
        "catoid": 55,
        "navoid": 11833,
        "year": "2025-2026",
        "level": "grad",
    },
]

RATE_LIMIT_MIN = 0.5   # seconds between requests, lower bound
RATE_LIMIT_MAX = 0.9   # seconds between requests, upper bound
MAX_RETRIES = 3
CHECKPOINT_EVERY = 20

# VolCore / GenEd code -> full label
VOLCORE_LABELS = {
    "WC": "Written Communication",
    "OC": "Oral Communication",
    "QR": "Quantitative Reasoning",
    "AH": "Arts & Humanities",
    "AOC": "Applied Oral Communication",
    "AAH": "Applied Arts & Humanities",
    "NS": "Natural Sciences",
    "SS": "Social Sciences",
    "GCI": "Global Citizenship - International",
    "GCUS": "Global Citizenship - U.S.",
    "EI": "Engaged Inquiries",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def setup_logging() -> logging.Logger:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("utk_scraper")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


log = setup_logging()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    )
    adapter = requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=8)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def polite_sleep() -> None:
    time.sleep(random.uniform(RATE_LIMIT_MIN, RATE_LIMIT_MAX))


def fetch(session: requests.Session, url: str) -> Optional[str]:
    """GET with retry + exponential backoff. Returns HTML text or None."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.text
            log.warning("HTTP %s on %s (attempt %s)", resp.status_code, url, attempt)
        except requests.RequestException as exc:
            log.warning("Network error on %s (attempt %s): %s", url, attempt, exc)
        # backoff: 2, 4, 8s with jitter
        time.sleep((2 ** attempt) + random.uniform(0, 1))
    log.error("Giving up on %s after %s attempts", url, MAX_RETRIES)
    return None


# ---------------------------------------------------------------------------
# Listing page parsing
# ---------------------------------------------------------------------------

COURSE_CALL_RE = re.compile(r"showCourse\(\s*'(\d+)'\s*,\s*'(\d+)'")


def listing_url(catoid: int, navoid: int, page: int) -> str:
    # Mirrors what the site actually uses for pagination
    return (
        f"{BASE}/content.php?catoid={catoid}&navoid={navoid}"
        f"&filter%5Bitem_type%5D=3&filter%5Bonly_active%5D=1"
        f"&filter%5B3%5D=1&filter%5Bcpage%5D={page}"
        "#acalog_template_course_filter"
    )


def extract_total_pages(html: str) -> int:
    """Scan listing HTML for the highest cpage number referenced."""
    pages = set()
    for m in re.finditer(r"filter%5Bcpage%5D=(\d+)", html):
        pages.add(int(m.group(1)))
    for m in re.finditer(r"filter\[cpage\]=(\d+)", html):
        pages.add(int(m.group(1)))
    return max(pages) if pages else 1


def parse_listing_page(html: str) -> list[dict[str, Any]]:
    """Extract (coid, course_code, has_asterisk) from a listing page."""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict[str, Any]] = []
    # Every course entry is an <a> whose onclick contains showCourse('catoid','coid', ...)
    for a in soup.find_all("a", onclick=True):
        onclick = a.get("onclick") or ""
        m = COURSE_CALL_RE.search(onclick)
        if not m:
            continue
        coid = int(m.group(2))
        text = a.get_text(strip=True)
        # e.g. "ACCT 200 - Foundations of Accounting" or "ENGL 101* - English Composition I"
        has_asterisk = False
        course_code = None
        if " - " in text:
            head, _rest = text.split(" - ", 1)
            head = head.strip()
            has_asterisk = head.endswith("*")
            course_code = head
        else:
            course_code = text
            has_asterisk = course_code.endswith("*")
        results.append(
            {
                "coid": coid,
                "course_code_raw": course_code,  # may include asterisk
                "has_volcore_asterisk_listing": has_asterisk,
            }
        )
    # Deduplicate by coid preserving order
    seen = set()
    unique: list[dict[str, Any]] = []
    for row in results:
        if row["coid"] in seen:
            continue
        seen.add(row["coid"])
        unique.append(row)
    return unique


# ---------------------------------------------------------------------------
# Course detail parsing
# ---------------------------------------------------------------------------


# Fragment of the detail page we care about runs from <h1 id="course_preview_title">
# up to the print-friendly / back-to-top block.
DETAIL_START_RE = re.compile(
    r"<h1\s+id=['\"]course_preview_title['\"][^>]*>.*?(?=<br>\s*<hr>\s*<div style=\"float: right\")",
    re.S,
)


def extract_detail_fragment(html: str) -> Optional[str]:
    m = DETAIL_START_RE.search(html)
    if m:
        return m.group(0)
    # fallback: just start at h1
    idx = html.find("course_preview_title")
    if idx < 0:
        return None
    # Anchor on the actual h1 tag that holds the title
    h1_idx = html.rfind("<h1", 0, idx + 100)
    if h1_idx < 0:
        h1_idx = idx
    # cut at print link area or end of td
    end = html.find('<div style="float: right"', h1_idx)
    if end < 0:
        end = html.find("</td>", h1_idx)
    return html[h1_idx:end] if end > 0 else html[h1_idx : h1_idx + 4000]


CREDIT_RE = re.compile(
    # Credit display can be wrapped in <strong>NUMBER</strong> followed by
    # either "<em>Credit Hours</em>" (undergrad template) or
    # "<strong>Credit Hours</strong>" (grad template).
    r"<strong>([^<]+)</strong>\s*<(?:em|strong)>\s*Credit Hours\s*</(?:em|strong)>",
    re.I | re.S,
)


def parse_credits(display: str) -> tuple[Optional[float], Optional[float]]:
    """Given a credit-hours display string, return (min, max) as floats where possible."""
    if not display:
        return None, None
    s = display.strip()
    # range: "1-6", "3-4"
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$", s)
    if m:
        return float(m.group(1)), float(m.group(2))
    # single number
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*$", s)
    if m:
        v = float(m.group(1))
        return v, v
    # comma list: "1, 2, 3"
    nums = re.findall(r"\d+(?:\.\d+)?", s)
    if nums:
        vals = [float(n) for n in nums]
        return min(vals), max(vals)
    return None, None


VOLCORE_CODE_RE = re.compile(r"\b(WC|OC|QR|AH|AOC|AAH|NS|SS|GCI|GCUS|EI)\b")


def parse_volcore(value: str) -> Optional[dict[str, str]]:
    """Extract first VolCore code from value string like '(WC)' or 'WC, EI'."""
    if not value:
        return None
    m = VOLCORE_CODE_RE.search(value)
    if not m:
        return None
    code = m.group(1)
    return {"code": code, "label": VOLCORE_LABELS.get(code, code)}


# Labels (lowercased, trailing ':' optional) we recognize as field markers.
# We preserve the original label casing in raw_fields; this list just drives
# the structured output.
KNOWN_LABELS = {
    "credit hours",
    "satisfies volunteer core requirement",
    "satisfies general education requirement through the 2021-2022 academic catalog",
    "satisfies general education requirement through the 2021-2022 academic catalogue",
    "prerequisite",
    "prerequisites",
    "prerequisite(s)",
    "(re) prerequisite",
    "(re) prerequisite(s)",
    "(re) prerequisites",
    "corequisite",
    "corequisites",
    "corequisite(s)",
    "(de) corequisite",
    "(de) corequisite(s)",
    "(de) corequisites",
    "registration restriction",
    "registration restrictions",
    "registration restriction(s)",
    "repeatability",
    "cross-listed",
    "same as",
    "cross-listed with",
    "grading restriction",
    "credit restriction",
    "recommended background",
    "comment",
    "comments",
    "comment(s)",
    "contact hour distribution",
}


def _label_key(label: str) -> str:
    return label.strip().rstrip(":").strip().lower()


def parse_course_detail(html: str, catoid: int, coid: int) -> Optional[dict[str, Any]]:
    """Parse a preview_course_nopop.php HTML page into a structured dict."""
    fragment = extract_detail_fragment(html)
    if not fragment:
        return None

    soup = BeautifulSoup(fragment, "lxml")

    # -- Title / course code -------------------------------------------------
    h1 = soup.find("h1", id="course_preview_title")
    if not h1:
        return None
    title_text = h1.get_text(" ", strip=True)
    # Normalize non-breaking spaces, then split on " - "
    title_text = title_text.replace("\xa0", " ")
    title_text = re.sub(r"\s+", " ", title_text).strip()
    # e.g. "ENGL 101* - English Composition I"
    course_code_raw = title_text
    title = ""
    # Acalog uses " - " as separator (possibly after normalization)
    sep_match = re.search(r"\s+-\s+", title_text)
    if sep_match:
        course_code_raw = title_text[: sep_match.start()].strip()
        title = title_text[sep_match.end():].strip()
    has_asterisk = course_code_raw.endswith("*")
    course_code = course_code_raw.rstrip("*").strip()
    subj_match = re.match(r"^([A-Z][A-Z0-9&/ ]*?)\s+([0-9A-Za-z]+)$", course_code)
    if subj_match:
        subject = subj_match.group(1).strip()
        catalog_number = subj_match.group(2).strip()
    else:
        # Fallback split on last whitespace
        parts = course_code.rsplit(None, 1)
        if len(parts) == 2:
            subject, catalog_number = parts[0].strip(), parts[1].strip()
        else:
            subject, catalog_number = course_code, ""

    # -- Credits -------------------------------------------------------------
    credits_display = None
    cred_m = CREDIT_RE.search(fragment)
    if cred_m:
        credits_display = BeautifulSoup(cred_m.group(1), "lxml").get_text(" ", strip=True)
    credits_min, credits_max = parse_credits(credits_display or "")

    # -- Description + labeled fields ---------------------------------------
    # Strategy: operate on the fragment after the <hr> that follows credits.
    hr_idx = fragment.find("<hr>")
    after_hr = fragment[hr_idx + len("<hr>"):] if hr_idx >= 0 else fragment

    # Split the content on <br> so each logical line is its own chunk.
    # This mirrors how the Acalog template builds the page.
    chunks = re.split(r"<br\s*/?>", after_hr, flags=re.I)

    description_parts: list[str] = []
    raw_fields: dict[str, str] = {}
    labeled_started = False

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        chunk_soup = BeautifulSoup(chunk, "lxml")
        # Walk <em> / <strong> tags to find a non-empty label candidate.
        # Labels end with ':' (e.g. "Prerequisite(s):", "Grading Restriction:")
        # Values are sometimes themselves wrapped in <em>, so prefer labels
        # whose text ends with ':'.
        label_tag = None
        label_text = ""
        for tag in chunk_soup.find_all(["em", "strong"]):
            text = tag.get_text(" ", strip=True)
            if not text:
                continue
            if text.endswith(":") or "Requirement" in text and text.endswith(":"):
                label_tag = tag
                label_text = text
                break
            # First non-empty em may be the label even without colon in rare cases
            if label_tag is None:
                label_tag = tag
                label_text = text
        if label_tag is not None and label_text.endswith(":"):
            full_text = chunk_soup.get_text(" ", strip=True)
            full_text = full_text.replace("\xa0", " ")
            value = full_text
            # Try to remove label (with and without trailing colon) from the start
            for lv in (label_text, label_text.rstrip(":")):
                if value.startswith(lv):
                    value = value[len(lv):].lstrip(" :").strip()
                    break
            else:
                # Label not at start — e.g. prefixed by an empty <em> placeholder.
                # Split on first occurrence.
                idx_split = full_text.find(label_text)
                if idx_split >= 0:
                    value = full_text[idx_split + len(label_text):].lstrip(" :").strip()
            value = re.sub(r"\s+", " ", value).strip()
            # Strip trailing period if it's a single-sentence value
            clean_key = label_text.rstrip(":").strip()
            if clean_key:
                raw_fields[clean_key] = value
            labeled_started = True
            continue

        # No label candidate -> either description or a stray value line.
        if not labeled_started:
            text = chunk_soup.get_text(" ", strip=True).replace("\xa0", " ")
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                description_parts.append(text)

    description = " ".join(description_parts).strip() or None

    # -- Map raw fields to structured outputs --------------------------------
    def _raw_get(*keys: str) -> Optional[str]:
        for k in keys:
            for raw_k, raw_v in raw_fields.items():
                if _label_key(raw_k) == _label_key(k):
                    return raw_v
        return None

    volcore_raw = _raw_get("Satisfies Volunteer Core Requirement")
    volcore = parse_volcore(volcore_raw) if volcore_raw else None

    gened_legacy_raw = None
    for raw_k, raw_v in raw_fields.items():
        if "General Education Requirement" in raw_k:
            gened_legacy_raw = raw_v
            break

    prerequisites = _raw_get(
        "Prerequisite(s)",
        "Prerequisites",
        "Prerequisite",
        "(RE) Prerequisite(s)",
        "(RE) Prerequisites",
        "(RE) Prerequisite",
    )
    corequisites = _raw_get(
        "Corequisite(s)",
        "Corequisites",
        "Corequisite",
        "(DE) Corequisite(s)",
        "(DE) Corequisites",
        "(DE) Corequisite",
    )
    registration_restrictions = _raw_get(
        "Registration Restriction(s)",
        "Registration Restrictions",
        "Registration Restriction",
    )
    repeatability = _raw_get("Repeatability")
    cross_listed = _raw_get("Cross-listed", "Same as", "Cross-listed with")
    grading_restriction = _raw_get("Grading Restriction")
    credit_restriction = _raw_get("Credit Restriction")
    recommended_background = _raw_get("Recommended Background")
    comments = _raw_get("Comment(s)", "Comments", "Comment")

    return {
        "subject": subject,
        "catalog_number": catalog_number,
        "course_code": course_code,
        "course_code_raw": course_code_raw,
        "has_volcore_asterisk": has_asterisk,
        "title": title or None,
        "description": description,
        "credits_display": credits_display,
        "credits_min": credits_min,
        "credits_max": credits_max,
        "volcore_requirement": volcore,
        "gened_legacy": gened_legacy_raw,
        "prerequisites_text": prerequisites,
        "corequisites_text": corequisites,
        "registration_restrictions": registration_restrictions,
        "repeatability": repeatability,
        "cross_listed": cross_listed,
        "grading_restriction": grading_restriction,
        "credit_restriction": credit_restriction,
        "recommended_background": recommended_background,
        "comments": comments,
        "raw_html_snippet": fragment.strip(),
        "raw_fields": raw_fields,
    }


# ---------------------------------------------------------------------------
# Checkpoint / resume
# ---------------------------------------------------------------------------


def load_existing_coids() -> set[tuple[int, int]]:
    """Return {(catoid, coid), ...} already written in the output file."""
    seen: set[tuple[int, int]] = set()
    if not OUTPUT_JSONL.exists():
        return seen
    with OUTPUT_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                seen.add((int(obj["catoid"]), int(obj["coid"])))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    return seen


# ---------------------------------------------------------------------------
# Main scraping loop
# ---------------------------------------------------------------------------


def scrape_catalog(
    session: requests.Session,
    catoid: int,
    navoid: int,
    year: str,
    level: str,
    already: set[tuple[int, int]],
    out_handle,
    max_pages: Optional[int] = None,
    max_courses: Optional[int] = None,
) -> tuple[int, int, list[int]]:
    """Scrape one catalog. Returns (new_count, skipped_count, failed_coids)."""
    log.info("=== Catalog catoid=%s level=%s year=%s ===", catoid, level, year)

    # First page — pull pagination info and first batch of courses
    first_url = listing_url(catoid, navoid, 1)
    html = fetch(session, first_url)
    polite_sleep()
    if not html:
        log.error("Failed to fetch first listing page for catoid=%s", catoid)
        return 0, 0, []
    total_pages = extract_total_pages(html)
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    # Collect course pointers across all pages
    course_stubs: list[dict[str, Any]] = parse_listing_page(html)
    log.info("page 1 of %s (%s stubs)", total_pages, len(course_stubs))

    for page in range(2, total_pages + 1):
        url = listing_url(catoid, navoid, page)
        page_html = fetch(session, url)
        polite_sleep()
        if not page_html:
            log.error("Skipping page %s due to fetch failure", page)
            continue
        stubs = parse_listing_page(page_html)
        course_stubs.extend(stubs)
        log.info("page %s of %s (%s stubs, running total %s)", page, total_pages, len(stubs), len(course_stubs))

    # Deduplicate across pages (some paginators repeat the last item)
    seen = set()
    unique_stubs: list[dict[str, Any]] = []
    for s in course_stubs:
        if s["coid"] in seen:
            continue
        seen.add(s["coid"])
        unique_stubs.append(s)
    log.info("Catalog catoid=%s: %s unique course stubs to fetch", catoid, len(unique_stubs))

    new_count = 0
    skipped = 0
    failed: list[int] = []

    total = len(unique_stubs)
    for idx, stub in enumerate(unique_stubs, 1):
        coid = stub["coid"]
        key = (catoid, coid)
        if key in already:
            skipped += 1
            if idx % 100 == 0:
                log.info("[%s/%s] catoid=%s skipping already-captured coids", idx, total, catoid)
            continue
        if max_courses is not None and new_count >= max_courses:
            break

        url = f"{BASE}/preview_course_nopop.php?catoid={catoid}&coid={coid}"
        html = fetch(session, url)
        polite_sleep()
        if not html:
            log.error("coid %s fetch failed", coid)
            failed.append(coid)
            continue
        parsed = parse_course_detail(html, catoid, coid)
        if not parsed:
            log.error("coid %s parse failed", coid)
            failed.append(coid)
            continue

        record = {
            "school": "UTK",
            "catalog_year": year,
            "catoid": catoid,
            "coid": coid,
            "level": level,
            **parsed,
            "offered_online": None,
            "online_modality_note": (
                "Per-course online modality is not published in the UTK Acalog "
                "catalog; programs flagged as Distance Education are tracked separately."
            ),
            "source_url": url,
        }

        out_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        new_count += 1
        already.add(key)

        if new_count % CHECKPOINT_EVERY == 0:
            out_handle.flush()
            os.fsync(out_handle.fileno())

        log.info(
            "coid %s (%s/%s) %s%s",
            coid,
            idx,
            total,
            parsed.get("course_code_raw") or parsed.get("course_code"),
            " [VolCore]" if parsed.get("volcore_requirement") else "",
        )

    out_handle.flush()
    try:
        os.fsync(out_handle.fileno())
    except OSError:
        pass
    log.info("Catalog catoid=%s done: %s new, %s skipped, %s failed", catoid, new_count, skipped, len(failed))
    return new_count, skipped, failed


def main(argv: list[str]) -> int:
    limit_pages = None
    limit_courses = None
    only_level = None
    for arg in argv[1:]:
        if arg.startswith("--max-pages="):
            limit_pages = int(arg.split("=", 1)[1])
        elif arg.startswith("--max-courses="):
            limit_courses = int(arg.split("=", 1)[1])
        elif arg.startswith("--only="):
            only_level = arg.split("=", 1)[1].strip().lower()
        elif arg == "--smoke":
            limit_pages = 1
            limit_courses = 5

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    already = load_existing_coids()
    log.info("Existing records in output: %s", len(already))

    session = make_session()

    start = time.time()
    total_new = 0
    total_skip = 0
    all_failed: list[tuple[int, int]] = []

    with OUTPUT_JSONL.open("a", encoding="utf-8") as out:
        for cat in CATALOGS:
            if only_level and cat["level"] != only_level:
                continue
            new, skipped, failed = scrape_catalog(
                session,
                cat["catoid"],
                cat["navoid"],
                cat["year"],
                cat["level"],
                already,
                out,
                max_pages=limit_pages,
                max_courses=limit_courses,
            )
            total_new += new
            total_skip += skipped
            for f in failed:
                all_failed.append((cat["catoid"], f))

    duration = time.time() - start
    log.info(
        "DONE. new=%s skipped=%s failed=%s duration=%.1fs",
        total_new,
        total_skip,
        len(all_failed),
        duration,
    )
    if all_failed:
        log.warning("Failed coids: %s", all_failed)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
