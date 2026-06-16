"""v2 analysis: proper semantic embeddings + cluster-to-cluster thematic bridges.

Addresses a flaw in v1: TF-IDF-based unique-course clusters at each school had
overlapping *themes* (e.g. ASU "Advanced research & methods" and UTK "Data
science & programming") while specific course pairs scored as "unique".

v2 does two things:
1. Replaces TF-IDF with sentence-transformer embeddings (all-MiniLM-L6-v2).
   Semantic similarity, not lexical.
2. Adds a cluster-centroid crosswalk: for every unique-course cluster at one
   school, find its nearest cluster at the other school. This reveals
   "thematic overlap without 1:1 course overlap" — which is precisely the
   kind of opportunity for joint development that gets missed by pair-only
   matching.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
DB_PATH = DATA / "catalog.db"
OUT = DATA / "analysis_v2"
OUT.mkdir(parents=True, exist_ok=True)
EMB_CACHE = DATA / "embeddings_minilm.npz"

# Thresholds calibrated for all-MiniLM-L6-v2 on course text (higher ranges
# than TF-IDF; MiniLM puts more pairs in 0.5-0.8).
STRONG = 0.70
MODERATE = 0.50
TOP_K = 8

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


def is_generic(title: str) -> bool:
    if not title:
        return True
    t = title.lower().strip()
    if t in {"thesis", "dissertation", "seminar", "internship", "special topics",
             "capstone", "research", "independent study", "directed study",
             "practicum", "workshop", "colloquium", "reading", "project",
             "field work", "field experience", "special problems"}:
        return True
    for pat in GENERIC_TITLE_PATTERNS:
        if re.match(pat, t):
            return True
    return False


def clean(text):
    if not text:
        return ""
    t = re.sub(r"<[^>]+>", " ", str(text))
    t = re.sub(r"Prerequisite(\(s\))?:.*?(\.|$)", " ", t, flags=re.I | re.S)
    t = re.sub(r"Corequisite(\(s\))?:.*?(\.|$)", " ", t, flags=re.I | re.S)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def load_courses() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT id, school, subject, catalog_number, course_code, title, "
        "description, level, college, offered_online FROM courses",
        conn,
    )
    conn.close()
    df["title"] = df["title"].fillna("").astype(str)
    df["description"] = df["description"].fillna("").astype(str).map(clean)
    df["is_generic"] = df["title"].map(is_generic)
    # For embedding: title + key description (description is more informative
    # than title for MiniLM; don't inflate title).
    df["text"] = (df["title"] + ". " + df["description"]).str.strip()
    df.loc[df["text"] == ".", "text"] = df["title"]
    return df


def get_embeddings(texts: list[str]) -> np.ndarray:
    """Encode with all-MiniLM-L6-v2, cache to disk."""
    if EMB_CACHE.exists():
        cached = np.load(EMB_CACHE, allow_pickle=True)
        if cached["n"].item() == len(texts):
            print(f"  using cached embeddings ({cached['X'].shape})")
            return cached["X"]

    print(f"  encoding {len(texts):,} texts...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    X = model.encode(
        texts,
        batch_size=128,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    np.savez_compressed(EMB_CACHE, X=X, n=np.array(len(texts)))
    return X


def topk_cross(
    query_X, query_df, index_X, index_df, k=TOP_K, batch=400
) -> list[list[dict]]:
    n = query_X.shape[0]
    out: list = [None] * n
    idx_codes = index_df["course_code"].to_numpy()
    idx_titles = index_df["title"].to_numpy()
    idx_ids = index_df["id"].to_numpy()
    idx_subjects = index_df["subject"].to_numpy()
    idx_levels = index_df["level"].fillna("").to_numpy()
    idx_colleges = index_df["college"].fillna("").to_numpy() if "college" in index_df else np.array([""] * len(index_df))
    for start in range(0, n, batch):
        end = min(start + batch, n)
        sim = query_X[start:end] @ index_X.T  # (batch, M)
        top_idx = np.argpartition(-sim, min(k, sim.shape[1] - 1), axis=1)[:, :k]
        top_idx = np.take_along_axis(
            top_idx,
            np.argsort(-np.take_along_axis(sim, top_idx, axis=1), axis=1),
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
                    "college": str(idx_colleges[j]),
                    "sim": float(s),
                }
                for j, s in zip(row_idx, row_sim)
            ]
        if start % (batch * 10) == 0:
            print(f"  topk: {end}/{n}")
    return out


def classify(sim: float) -> str:
    if sim >= STRONG:
        return "strong"
    if sim >= MODERATE:
        return "moderate"
    return "unique"


def cluster_unique(df: pd.DataFrame, X: np.ndarray, school: str, n_clusters: int = 24):
    """Cluster the unique (non-generic, no strong cross-school match) courses
    using MiniBatchKMeans on the MiniLM embeddings (same semantic space we
    matched in — better than TF-IDF clustering)."""
    from sklearn.cluster import MiniBatchKMeans

    mask = (df["match_strength"] == "unique") & (~df["is_generic"])
    sub_df = df[mask].reset_index(drop=True).copy()
    sub_X = X[mask.to_numpy()]

    if len(sub_df) < n_clusters:
        n_clusters = max(2, len(sub_df) // 5)

    km = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, n_init=5, batch_size=1024)
    sub_df["cluster"] = km.fit_predict(sub_X)
    centroids = km.cluster_centers_
    # Normalize centroids for cosine sim with normalized embeddings
    centroids = centroids / (np.linalg.norm(centroids, axis=1, keepdims=True) + 1e-9)

    rows = []
    for c in range(n_clusters):
        members = sub_df[sub_df["cluster"] == c]
        if members.empty:
            continue
        # Top terms from titles (for human labels)
        titles = " ".join(members["title"].tolist()).lower()
        words = re.findall(r"[a-z][a-z]+", titles)
        stop = set("the of and a in to for with on an by at from is as not or be "
                   "about through between under within into this that these those "
                   "advanced introduction principles methods systems".split())
        from collections import Counter
        top_words = [w for w, _ in Counter([w for w in words if len(w) > 3 and w not in stop]).most_common(10)]
        top_subjects = members["subject"].value_counts().head(5).to_dict()
        top_colleges = (
            members["college"].value_counts().head(3).to_dict()
            if "college" in members.columns and members["college"].notna().any()
            else {}
        )
        # Representative exemplars: members closest to centroid
        member_X = sub_X[sub_df["cluster"].to_numpy() == c]
        sims_to_centroid = member_X @ centroids[c]
        top_member_idx = np.argsort(-sims_to_centroid)[:6]
        member_codes = members.iloc[top_member_idx]
        exemplars = [
            {
                "course_code": r.course_code,
                "title": r.title,
                "level": r.level,
                "description": (r.description or "")[:280],
            }
            for r in member_codes.itertuples()
        ]
        # All courses for drill-down (limit 40 to keep html manageable)
        all_courses = members.sort_values("title").head(40)
        courses_all = [
            {
                "course_code": r.course_code,
                "title": r.title,
                "level": r.level,
                "description": (r.description or "")[:400],
            }
            for r in all_courses.itertuples()
        ]
        rows.append({
            "school": school,
            "cluster_id": int(c),
            "size": int(len(members)),
            "top_words": top_words,
            "top_subjects": top_subjects,
            "top_colleges": top_colleges,
            "level_mix": members["level"].value_counts().to_dict(),
            "exemplars": exemplars,
            "courses": courses_all,
        })
    return pd.DataFrame(rows).sort_values("size", ascending=False).reset_index(drop=True), centroids


def cluster_bridges(
    asu_clusters: pd.DataFrame, asu_centroids: np.ndarray,
    utk_clusters: pd.DataFrame, utk_centroids: np.ndarray,
) -> list[dict]:
    """For each ASU cluster, find nearest UTK cluster (and vice versa).
    Return records showing the bridges — these are thematic overlaps that
    pair-only matching misses.
    """
    # asu_clusters is sorted by size; its "cluster_id" column carries
    # the original kmeans id matching a row in asu_centroids.
    asu_ids = asu_clusters["cluster_id"].to_numpy()
    utk_ids = utk_clusters["cluster_id"].to_numpy()
    asu_cen = asu_centroids[asu_ids]
    utk_cen = utk_centroids[utk_ids]
    sim = asu_cen @ utk_cen.T  # (n_asu_clusters, n_utk_clusters)

    bridges = []
    for i, arow in asu_clusters.iterrows():
        j = int(np.argmax(sim[i]))
        bridges.append({
            "direction": "ASU->UTK",
            "score": float(sim[i, j]),
            "asu_cluster_id": int(arow["cluster_id"]),
            "asu_size": int(arow["size"]),
            "asu_top_words": arow["top_words"][:6],
            "asu_exemplars": arow["exemplars"][:3],
            "utk_cluster_id": int(utk_clusters.iloc[j]["cluster_id"]),
            "utk_size": int(utk_clusters.iloc[j]["size"]),
            "utk_top_words": utk_clusters.iloc[j]["top_words"][:6],
            "utk_exemplars": utk_clusters.iloc[j]["exemplars"][:3],
        })
    for j, urow in utk_clusters.iterrows():
        i = int(np.argmax(sim[:, j]))
        bridges.append({
            "direction": "UTK->ASU",
            "score": float(sim[i, j]),
            "utk_cluster_id": int(urow["cluster_id"]),
            "utk_size": int(urow["size"]),
            "utk_top_words": urow["top_words"][:6],
            "utk_exemplars": urow["exemplars"][:3],
            "asu_cluster_id": int(asu_clusters.iloc[i]["cluster_id"]),
            "asu_size": int(asu_clusters.iloc[i]["size"]),
            "asu_top_words": asu_clusters.iloc[i]["top_words"][:6],
            "asu_exemplars": asu_clusters.iloc[i]["exemplars"][:3],
        })
    return bridges


def main():
    print("Loading courses...")
    df = load_courses()
    print(f"  {len(df):,} rows")

    print("Embedding (MiniLM)...")
    X = get_embeddings(df["text"].tolist())
    print(f"  embeddings shape: {X.shape}")

    asu_mask = (df["school"] == "ASU").to_numpy()
    utk_mask = (df["school"] == "UTK").to_numpy()
    asu_df = df[asu_mask].reset_index(drop=True)
    utk_df = df[utk_mask].reset_index(drop=True)
    X_asu = X[asu_mask]
    X_utk = X[utk_mask]
    print(f"  ASU {X_asu.shape}, UTK {X_utk.shape}")

    print("UTK -> ASU nearest...")
    utk_to_asu = topk_cross(X_utk, utk_df, X_asu, asu_df)
    print("ASU -> UTK nearest...")
    asu_to_utk = topk_cross(X_asu, asu_df, X_utk, utk_df)

    asu_df["matches"] = asu_to_utk
    utk_df["matches"] = utk_to_asu
    asu_df["best_sim"] = [m[0]["sim"] if m else 0.0 for m in asu_to_utk]
    asu_df["best_code"] = [m[0]["course_code"] if m else None for m in asu_to_utk]
    asu_df["best_title"] = [m[0]["title"] if m else None for m in asu_to_utk]
    asu_df["match_strength"] = asu_df["best_sim"].map(classify)
    utk_df["best_sim"] = [m[0]["sim"] if m else 0.0 for m in utk_to_asu]
    utk_df["best_code"] = [m[0]["course_code"] if m else None for m in utk_to_asu]
    utk_df["best_title"] = [m[0]["title"] if m else None for m in utk_to_asu]
    utk_df["match_strength"] = utk_df["best_sim"].map(classify)

    # Downgrade if either side is generic shell
    asu_df["best_is_generic"] = asu_df["best_title"].fillna("").map(is_generic)
    utk_df["best_is_generic"] = utk_df["best_title"].fillna("").map(is_generic)
    asu_df.loc[asu_df["is_generic"] | asu_df["best_is_generic"], "match_strength"] = "generic_shell"
    utk_df.loc[utk_df["is_generic"] | utk_df["best_is_generic"], "match_strength"] = "generic_shell"

    # Mutual strong
    asu_indexed = asu_df.drop_duplicates("course_code").set_index("course_code", drop=False)
    utk_indexed = utk_df.drop_duplicates("course_code").set_index("course_code", drop=False)
    def mutual(side, other_indexed):
        marks = []
        for _, row in side.iterrows():
            if row["match_strength"] != "strong" or not row["best_code"]:
                marks.append(False); continue
            other = other_indexed[other_indexed.index == row["best_code"]]
            if other.empty:
                marks.append(False); continue
            o = other.iloc[0]
            marks.append(
                o["match_strength"] == "strong"
                and o["best_code"] == row["course_code"]
            )
        return marks
    asu_df["mutual_strong"] = mutual(asu_df, utk_indexed)
    utk_df["mutual_strong"] = mutual(utk_df, asu_indexed)

    print("Clustering unique ASU courses (semantic)...")
    asu_clusters, asu_centroids = cluster_unique(asu_df, X_asu, "ASU", n_clusters=24)
    print("Clustering unique UTK courses (semantic)...")
    utk_clusters, utk_centroids = cluster_unique(utk_df, X_utk, "UTK", n_clusters=24)

    print("Building cluster-to-cluster bridges...")
    bridges = cluster_bridges(asu_clusters, asu_centroids, utk_clusters, utk_centroids)

    # Summary
    summary = {
        "method": "sentence-transformers all-MiniLM-L6-v2 on title + description; cosine similarity",
        "thresholds": {"strong": STRONG, "moderate": MODERATE},
        "counts": {
            "asu_total": int(len(asu_df)),
            "utk_total": int(len(utk_df)),
            "asu_undergrad": int(((asu_df.level == "undergrad")).sum()),
            "asu_grad": int(((asu_df.level == "grad")).sum()),
            "utk_undergrad": int(((utk_df.level == "undergrad")).sum()),
            "utk_grad": int(((utk_df.level == "grad")).sum()),
            "asu_online": int((asu_df.offered_online == 1).sum()),
        },
        "match_distribution": {
            "asu_to_utk": asu_df["match_strength"].value_counts().to_dict(),
            "utk_to_asu": utk_df["match_strength"].value_counts().to_dict(),
        },
        "mutual_strong_count": int(asu_df["mutual_strong"].sum()),
    }
    print(json.dumps(summary, indent=2, default=int))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=int))

    # Persist
    keep_cols = [
        "id", "school", "subject", "catalog_number", "course_code",
        "title", "description", "level", "college", "offered_online",
        "is_generic", "best_code", "best_title", "best_sim",
        "match_strength", "mutual_strong", "matches",
    ]
    asu_df[keep_cols].to_json(OUT / "asu_courses.jsonl", orient="records", lines=True)
    utk_df[keep_cols].to_json(OUT / "utk_courses.jsonl", orient="records", lines=True)

    asu_clusters.to_json(OUT / "asu_unique_clusters.jsonl", orient="records", lines=True)
    utk_clusters.to_json(OUT / "utk_unique_clusters.jsonl", orient="records", lines=True)
    (OUT / "cluster_bridges.json").write_text(json.dumps(bridges, indent=2, default=int))

    # Mutual-strong pairs (for report backbone)
    mut = asu_df[(asu_df["mutual_strong"] == True) & (~asu_df["is_generic"])].copy()
    utk_lookup = utk_df.drop_duplicates("course_code").set_index("course_code")[["subject", "level"]].to_dict("index")
    mut["utk_subject"] = mut["best_code"].map(lambda c: utk_lookup.get(c, {}).get("subject"))
    mut["utk_level"] = mut["best_code"].map(lambda c: utk_lookup.get(c, {}).get("level"))
    mut_out = mut[[
        "course_code", "title", "level", "college", "subject",
        "best_code", "best_title", "best_sim",
        "utk_subject", "utk_level",
    ]].rename(columns={
        "course_code": "asu_code", "title": "asu_title", "level": "asu_level",
        "subject": "asu_subject", "college": "asu_college",
        "best_code": "utk_code", "best_title": "utk_title", "best_sim": "similarity",
    }).sort_values("similarity", ascending=False)
    mut_out.to_json(OUT / "mutual_strong_pairs.jsonl", orient="records", lines=True)
    mut_out.to_csv(OUT / "mutual_strong_pairs.csv", index=False)

    print("\nArtifacts:")
    for p in sorted(OUT.iterdir()):
        print(f"  {p.name:40s} {p.stat().st_size:>12,} bytes")


if __name__ == "__main__":
    main()
