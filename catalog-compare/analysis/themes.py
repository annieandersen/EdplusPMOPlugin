"""Thematic analysis layer:

- Clusters unique courses at each school to find "what each school uniquely
  teaches" themes.
- Builds a subject-pair map (UTK subject <-> most-linked ASU subject).
- Extracts top mutual-strong pairs for the report backbone.
- Examines VolCore <-> General Studies designation differences.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
DB_PATH = DATA / "catalog.db"
ANALYSIS = DATA / "analysis"
OUT = ANALYSIS


def load_matches(path: Path) -> pd.DataFrame:
    return pd.read_json(path, lines=True)


def top_cluster_terms(vec: TfidfVectorizer, X, cluster_assignments, n_clusters, top_n=8):
    """Return top TF-IDF terms per cluster, computed from centroids."""
    terms = np.array(vec.get_feature_names_out())
    term_scores = np.zeros((n_clusters, len(terms)))
    for c in range(n_clusters):
        mask = cluster_assignments == c
        if mask.sum() == 0:
            continue
        centroid = np.asarray(X[mask].mean(axis=0)).ravel()
        term_scores[c] = centroid
    out = []
    for c in range(n_clusters):
        top_idx = np.argsort(-term_scores[c])[:top_n]
        out.append([str(t) for t in terms[top_idx]])
    return out


def cluster_unique_courses(df: pd.DataFrame, school: str, n_clusters: int = 25) -> pd.DataFrame:
    unique = df[(df["match_strength"] == "unique") & (~df["is_generic"])].copy()
    unique["text"] = (unique["title"].fillna("") + ". ") * 3 + unique["description"].fillna("")
    if len(unique) < n_clusters:
        n_clusters = max(2, len(unique) // 5)

    vec = TfidfVectorizer(
        max_features=20_000, ngram_range=(1, 2), min_df=3, max_df=0.4,
        stop_words="english", sublinear_tf=True,
    )
    X = vec.fit_transform(unique["text"])
    X = normalize(X)

    km = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, n_init=5, batch_size=1024)
    unique["cluster"] = km.fit_predict(X)

    cluster_terms = top_cluster_terms(vec, X, unique["cluster"].values, n_clusters)

    rows = []
    for c in range(n_clusters):
        mask = unique["cluster"] == c
        members = unique[mask]
        if members.empty:
            continue
        exemplars = members.sort_values("best_match_sim").head(6)
        rows.append({
            "school": school,
            "cluster_id": int(c),
            "size": int(mask.sum()),
            "top_terms": cluster_terms[c],
            "top_subjects": members["subject"].value_counts().head(5).to_dict(),
            "top_colleges": (
                members["college"].value_counts().head(3).to_dict()
                if "college" in members.columns and members["college"].notna().any()
                else {}
            ),
            "level_mix": members["level"].value_counts().to_dict(),
            "exemplars": [
                {"course_code": r.course_code, "title": r.title}
                for r in exemplars.itertuples()
            ],
        })
    return pd.DataFrame(rows).sort_values("size", ascending=False)


def subject_pair_map(asu: pd.DataFrame, utk: pd.DataFrame) -> pd.DataFrame:
    """For each UTK subject, find the ASU subject it most often maps into (strong/moderate)."""
    merged = utk[["subject", "best_match_code", "match_strength"]].dropna(subset=["best_match_code"]).copy()
    asu_lookup = (
        asu.drop_duplicates("course_code")
        .set_index("course_code")[["subject", "college"]]
        .to_dict("index")
    )
    merged["asu_subject"] = merged["best_match_code"].map(
        lambda c: asu_lookup.get(c, {}).get("subject")
    )
    merged["asu_college"] = merged["best_match_code"].map(
        lambda c: asu_lookup.get(c, {}).get("college")
    )
    strong = merged[merged["match_strength"].isin(["strong", "moderate"])]
    counts = (
        strong.groupby(["subject", "asu_subject", "asu_college"])
        .size()
        .reset_index(name="links")
        .sort_values(["subject", "links"], ascending=[True, False])
    )
    # Keep top pair per UTK subject.
    top = counts.groupby("subject").head(1).reset_index(drop=True)
    return top.sort_values("links", ascending=False)


def top_mutual_pairs(asu: pd.DataFrame, utk: pd.DataFrame, limit: int = 120) -> pd.DataFrame:
    mut = asu[asu["mutual_strong"] == True].copy()
    mut = mut[~mut["is_generic"]]
    out = mut[[
        "course_code", "title", "level", "college", "best_match_code",
        "best_match_title", "best_match_sim",
    ]].rename(columns={
        "course_code": "asu_code",
        "title": "asu_title",
        "level": "asu_level",
        "college": "asu_college",
        "best_match_code": "utk_code",
        "best_match_title": "utk_title",
        "best_match_sim": "similarity",
    })
    # Attach UTK metadata (dedupe since UTK course_code can repeat across undergrad/grad catalogs)
    utk_lookup = (
        utk.drop_duplicates("course_code")
        .set_index("course_code")[["subject", "level"]]
        .to_dict("index")
    )
    out["utk_subject"] = out["utk_code"].map(lambda c: utk_lookup.get(c, {}).get("subject"))
    out["utk_level"] = out["utk_code"].map(lambda c: utk_lookup.get(c, {}).get("level"))
    return out.sort_values("similarity", ascending=False).head(limit)


def modality_gap(asu: pd.DataFrame, utk: pd.DataFrame) -> dict:
    """Where ASU is heavily online; the UTK side has no online flag in catalog."""
    asu_online = asu[asu["offered_online"] == 1]
    online_by_college = asu_online["college"].value_counts().to_dict()
    online_by_level = asu_online["level"].value_counts().to_dict()
    online_subjects = asu_online["subject"].value_counts().head(15).to_dict()
    return {
        "asu_total_online": int(len(asu_online)),
        "asu_online_share_pct": round(len(asu_online) / max(1, len(asu)) * 100, 1),
        "online_by_college": online_by_college,
        "online_by_level": online_by_level,
        "top_online_subjects": online_subjects,
        "utk_note": "UTK catalog does not flag per-course online modality; distance-ed is captured at program level only.",
    }


def designation_comparison(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        """
        SELECT c.school, c.course_code, c.level, d.system, d.code, d.label
        FROM designations d
        JOIN courses c ON c.id = d.course_id
        """,
        conn,
    )
    conn.close()
    totals = df.groupby(["system", "code"]).size().reset_index(name="count")
    totals = totals.sort_values(["system", "count"], ascending=[True, False])

    asu_gen_count = int(df[df.system.str.startswith("ASU_")].course_code.nunique())
    utk_vc_count = int(df[df.system == "UTK_VOLCORE"].course_code.nunique())
    out = {
        "asu_general_studies_tagged_courses": asu_gen_count,
        "utk_volcore_tagged_courses": utk_vc_count,
        "systems": {},
    }
    for sys_name, grp in totals.groupby("system"):
        out["systems"][sys_name] = grp[["code", "count"]].to_dict("records")
    return out


def discipline_rollup(asu: pd.DataFrame, utk: pd.DataFrame) -> pd.DataFrame:
    """Roll the UTK subjects up to ASU-college space via the subject_pair_map,
    then show counts per (discipline, school, level)."""
    sp = subject_pair_map(asu, utk)
    utk_to_college = dict(zip(sp["subject"], sp["asu_college"]))

    rows = []
    asu_agg = asu.groupby(["college", "level"]).size().reset_index(name="asu_count")
    asu_agg = asu_agg.rename(columns={"college": "discipline"})

    utk_agg = utk.copy()
    utk_agg["discipline"] = utk_agg["subject"].map(utk_to_college).fillna("Unmapped")
    utk_agg = utk_agg.groupby(["discipline", "level"]).size().reset_index(name="utk_count")

    merged = pd.merge(asu_agg, utk_agg, on=["discipline", "level"], how="outer").fillna(0)
    merged["asu_count"] = merged["asu_count"].astype(int)
    merged["utk_count"] = merged["utk_count"].astype(int)
    merged["total"] = merged["asu_count"] + merged["utk_count"]
    return merged.sort_values(["discipline", "level"])


def main():
    asu = load_matches(ANALYSIS / "asu_with_matches.jsonl")
    utk = load_matches(ANALYSIS / "utk_with_matches.jsonl")

    print(f"ASU {len(asu)}, UTK {len(utk)}")

    print("Clustering unique ASU courses...")
    asu_clusters = cluster_unique_courses(asu, "ASU", n_clusters=30)
    asu_clusters.to_json(OUT / "asu_unique_clusters.jsonl", orient="records", lines=True)

    print("Clustering unique UTK courses...")
    utk_clusters = cluster_unique_courses(utk, "UTK", n_clusters=30)
    utk_clusters.to_json(OUT / "utk_unique_clusters.jsonl", orient="records", lines=True)

    print("Subject pair map (UTK -> ASU)...")
    sp = subject_pair_map(asu, utk)
    sp.to_csv(OUT / "utk_to_asu_subject_map.csv", index=False)

    print("Top mutual-strong pairs...")
    mp = top_mutual_pairs(asu, utk, limit=200)
    mp.to_csv(OUT / "top_mutual_pairs.csv", index=False)
    mp.to_json(OUT / "top_mutual_pairs.jsonl", orient="records", lines=True)

    print("Modality gap...")
    mg = modality_gap(asu, utk)
    (OUT / "modality_gap.json").write_text(json.dumps(mg, indent=2))

    print("Designation comparison...")
    dc = designation_comparison(DB_PATH)
    (OUT / "designation_comparison.json").write_text(json.dumps(dc, indent=2))

    print("Discipline rollup...")
    dr = discipline_rollup(asu, utk)
    dr.to_csv(OUT / "discipline_rollup.csv", index=False)

    print("\nArtifacts:")
    for p in sorted(OUT.iterdir()):
        print(f"  {p.name:40s}  {p.stat().st_size:>10,} bytes")


if __name__ == "__main__":
    main()
