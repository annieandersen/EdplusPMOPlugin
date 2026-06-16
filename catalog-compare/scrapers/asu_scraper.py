#!/usr/bin/env python3
"""
ASU Course Catalog Scraper.

Authentication: ASU's class-search SPA sends `Authorization: Bearer null` for
anonymous searches and the catalog API accepts it. This is what the SPA itself
does when no user session is established, so we mirror that. No OAuth dance is
needed for the public search endpoints.

Strategy:
  1. Pull the subject list for the primary term (STRM 2261, Spring 2026).
  2. For each subject, page through `/search/courses?term=2261&subject=X` with
     pageSize=200. These are the canonical course records for that term.
  3. For each subject, hit `/search/classes?term=2261&subject=X&campusOrOnlineSelection=O`
     and again for STRM 2264 (Summer 2026) to collect the set of
     (subject, catalogNbr) pairs that are currently offered online. That gets
     merged onto the course records as `modality_online_2261`,
     `modality_online_2264`, and the union into `offered_online`.
  4. Dedupe by (SUBJECT, CATALOGNBR) — ASU sometimes has multiple catalog rows
     for the same course (different campus offer numbers). Their CRSEIDs match,
     the descriptive fields are identical; the only thing that differs is
     CAMPUS. We merge into a `campuses` list and keep the first row's data as
     the base, with `raw` preserving every underlying row.

Output:
  Appended to `asu_courses.jsonl` one JSON object per unique course.
  Checkpointing: the script scans the existing file for subjects already fully
  processed and skips those on resume.

Rate limit: 3 req/sec with 50-200ms jitter, exponential backoff on 429/503,
honor Retry-After.
"""

from __future__ import annotations

import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


API_BASE = "https://eadvs-cscc-catalog-api.apps.asu.edu/catalog-microservices/api/v1"
PRIMARY_TERM = "2261"   # Spring 2026 per /search/terms
ONLINE_UNION_TERMS = ["2261", "2264"]  # Spring 2026 + Summer 2026
CATALOG_YEAR = "2025-2026"
USER_AGENT = "ASU-UTK-Catalog-Comparison-Research/1.0 (contact: apratlif@asu.edu)"

DATA_DIR = Path("/Users/apratlif/Documents/PM Skills/catalog-compare/data")
OUTPUT_FILE = DATA_DIR / "asu_courses.jsonl"
LOG_FILE = DATA_DIR / "asu_scraper.log"

REQUESTS_PER_SEC = 3.0
MIN_JITTER_S = 0.05
MAX_JITTER_S = 0.20
MAX_RETRIES = 5
PAGE_SIZE = 200


def setup_logging() -> logging.Logger:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("asu_scraper")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    # Clear any prior handlers if re-run in same interpreter.
    logger.handlers.clear()
    fh = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


@dataclass
class RateLimiter:
    """Simple token-bucket-ish pacing at N req/sec with per-call jitter."""
    rate_per_sec: float
    _last: float = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        interval = 1.0 / self.rate_per_sec
        gap = now - self._last
        if gap < interval:
            time.sleep(interval - gap)
        time.sleep(random.uniform(MIN_JITTER_S, MAX_JITTER_S))
        self._last = time.monotonic()


