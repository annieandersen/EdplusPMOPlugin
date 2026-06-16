"""Subject-level analysis: for each ASU college and subject (and each UTK
subject), compute the match-strength distribution and surface:
- reciprocal-credit depth (% strong)
- joint-development opportunity (% moderate)
- distinctive offering (% unique)
- top partner subject on the other side

Feeds the HTML drill-down drawers.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
IN = DATA / "analysis_v2"
OUT = DATA / "analysis_v2"


def load(p):
    return pd.read_json(p, lines=True)


def pct(n, d):
    return round(100 * n / d, 1) if d else 0.0


def subject_rollup(side_df: pd.DataFrame, other_df: pd.DataFrame, school: str) -> list[dict]:
    """Per-subject stats + sample courses by bucket."""
    other_by_code = other_df.drop_duplicates("course_code").set_index("course_code")
    rows = []
    for subject, grp in side_df.groupby("subject"):
        non_generic = grp[~grp["is_generic"]]
        if len(non_generic) < 3:
            continue
        total = len(non_generic)
        strong = non_generic[non_generic.match_strength == "strong"]
        moderate = non_generic[non_generic.match_strength == "moderate"]
        unique = non_generic[non_generic.match_strength == "unique"]

        # Partner subject: where do the strong+moderate matches point to most?
        partner_counts = Counter()
        for code in strong["best_code"].dropna().tolist() + moderate["best_code"].dropna().tolist():
            if code in other_by_code.index:
                partner_counts[other_by_code.loc[code]["subject"]] += 1
        partner_subject, partner_count = partner_counts.most_common(1)[0] if partner_counts else (None, 0)

        # College (ASU has it, UTK doesn't)
        college = None
        if "college" in non_generic.columns and non_generic["college"].notna().any():
            college = non_generic["college"].value_counts().head(1).index[0]

        def samples(frame, n=8):
            return [
                {
                    "course_code": r.course_code,
                    "title": r.title,
                    "level": r.level,
                    "description": (r.description or "")[:400],
                    "best_code": r.best_code,
                    "best_title": r.best_title,
                    "best_sim": round(float(r.best_sim or 0), 2),
                }
                for r in frame.sort_values("best_sim", ascending=False).head(n).itertuples()
            ]

        rows.append({
            "school": school,
            "subject": subject,
            "college": college,
            "total": int(total),
            "strong": int(len(strong)),
            "moderate": int(len(moderate)),
            "unique": int(len(unique)),
            "strong_pct": pct(len(strong), total),
            "moderate_pct": pct(len(moderate), total),
            "unique_pct": pct(len(unique), total),
            "partner_subject": partner_subject,
            "partner_links": int(partner_count),
            "sample_strong": samples(strong, 6),
            "sample_moderate": samples(moderate, 6),
            "sample_unique": samples(unique, 8),
        })
    return sorted(rows, key=lambda r: -r["total"])


def discipline_rollup(asu_subject_rows: list[dict]) -> list[dict]:
    """Group ASU subjects by college. For each college, aggregate stats and
    hold the subject rows as children for drill-down."""
    by_college = defaultdict(list)
    for r in asu_subject_rows:
        by_college[r["college"] or "Other / Unassigned"].append(r)

    out = []
    for college, subjects in by_college.items():
        total = sum(s["total"] for s in subjects)
        strong = sum(s["strong"] for s in subjects)
        moderate = sum(s["moderate"] for s in subjects)
        unique = sum(s["unique"] for s in subjects)
        out.append({
            "college": college,
            "total": total,
            "strong": strong,
            "moderate": moderate,
            "unique": unique,
            "strong_pct": pct(strong, total),
            "moderate_pct": pct(moderate, total),
            "unique_pct": pct(unique, total),
            "subject_count": len(subjects),
            "subjects": sorted(subjects, key=lambda s: -s["total"]),
        })
    return sorted(out, key=lambda c: -c["total"])


def distinctive_leaders(subject_rows, side: str, min_total=10, top=12):
    """Subjects with the highest share of unique+moderate (less overlap with
    the other school) — the distinctive teaching that doesn't have a direct
    counterpart."""
    candidates = [r for r in subject_rows if r["total"] >= min_total]
    # Composite score: emphasis on unique and moderate share; tiebreak by total
    def score(r):
        return (r["unique_pct"] * 1.5 + r["moderate_pct"] * 0.6, r["total"])
    ranked = sorted(candidates, key=score, reverse=True)
    return ranked[:top]


def overlap_leaders(subject_rows, side: str, min_total=10, top=12):
    """Subjects with the highest share of strong cross-school matches — the
    reciprocal-credit density hotspots."""
    candidates = [r for r in subject_rows if r["total"] >= min_total]
    def score(r):
        return (r["strong_pct"], r["total"])
    ranked = sorted(candidates, key=score, reverse=True)
    return ranked[:top]


def main():
    print("Loading...")
    asu = load(IN / "asu_courses.jsonl")
    utk = load(IN / "utk_courses.jsonl")

    # Make sure every row has is_generic and match_strength (from v2)
    asu["match_strength"] = asu["match_strength"].fillna("unique")
    utk["match_strength"] = utk["match_strength"].fillna("unique")
    print(f"  ASU {len(asu)}, UTK {len(utk)}")

    print("Rolling up ASU by subject...")
    asu_subjects = subject_rollup(asu, utk, "ASU")
    print("Rolling up UTK by subject...")
    utk_subjects = subject_rollup(utk, asu, "UTK")

    print("Rolling up ASU by college...")
    asu_colleges = discipline_rollup(asu_subjects)

    asu_distinctive = distinctive_leaders(asu_subjects, "ASU")
    utk_distinctive = distinctive_leaders(utk_subjects, "UTK")
    asu_overlap = overlap_leaders(asu_subjects, "ASU")
    utk_overlap = overlap_leaders(utk_subjects, "UTK")

    (OUT / "asu_subjects.json").write_text(json.dumps(asu_subjects, indent=2, default=int))
    (OUT / "utk_subjects.json").write_text(json.dumps(utk_subjects, indent=2, default=int))
    (OUT / "asu_by_college.json").write_text(json.dumps(asu_colleges, indent=2, default=int))
    (OUT / "distinctive_leaders.json").write_text(json.dumps({
        "asu": asu_distinctive, "utk": utk_distinctive,
    }, indent=2, default=int))
    (OUT / "overlap_leaders.json").write_text(json.dumps({
        "asu": asu_overlap, "utk": utk_overlap,
    }, indent=2, default=int))

    print("\nTop 5 ASU colleges by total courses:")
    for c in asu_colleges[:5]:
        print(f"  {c['college']:40s} total={c['total']:5}  strong={c['strong_pct']:>5}%  moderate={c['moderate_pct']:>5}%  unique={c['unique_pct']:>5}%")

    print("\nASU 'most distinctive' subjects (high unique+moderate, min 10 courses):")
    for s in asu_distinctive[:10]:
        print(f"  {s['subject']:6} ({s['college'] or '-'[:25]:30s})  total={s['total']:3}  unique={s['unique_pct']:>4}%  moderate={s['moderate_pct']:>4}%  partner=UTK {s['partner_subject']}")

    print("\nUTK 'most distinctive' subjects (high unique+moderate, min 10 courses):")
    for s in utk_distinctive[:10]:
        print(f"  {s['subject']:6}  total={s['total']:3}  unique={s['unique_pct']:>4}%  moderate={s['moderate_pct']:>4}%  partner=ASU {s['partner_subject']}")

    print("\nASU subjects with highest STRONG overlap (reciprocal-credit density):")
    for s in asu_overlap[:10]:
        print(f"  {s['subject']:6}  total={s['total']:3}  strong={s['strong_pct']:>4}%   partner=UTK {s['partner_subject']} ({s['partner_links']})")

    print("\nArtifacts written to", OUT)


if __name__ == "__main__":
    main()
