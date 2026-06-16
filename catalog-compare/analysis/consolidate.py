"""Load ASU + UTK scraper JSONL output into a unified SQLite database.

Usage:
    python consolidate.py

Reads:
    ../data/asu_courses.jsonl
    ../data/utk_courses.jsonl

Writes:
    ../data/catalog.db
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
DB_PATH = DATA / "catalog.db"
ASU_JSONL = DATA / "asu_courses.jsonl"
# UTK scraper writes split files per level; fall back to combined if present.
UTK_JSONL_FILES = [
    DATA / "utk_courses_undergrad.jsonl",
    DATA / "utk_courses_grad.jsonl",
    DATA / "utk_courses.jsonl",
]


SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY,
    school TEXT NOT NULL,
    catalog_year TEXT,
    subject TEXT NOT NULL,
    catalog_number TEXT NOT NULL,
    course_code TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    credits_display TEXT,
    credits_min REAL,
    credits_max REAL,
    level TEXT,
    career TEXT,
    college TEXT,
    department TEXT,
    prerequisites_text TEXT,
    corequisites_text TEXT,
    cross_listed TEXT,
    repeatability TEXT,
    grading_basis TEXT,
    offered_online INTEGER,
    source_url TEXT,
    raw_json TEXT,
    UNIQUE (school, course_code, catalog_year)
);

CREATE INDEX IF NOT EXISTS idx_courses_school ON courses(school);
CREATE INDEX IF NOT EXISTS idx_courses_subject ON courses(subject);
CREATE INDEX IF NOT EXISTS idx_courses_level ON courses(level);
CREATE INDEX IF NOT EXISTS idx_courses_online ON courses(offered_online);

CREATE TABLE IF NOT EXISTS designations (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    system TEXT NOT NULL,
    code TEXT NOT NULL,
    label TEXT,
    FOREIGN KEY (course_id) REFERENCES courses(id)
);

CREATE INDEX IF NOT EXISTS idx_designations_course ON designations(course_id);
CREATE INDEX IF NOT EXISTS idx_designations_system_code ON designations(system, code);
"""


def parse_credits(raw) -> tuple[float | None, float | None, str | None]:
    if raw is None:
        return None, None, None
    if isinstance(raw, (int, float)):
        v = float(raw)
        return v, v, str(raw)
    s = str(raw).strip()
    if not s:
        return None, None, None
    m = re.search(r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1)), float(m.group(2)), s
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if m:
        v = float(m.group(1))
        return v, v, s
    return None, None, s


def insert_course(conn: sqlite3.Connection, row: dict) -> int | None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT OR IGNORE INTO courses (
                school, catalog_year, subject, catalog_number, course_code,
                title, description, credits_display, credits_min, credits_max,
                level, career, college, department,
                prerequisites_text, corequisites_text, cross_listed,
                repeatability, grading_basis, offered_online,
                source_url, raw_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                row["school"],
                row.get("catalog_year"),
                row["subject"],
                row["catalog_number"],
                row["course_code"],
                row.get("title") or "",
                row.get("description"),
                row.get("credits_display"),
                row.get("credits_min"),
                row.get("credits_max"),
                row.get("level"),
                row.get("career"),
                row.get("college"),
                row.get("department"),
                row.get("prerequisites_text"),
                row.get("corequisites_text"),
                row.get("cross_listed"),
                row.get("repeatability"),
                row.get("grading_basis"),
                1 if row.get("offered_online") else (0 if row.get("offered_online") is False else None),
                row.get("source_url"),
                json.dumps(row.get("raw") or row.get("raw_fields") or {}),
            ),
        )
        if cur.rowcount == 0:
            cur.execute(
                "SELECT id FROM courses WHERE school=? AND course_code=? AND catalog_year IS ?",
                (row["school"], row["course_code"], row.get("catalog_year")),
            )
            r = cur.fetchone()
            return r[0] if r else None
        return cur.lastrowid
    except Exception as e:
        print(f"  insert error for {row.get('course_code')}: {e}", file=sys.stderr)
        return None


def insert_designations(conn: sqlite3.Connection, course_id: int, designations: list[dict]):
    if not designations:
        return
    conn.executemany(
        "INSERT INTO designations (course_id, system, code, label) VALUES (?,?,?,?)",
        [(course_id, d["system"], d["code"], d.get("label")) for d in designations],
    )