class ASUClient:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Origin": "https://catalog.apps.asu.edu",
            "Referer": "https://catalog.apps.asu.edu/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": "Bearer null",  # What the SPA sends pre-login.
        })
        self.limiter = RateLimiter(REQUESTS_PER_SEC)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{API_BASE}{path}"
        for attempt in range(MAX_RETRIES):
            self.limiter.wait()
            try:
                r = self.session.get(url, params=params, timeout=60)
            except requests.RequestException as exc:
                wait = (2 ** attempt) + random.random()
                self.logger.warning(f"Network error on {path} {params}: {exc}. Retrying in {wait:.1f}s")
                time.sleep(wait)
                continue
            if r.status_code in (429, 503):
                retry_after = r.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else (2 ** attempt)
                self.logger.warning(f"{r.status_code} on {path} {params}. Backing off {wait:.1f}s (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            if r.status_code == 401:
                # The SPA uses 'Bearer null' anonymously; if the API ever stops
                # honoring that we need a new approach. Log and raise.
                raise RuntimeError(f"401 Unauthorized on {url}. The anonymous 'Bearer null' auth was rejected; approach must be revisited.")
            if r.status_code >= 500:
                wait = 2 ** attempt
                self.logger.warning(f"{r.status_code} on {path}. Retrying in {wait:.1f}s")
                time.sleep(wait)
                continue
            if not r.ok:
                raise RuntimeError(f"HTTP {r.status_code} on {url}: {r.text[:200]}")
            try:
                return r.json()
            except ValueError:
                raise RuntimeError(f"Non-JSON response on {url}: {r.text[:200]}")
        raise RuntimeError(f"Exhausted retries on {path} {params}")

    def terms(self) -> list[dict]:
        return self.get("/search/terms").get("fullList", [])

    def subjects(self, term: str) -> list[str]:
        data = self.get(f"/search/subjects", params={"term": term})
        # Response groups by acad-group code; flatten to unique SUBJECT list.
        seen: set[str] = set()
        for _group, subs in (data or {}).items():
            if not isinstance(subs, list):
                continue
            for s in subs:
                code = s.get("SUBJECT")
                if code:
                    seen.add(code)
        return sorted(seen)

    def courses(self, term: str, subject: str) -> list[dict]:
        """Page through /search/courses and return all hit _source dicts."""
        out: list[dict] = []
        page = 1
        while True:
            data = self.get("/search/courses", params={
                "term": term,
                "subject": subject,
                "pageSize": PAGE_SIZE,
                "page": page,
            })
            hits = data.get("hits") or []
            out.extend(hits)
            total_obj = data.get("total")
            total = total_obj.get("value") if isinstance(total_obj, dict) else total_obj
            if total is None:
                break
            if len(out) >= total or not hits:
                break
            page += 1
            if page > 200:  # safety: 40k rows max per subject
                self.logger.warning(f"Hit page safety cap for {subject}")
                break
        return out

    def online_classes(self, term: str, subject: str) -> list[dict]:
        """Return the list of online class offerings for this (term, subject)."""
        data = self.get("/search/classes", params={
            "term": term,
            "subject": subject,
            "campusOrOnlineSelection": "O",
            "pageSize": PAGE_SIZE,
            "page": 1,
        })
        # The classes endpoint wraps hits differently: {hits: {total, hits: [...]}}
        inner = data.get("hits")
        if isinstance(inner, dict):
            return inner.get("hits") or []
        if isinstance(inner, list):
            return inner
        return []


# -------------------- normalization --------------------

CAREER_FROM_CATALOG_NUMBER = {
    # ASU: 100-499 undergrad, 500-599 shared grad/ugrd graduate numbers, 600+ grad.
    # 700s are doctoral; 800s/900s rare/non-credit.
}


def parse_int(s: Any) -> int | None:
    try:
        if s is None or s == "":
            return None
        return int(float(str(s)))
    except (ValueError, TypeError):
        return None


def infer_career_and_level(catalog_nbr: str) -> tuple[str, str]:
    """Return (career_code, level). ASU convention by first digit of catalog num."""
    digits = "".join(ch for ch in (catalog_nbr or "") if ch.isdigit())
    if not digits:
        return ("OTHER", "other")
    n = int(digits)
    if n < 500:
        return ("UGRD", "undergrad")
    if n < 800:
        return ("GRAD", "grad")
    return ("OTHER", "other")


def credits_display(cmin: int | None, cmax: int | None) -> str:
    if cmin is None and cmax is None:
        return ""
    if cmin == cmax:
        return str(cmin)
    return f"{cmin}-{cmax}"


def parse_gen_studies(descr4: str) -> list[dict]:
    """RQMNTDESIGNTN/DESCR4 encodes general studies designations. We emit a
    best-effort list of {code, label} for each token separated by ' & ' or ' OR '.
    If we can't map the code we still emit it with code==label."""
    if not descr4:
        return []
    # Common ASU general studies codes (short -> label). Gold = ASU's current
    # framework (introduced 2024). This is a best-effort mapping; downstream
    # normalization can enrich it.
    gold_labels = {
        "HUAD": "Humanities, Arts and Design",
        "SBS": "Social-Behavioral Sciences",
        "SB": "Social-Behavioral Sciences",
        "SQ": "Scientific Thinking in Natural Sciences",
        "SG": "Science, Quantitative Reasoning",
        "MA": "Mathematics",
        "QTRS": "Quantitative Reasoning",
        "CS": "Communication",
        "L": "Literacy and Critical Inquiry",
        "HU": "Humanities",
        "H": "Historical Awareness",
        "G": "Global Awareness",
        "C": "Cultural Diversity in the US",
    }
    tokens = [t.strip() for chunk in descr4.replace(" OR ", "&").split("&") for t in chunk.split(",") if t.strip()]
    out = []
    seen = set()
    for tok in tokens:
        tok_up = tok.upper()
        if tok_up in seen:
            continue
        seen.add(tok_up)
        out.append({"code": tok_up, "label": gold_labels.get(tok_up, tok_up)})
    return out


def normalize_course(source: dict, raw_rows: list[dict], online_map: dict[str, set[str]]) -> dict:
    """Build one canonical JSONL record from one _source and extra rows."""
    subject = source.get("SUBJECT") or ""
    catalog_nbr = source.get("CATALOGNBR") or ""
    course_code = f"{subject} {catalog_nbr}".strip()

    cmin = parse_int(source.get("UNITSMINIMUM"))
    cmax = parse_int(source.get("UNITSMAXIMUM"))
    career, level = infer_career_and_level(catalog_nbr)

    campuses = sorted({(r.get("CAMPUS") or "").strip() for r in raw_rows if r.get("CAMPUS")})

    key = f"{subject} {catalog_nbr}"
    online_2261 = key in online_map.get("2261", set())
    online_2264 = key in online_map.get("2264", set())
    offered_online = online_2261 or online_2264

    # ASU doesn't split gold vs maroon (legacy) in the course record; we emit the
    # same list under both keys to keep downstream parsers happy.
    gs = parse_gen_studies(source.get("DESCR4") or source.get("DESCRFORMAL") or "")

    # source_url: point back to the public catalog search for this course.
    source_url = (
        "https://catalog.apps.asu.edu/catalog/courses/courses?"
        f"acadCareer={career}&subject={subject}&catalogNbr={catalog_nbr}"
    )

    if offered_online:
        campuses_out = sorted(set(campuses) | {"ASUONLINE"})
    else:
        campuses_out = campuses

    record = {
        "school": "ASU",
        "catalog_year": CATALOG_YEAR,
        "subject": subject,
        "catalog_number": catalog_nbr,
        "course_code": course_code,
        "title": source.get("COURSETITLELONG") or source.get("CATDESCR") or "",
        "description": source.get("DESCRLONG") or "",
        "credits_min": cmin,
        "credits_max": cmax,
        "credits_display": credits_display(cmin, cmax),
        "career": career,
        "level": level,
        "college": source.get("GRPDESCR") or "",
        "department": source.get("ORGDESCR") or source.get("ORGDESCRFORMAL") or "",
        "prerequisites_text": source.get("RQDESCR") or "",
        "corequisites_text": "",  # not broken out by the API; lives in RQDESCR prose
        "cross_listed": "",       # not in this endpoint
        "repeatability": (
            f"repeatable; up to {source.get('UNITSREPEATLIMIT')} units / "
            f"{source.get('CRSEREPEATLIMIT')} times"
            if (source.get("CRSEREPEATABLE") == "Y")
            else ("not repeatable" if source.get("CRSEREPEATABLE") == "N" else "")
        ),
        "grading_basis": source.get("GRADINGBASISDESCR") or "",
        "modality_online_2261": online_2261,
        "modality_online_2264": online_2264,
        "offered_online": offered_online,
        "general_studies_gold": gs,
        "general_studies_maroon": gs,  # ASU's API doesn't differentiate here.
        "campuses": campuses_out,
        "source_url": source_url,
        "raw": {"rows": raw_rows},
    }
    return record


# -------------------- main orchestrator --------------------

def scan_existing_subjects(path: Path) -> set[str]:
    """If the output file exists, return the set of subjects already present.

    Resume means: skip subjects where we already wrote at least one course.
    This is coarse but safe — we're writing subjects one batch at a time so a
    partially-written subject rerun only produces idempotent duplicates we
    tolerate (downstream dedupes on course_code)."""
    if not path.exists():
        return set()
    done: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            subj = rec.get("subject")
            if subj:
                done.add(subj)
    return done


def dedupe_rows_by_course(rows: list[dict]) -> list[tuple[dict, list[dict]]]:
    """Group raw hits by (SUBJECT, CATALOGNBR). Returns [(primary_row, all_rows)]."""
    groups: dict[str, list[dict]] = {}
    for h in rows:
        src = h.get("_source") or h
        key = f"{src.get('SUBJECT','')}-{src.get('CATALOGNBR','')}"
        groups.setdefault(key, []).append(src)
    out: list[tuple[dict, list[dict]]] = []
    for key, rs in groups.items():
        # Pick the row with the latest EFFDT as canonical.
        rs_sorted = sorted(rs, key=lambda r: r.get("EFFDT") or "", reverse=True)
        out.append((rs_sorted[0], rs))
    return out


def build_online_map(client: ASUClient, subject: str, logger: logging.Logger) -> dict[str, set[str]]:
    """For a given subject, collect (subject, catalogNbr) online offerings
    across each term in ONLINE_UNION_TERMS. Keys are 'SUBJECT CATALOGNBR' strings."""
    out: dict[str, set[str]] = {t: set() for t in ONLINE_UNION_TERMS}
    for term in ONLINE_UNION_TERMS:
        try:
            rows = client.online_classes(term, subject)
        except Exception as exc:
            logger.warning(f"online_classes failed for {subject}/{term}: {exc}")
            continue
        for h in rows:
            src = h.get("_source") or h
            subj = src.get("SUBJECT") or ""
            cat = src.get("CATALOGNBR") or ""
            loc = (src.get("LOCATION") or "").upper()
            # API's `O` filter already restricts to online, but double-check on LOCATION.
            if subj and cat and ("ASUONLINE" in loc or loc == "" or "ONLINE" in loc):
                out[term].add(f"{subj} {cat}")
    return out


def main() -> int:
    logger = setup_logging()
    start = time.time()
    logger.info("==== ASU catalog scrape starting ====")
    logger.info(f"Output: {OUTPUT_FILE}")

    client = ASUClient(logger)
    # Sanity: confirm terms endpoint works (validates auth).
    terms = client.terms()
    logger.info(f"Auth OK. API returned {len(terms)} terms. Primary={PRIMARY_TERM}, online-union={ONLINE_UNION_TERMS}")

    subjects = client.subjects(PRIMARY_TERM)
    logger.info(f"Subjects for term {PRIMARY_TERM}: {len(subjects)}")

    done_subjects = scan_existing_subjects(OUTPUT_FILE)
    if done_subjects:
        logger.info(f"Resuming: {len(done_subjects)} subjects already on disk.")

    total_courses = 0
    online_courses = 0
    failed_subjects: list[str] = []
    out_f = OUTPUT_FILE.open("a", encoding="utf-8")

    try:
        for i, subject in enumerate(subjects, start=1):
            if subject in done_subjects:
                logger.info(f"[{i}/{len(subjects)}] {subject} — skip (already done)")
                continue

            attempts = 0
            rows: list[dict] | None = None
            while attempts < 3 and rows is None:
                try:
                    rows = client.courses(PRIMARY_TERM, subject)
                except Exception as exc:
                    attempts += 1
                    logger.warning(f"[{i}/{len(subjects)}] {subject} courses attempt {attempts} failed: {exc}")
                    time.sleep(2 * attempts)
            if rows is None:
                logger.error(f"[{i}/{len(subjects)}] {subject} — FAILED after 3 attempts; skipping")
                failed_subjects.append(subject)
                continue

            # Collect online-offering map for this subject, across Spring+Summer 2026.
            online_map = build_online_map(client, subject, logger)

            grouped = dedupe_rows_by_course(rows)
            subj_written = 0
            subj_online = 0
            for primary_src, all_rows in grouped:
                record = normalize_course(primary_src, all_rows, online_map)
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                subj_written += 1
                if record["offered_online"]:
                    subj_online += 1

            out_f.flush()
            os.fsync(out_f.fileno())
            total_courses += subj_written
            online_courses += subj_online
            logger.info(
                f"[{i}/{len(subjects)}] {subject} — {subj_written} courses "
                f"({subj_online} online). running total: {total_courses}"
            )
    finally:
        out_f.close()

    elapsed = time.time() - start
    logger.info("==== Done ====")
    logger.info(f"Total courses written (this run): {total_courses}")
    logger.info(f"Online courses (this run): {online_courses}")
    if failed_subjects:
        logger.warning(f"Failed subjects ({len(failed_subjects)}): {', '.join(failed_subjects)}")
    else:
        logger.info("No failed subjects.")
    logger.info(f"Elapsed: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
