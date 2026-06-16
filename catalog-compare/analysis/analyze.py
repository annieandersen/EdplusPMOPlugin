"""Cross-school catalog analysis: TF-IDF similarity + summary statistics.

Produces JSON + CSV artifacts under ../data/ for the report layer.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, vstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
DB_PATH = DATA / "catalog.db"
OUT = DATA / "analysis"
OUT.mkdir(exist_ok=True, parents=True)

STRONG_THRESHOLD = 0.55
MODERATE_THRESHOLD = 0.30
TOP_K = 5

# Generic administrative course "shells" that match each other on boilerplate
# rather than teaching content. Flag these so they don't inflate overlap stats.
GENERIC_TITLE_PATTERNS = [
    r"^special topics\b", r"^topics in\b", r"^selected topics\b",
    r"^thesis\b", r"^dissertation\b", r"^master'?s thesis\b",
    r"^doctoral dissertation\b", r"^research\b", r"^undergraduate research\b",
    r"^independent study\b", r"^directed study\b", r"^directed research\b",
    r"^seminar\b", r"^graduate seminar\b", r"^honors seminar\b",
    r"^internship\b", r"^practicum\b", r"^field work\b", r"^field experience\b",
    r"^capstone\b", r"^project\b", r"^senior project\b",
    r"^continuing registration\b", r"^reading\b", r"^readings in\b",
    r"^workshop\b", r"^colloquium\b",
    r"^teaching assistant\b", r"^teaching practicum\b",
    r"^honors thesis\b", r"^doctoral research\b", r"^masters research\b",
]


def is_generic_shell(title: str) -> bool:
    if not title:
        return True
    t = title.lower().strip()
    # Common short titles
    if t in {"thesis", "dissertation", "seminar", "internship", "special topics",
             "capstone", "research", "independent study", "directed study",
             "practicum", "workshop", "colloquium", "reading", "project",
             "field work", "field experience", "special problems"}:
        return True
    for pat in GENERIC_TITLE_PATTERNS:
        if re.match(pat, t):
            return True
    return False


def clean_description(text: str | None) -> str:
    if not text:
        return ""
    t = re.sub(r"<[^>]+>", " ", str(text))
    t = re.sub(
        r"Prerequisite(\(s\))?:.*?(\.|$)",
        " ",
        t,
        flags=re.IGNORECASE | re.DOTALL,
    )
    t = re.sub(
        r"Corequisite(\(s\))?:.*?(\.|$)",
        " ",
        t,
        flags=re.IGNORECASE | re.DOTALL,
    )
    t = re.sub(
        r"Registration Restriction(\(s\))?:.*?(\.|$)",
        " ",
        t,
        flags=re.IGNORECASE | re.DOTALL,
    )
    t = re.sub(r"\s+", " ", t).strip()
    return t


def load_courses(db_path: Path) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        """
        SELECT id, school, subject, catalog_number, course_code,
               title, description, level, college, offered_online, credits_min,
               credits_max
          FROM courses
        """,
        conn,
    )
    conn.close()
    df["title"] = df["title"].fillna("").astype(str)
    df["description"] = df["description"].fillna("").astype(str).map(clean_description)
    df["is_generic"] = df["title"].map(is_generic_shell)
    # Emphasize title (repeated) then description.
    df["text"] = (df["title"] + ". ") * 3 + df["description"]
    df["text"] = df["text"].str.strip()
    return df


def vectorize(df: pd.DataFrame):
    vec = TfidfVectorizer(
        max_features=60_000,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.5,
        stop_words="english",
        sublinear_tf=True,
    )
    X = vec.fit_transform(df["text"])
    X = normalize(X)
    return vec, X


def topk_cross(query_X, query_df, index_X, index_df, k=TOP_K, batch=400):
    """For each row in query_X, return the top-k matches in index_X.

    Returns a list of lists: [(course_code, similarity), ...] per query row.
    """
    n = query_X.shape[0]
    out = [None] * n
    idx_codes = index_df["course_code"].to_numpy()
    idx_titles = index_df["title"].to_numpy()
    idx_ids = index_df["id"].to_numpy()
    idx_subjects = index_df["subject"].to_numpy()
    idx_levels = index_df["level"].fillna("").to_numpy()
    for start in range(0, n, batch):
        end = min(start + batch, n)
        sim = (query_X[start:end] @ index_X.T).toarray()
        if sim.shape[1] <= k:
            top_idx = np.argsort(-sim, axis=1)
        else:
            part = np.argpartition(-sim, k, axis=1)[:, :k]
            top_idx = np.take_along_axis(
                part,
                np.argsort(-np.take_along_axis(sim, part, axis=1), axis=1),
                axis=1,
            )
        for i in range(end - start):
            row_idx = top_idx[i]
            row_sim = sim[i, row_idx]
            out[start + i] = [
                {
                    "id": int(idx_ids[j]),
                    "course_code": str(idx_codes[j]),
                    "title": str(idx_titles[j]),
                    "subject": str(idx_subjects[j]),
                    "level": str(idx_levels[j]),
                    "sim": float(s),
                }
                for j, s in zip(row_idx, row_sim)
            ]
        if start % (batch * 10) == 0:
            print(f"  topk: {end}/{n}")
    return out


def classify(sim: float) -> str:
    if sim >= STRONG_THRESHOLD:
        return "strong"
    if sim >= MODERATE_THRESHOLD:
        return "moderate"
    return "unique"


def main():
    print("Loading courses...")
    df = load_courses(DB_PATH)
    print(f"  total {len(df)}")

    print("Vectorizing (TF-IDF)...")
    vec, X = vectorize(df)
    print(f"  vocab size: {len(vec.get_feature_names_out())}")

    asu_mask = df["school"] == "ASU"
    utk_mask = df["school"] == "UTK"
    asu_df = df[asu_mask].reset_index(drop=True)
    utk_df = df[utk_mask].reset_index(drop=True)
    X_asu = X[asu_mask.values]
    X_utk = X[utk_mask.values]
    print(f"  ASU {X_asu.shape}, UTK {X_utk.shape}")

    print("Matching UTK -> ASU...")
    utk_to_asu = topk_cross(X_utk, utk_df, X_asu, asu_df)
    print("Matching ASU -> UTK...")
    asu_to_utk = topk_cross(X_asu, asu_df, X_utk, utk_df)

    # Save raw matches
    utk_df["matches_in_asu"] = utk_to_asu
    asu_df["matches_in_utk"] = asu_to_utk

    utk_df["best_match_sim"] = [m[0]["sim"] if m else 0.0 for m in utk_to_asu]
    utk_df["best_match_code"] = [m[0]["course_code"] if m else None for m in utk_to_asu]
    utk_df["best_match_title"] = [m[0]["title"] if m else None for m in utk_to_asu]
    utk_df["match_strength"] = utk_df["best_match_sim"].map(classify)
    # If either side of the match is a generic admin shell, downgrade the label.
    asu_titles = asu_df.set_index("course_code")["title"].to_dict()
    utk_df["best_is_generic"] = utk_df["best_match_title"].fillna("").map(is_generic_shell)
    utk_df.loc[utk_df["is_generic"] | utk_df["best_is_generic"], "match_strength"] = "generic_shell"

    asu_df["best_match_sim"] = [m[0]["sim"] if m else 0.0 for m in asu_to_utk]
    asu_df["best_match_code"] = [m[0]["course_code"] if m else None for m in asu_to_utk]
    asu_df["best_match_title"] = [m[0]["title"] if m else None for m in asu_to_utk]
    asu_df["match_strength"] = asu_df["best_match_sim"].map(classify)
    asu_df["best_is_generic"] = asu_df["best_match_title"].fillna("").map(is_generic_shell)
    asu_df.loc[asu_df["is_generic"] | asu_df["best_is_generic"], "match_strength"] = "generic_shell"

    # Mutual strong match: both sides agree at strong threshold.
    asu_by_code = asu_df.set_index("course_code")
    utk_by_code = utk_df.set_index("course_code")

    def mark_mutual(df_side, other_side):
        mutual = []
        for _, row in df_side.iterrows():
            if row["match_strength"] != "strong" or not row["best_match_code"]:
                mutual.append(False)
                continue
            other = other_side.loc[other_side.index == row["best_match_code"]]
            if other.empty:
                mutual.append(False)
                continue
            other_row = other.iloc[0]
            mutual.append(
                other_row["match_strength"] == "strong"
                and other_row["best_match_code"] == row.name
            )
        return mutual

    # set index to course_code for membership lookup
    asu_df_indexed = asu_df.set_index("course_code", drop=False)
    utk_df_indexed = utk_df.set_index("course_code", drop=False)
    asu_df["mutual_strong"] = mark_mutual(asu_df_indexed, utk_df_indexed)
    utk_df["mutual_strong"] = mark_mutual(utk_df_indexed, asu_df_indexed)

    # Persist full match artifacts
    print("Writing artifacts...")
    asu_out = asu_df[[
        "id", "school", "subject", "catalog_number", "course_code",
        "title", "description", "level", "college", "offered_online",
        "credits_min", "credits_max", "is_generic",
        "best_match_code", "best_match_title", "best_match_sim",
        "match_strength", "mutual_strong", "matches_in_utk",
    ]]
    utk_out = utk_df[[
        "id", "school", "subject", "catalog_number", "course_code",
        "title", "description", "level", "college", "offered_online",
        "credits_min", "credits_max", "is_generic",
        "best_match_code", "best_match_title", "best_match_sim",
        "match_strength", "mutual_strong", "matches_in_asu",
    ]]
    asu_out.to_json(OUT / "asu_with_matches.jsonl", orient="records", lines=True)
    utk_out.to_json(OUT / "utk_with_matches.jsonl", orient="records", lines=True)

    # Summary stats
    summary = {
        "counts": {
            "asu_total": int(asu_mask.sum()),
            "utk_total": int(utk_mask.sum()),
            "asu_undergrad": int(((df.school == "ASU") & (df.level == "undergrad")).sum()),
            "asu_grad": int(((df.school == "ASU") & (df.level == "grad")).sum()),
            "utk_undergrad": int(((df.school == "UTK") & (df.level == "undergrad")).sum()),
            "utk_grad": int(((df.school == "UTK") & (df.level == "grad")).sum()),
            "asu_online": int(((df.school == "ASU") & (df.offered_online == 1)).sum()),
            "utk_online": int(((df.school == "UTK") & (df.offered_online == 1)).sum()),
        },
        "match_distribution": {
            "asu_to_utk": asu_df["match_strength"].value_counts().to_dict(),
            "utk_to_asu": utk_df["match_strength"].value_counts().to_dict(),
        },
        "mutual_strong_count": int(asu_df["mutual_strong"].sum()),
        "generic_shells": {
            "asu": int(asu_df["is_generic"].sum()),
            "utk": int(utk_df["is_generic"].sum()),
        },
        "thresholds": {
            "strong": STRONG_THRESHOLD,
            "moderate": MODERATE_THRESHOLD,
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=int))
    print(json.dumps(summary, indent=2, default=int))

    # Discipline view: bucket by ASU college for ASU courses
    # For UTK, use subject-to-college inference via strong ASU matches.
    print("Building discipline view...")
    asu_by_college = (
        asu_df.groupby(["college", "level"]).size().unstack(fill_value=0).reset_index()
    )
    asu_by_college.to_csv(OUT / "asu_by_college.csv", index=False)

    # Infer UTK subject -> ASU college by strong matches
    strong_utk = utk_df[utk_df.match_strength == "strong"].copy()
    code_to_college = asu_df.set_index("course_code")["college"].to_dict()
    strong_utk["inferred_college"] = strong_utk["best_match_code"].map(code_to_college)
    utk_subject_college = (
        strong_utk.groupby(["subject", "inferred_college"]).size()
        .reset_index(name="strong_match_count")
        .sort_values(["subject", "strong_match_count"], ascending=[True, False])
    )
    utk_subject_college.to_csv(OUT / "utk_subject_college_inference.csv", index=False)

    # Unique courses per school (no strong match)
    asu_unique = asu_df[asu_df.match_strength == "unique"][
        ["course_code", "title", "level", "college", "subject", "best_match_sim"]
    ].sort_values("college")
    utk_unique = utk_df[utk_df.match_strength == "unique"][
        ["course_code", "title", "level", "subject", "best_match_sim"]
    ].sort_values("subject")
    asu_unique.to_csv(OUT / "asu_unique_courses.csv", index=False)
    utk_unique.to_csv(OUT / "utk_unique_courses.csv", index=False)

    # Subject-level overlap: for each school+subject, what % have strong matches?
    asu_subject_overlap = (
        asu_df.groupby("subject").agg(
            total=("course_code", "count"),
            strong=("match_strength", lambda s: (s == "strong").sum()),
            moderate=("match_strength", lambda s: (s == "moderate").sum()),
            unique=("match_strength", lambda s: (s == "unique").sum()),
            avg_best_sim=("best_match_sim", "mean"),
        ).reset_index()
    )
    asu_subject_overlap["strong_pct"] = asu_subject_overlap["strong"] / asu_subject_overlap["total"]
    asu_subject_overlap = asu_subject_overlap.sort_values("total", ascending=False)
    asu_subject_overlap.to_csv(OUT / "asu_subject_overlap.csv", index=False)

    utk_subject_overlap = (
        utk_df.groupby("subject").agg(
            total=("course_code", "count"),
            strong=("match_strength", lambda s: (s == "strong").sum()),
            moderate=("match_strength", lambda s: (s == "moderate").sum()),
            unique=("match_strength", lambda s: (s == "unique").sum()),
            avg_best_sim=("best_match_sim", "mean"),
        ).reset_index()
    )
    utk_subject_overlap["strong_pct"] = utk_subject_overlap["strong"] / utk_subject_overlap["total"]
    utk_subject_overlap = utk_subject_overlap.sort_values("total", ascending=False)
    utk_subject_overlap.to_csv(OUT / "utk_subject_overlap.csv", index=False)

    print("\nDone. Artifacts written to", OUT)
    print("Files:")
    for p in sorted(OUT.iterdir()):
        size = p.stat().st_size
        print(f"  {p.name:40s}  {size:>10,} bytes")


if __name__ == "__main__":
    main()