def normalize_asu(row: dict) -> tuple[dict, list[dict]]:
    credits_min, credits_max, credits_display = (
        row.get("credits_min"),
        row.get("credits_max"),
        row.get("credits_display"),
    )
    if credits_display is None and credits_min is not None:
        credits_display = (
            str(int(credits_min)) if credits_min == credits_max else f"{credits_min}-{credits_max}"
        )

    out = {
        "school": "ASU",
        "catalog_year": row.get("catalog_year") or "2025-2026",
        "subject": row["subject"],
        "catalog_number": str(row["catalog_number"]),
        "course_code": row.get("course_code") or f"{row['subject']} {row['catalog_number']}",
        "title": row.get("title"),
        "description": row.get("description"),
        "credits_display": credits_display,
        "credits_min": credits_min,
        "credits_max": credits_max,
        "level": row.get("level"),
        "career": row.get("career"),
        "college": row.get("college"),
        "department": row.get("department"),
        "prerequisites_text": row.get("prerequisites_text"),
        "corequisites_text": row.get("corequisites_text"),
        "cross_listed": row.get("cross_listed"),
        "repeatability": row.get("repeatability"),
        "grading_basis": row.get("grading_basis"),
        "offered_online": row.get("offered_online"),
        "source_url": row.get("source_url"),
        "raw": row.get("raw") or row,
    }
    designations = []
    gold = row.get("general_studies_gold") or []
    maroon = row.get("general_studies_maroon") or []
    gold_keys = {(d.get("code"), d.get("label")) for d in gold}
    maroon_keys = {(d.get("code"), d.get("label")) for d in maroon}
    for d in gold:
        designations.append({"system": "ASU_GS_GOLD", "code": d.get("code", ""), "label": d.get("label")})
    # Only add Maroon entries that differ from Gold (ASU API currently returns
    # identical lists; dedupe to avoid inflating designation counts).
    for d in maroon:
        if (d.get("code"), d.get("label")) not in gold_keys:
            designations.append({"system": "ASU_GS_MAROON", "code": d.get("code", ""), "label": d.get("label")})
    return out, designations


def normalize_utk(row: dict) -> tuple[dict, list[dict]]:
    cmin, cmax, cdisp = parse_credits(row.get("credits_display") or row.get("credits"))
    if row.get("credits_min") is not None:
        cmin = row["credits_min"]
    if row.get("credits_max") is not None:
        cmax = row["credits_max"]

    out = {
        "school": "UTK",
        "catalog_year": row.get("catalog_year")
        or ("2026-2027" if row.get("catoid") == 56 else "2025-2026"),
        "subject": row["subject"],
        "catalog_number": str(row["catalog_number"]),
        "course_code": row.get("course_code") or f"{row['subject']} {row['catalog_number']}",
        "title": row.get("title"),
        "description": row.get("description"),
        "credits_display": cdisp,
        "credits_min": cmin,
        "credits_max": cmax,
        "level": row.get("level"),
        "career": None,
        "college": None,
        "department": None,
        "prerequisites_text": row.get("prerequisites_text"),
        "corequisites_text": row.get("corequisites_text"),
        "cross_listed": row.get("cross_listed"),
        "repeatability": row.get("repeatability"),
        "grading_basis": row.get("grading_restriction"),
        "offered_online": row.get("offered_online"),
        "source_url": row.get("source_url"),
        "raw": row.get("raw_fields") or row,
    }
    designations = []
    vc = row.get("volcore_requirement")
    if vc and isinstance(vc, dict) and vc.get("code"):
        designations.append({"system": "UTK_VOLCORE", "code": vc["code"], "label": vc.get("label")})
    gel = row.get("gened_legacy")
    if gel:
        m = re.search(r"\(([A-Z]{1,4})\)", gel)
        if m:
            designations.append({"system": "UTK_GENED_LEGACY", "code": m.group(1), "label": gel})
    return out, designations


def load_jsonl(path: Path):
    if not path.exists():
        print(f"  missing: {path}")
        return
    with path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  {path.name}:{ln} bad json: {e}", file=sys.stderr)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    print(f"Loading ASU from {ASU_JSONL}")
    n_asu, n_asu_des = 0, 0
    for row in load_jsonl(ASU_JSONL):
        norm, des = normalize_asu(row)
        cid = insert_course(conn, norm)
        if cid:
            insert_designations(conn, cid, des)
            n_asu += 1
            n_asu_des += len(des)
    conn.commit()

    n_utk, n_utk_des = 0, 0
    for utk_path in UTK_JSONL_FILES:
        if not utk_path.exists():
            continue
        print(f"Loading UTK from {utk_path}")
        for row in load_jsonl(utk_path):
            norm, des = normalize_utk(row)
            cid = insert_course(conn, norm)
            if cid:
                insert_designations(conn, cid, des)
                n_utk += 1
                n_utk_des += len(des)
        conn.commit()

    print("\n=== Summary ===")
    print(f"ASU courses: {n_asu} ({n_asu_des} designations)")
    print(f"UTK courses: {n_utk} ({n_utk_des} designations)")

    cur = conn.cursor()
    for school, in cur.execute("SELECT DISTINCT school FROM courses ORDER BY school"):
        total = cur.execute("SELECT COUNT(*) FROM courses WHERE school=?", (school,)).fetchone()[0]
        by_level = dict(
            cur.execute(
                "SELECT COALESCE(level,'unknown'), COUNT(*) FROM courses WHERE school=? GROUP BY level",
                (school,),
            ).fetchall()
        )
        online = cur.execute(
            "SELECT COUNT(*) FROM courses WHERE school=? AND offered_online=1", (school,)
        ).fetchone()[0]
        subjects = cur.execute(
            "SELECT COUNT(DISTINCT subject) FROM courses WHERE school=?", (school,)
        ).fetchone()[0]
        print(f"\n{school}: {total} courses, {subjects} subjects, online={online}, levels={by_level}")

    conn.close()
    print(f"\nDB: {DB_PATH}")


if __name__ == "__main__":
    main()
