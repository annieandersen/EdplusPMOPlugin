"""Build a polished static HTML comparison report from analysis artifacts.

Reads from ../data/analysis/* and writes ./catalog_comparison.html.
"""
from __future__ import annotations

import html
import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
ANALYSIS = DATA / "analysis"
OUT_HTML = HERE / "catalog_comparison.html"


def read_jsonl(p: Path):
    with p.open() as f:
        return [json.loads(l) for l in f if l.strip()]


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def pct(n, d):
    return f"{(100 * n / d):.1f}%" if d else "0%"


# ----- Load all artifacts -----
summary = json.loads((ANALYSIS / "summary.json").read_text())
modality = json.loads((ANALYSIS / "modality_gap.json").read_text())
designations = json.loads((ANALYSIS / "designation_comparison.json").read_text())
mutual_pairs = read_jsonl(ANALYSIS / "top_mutual_pairs.jsonl")
asu_clusters = sorted(read_jsonl(ANALYSIS / "asu_unique_clusters.jsonl"),
                      key=lambda c: -c["size"])
utk_clusters = sorted(read_jsonl(ANALYSIS / "utk_unique_clusters.jsonl"),
                      key=lambda c: -c["size"])

import csv as _csv
def read_csv(p):
    with open(p) as f:
        return list(_csv.DictReader(f))

subject_pair_map = read_csv(ANALYSIS / "utk_to_asu_subject_map.csv")
subject_pair_map = sorted(subject_pair_map, key=lambda r: -int(r["links"]))[:25]

c = summary["counts"]
md = summary["match_distribution"]

asu_total = c["asu_total"]
utk_total = c["utk_total"]
combined = asu_total + utk_total
mutual_count = summary.get("mutual_strong_count", len(mutual_pairs))


# Overall overlap bars
asu_strong = md["asu_to_utk"].get("strong", 0)
asu_moderate = md["asu_to_utk"].get("moderate", 0)
asu_unique = md["asu_to_utk"].get("unique", 0)
asu_generic = md["asu_to_utk"].get("generic_shell", 0)
utk_strong = md["utk_to_asu"].get("strong", 0)
utk_moderate = md["utk_to_asu"].get("moderate", 0)
utk_unique = md["utk_to_asu"].get("unique", 0)
utk_generic = md["utk_to_asu"].get("generic_shell", 0)


def bar_segment(label, count, total, color):
    if not total:
        return ""
    w = 100 * count / total
    return (
        f'<div class="seg" style="width:{w:.2f}%;background:{color}" '
        f'title="{esc(label)}: {count:,} ({w:.1f}%)"></div>'
    )


def stacked_bar(school, counts, total):
    colors = {
        "strong": "#1a5d3a",
        "moderate": "#6aa889",
        "unique": "#c44536",
        "generic_shell": "#9ca3af",
    }
    order = [("strong", "Strong"), ("moderate", "Moderate"),
             ("unique", "Unique"), ("generic_shell", "Admin shell")]
    segs = "".join(
        bar_segment(label, counts.get(key, 0), total, colors[key])
        for key, label in order
    )
    return f'<div class="stackbar">{segs}</div>'


# Top unique clusters rendering
def render_cluster(c, side="asu"):
    terms = ", ".join(c["top_terms"][:6])
    top_sub = ", ".join([f"{k} ({v})" for k, v in list(c.get("top_subjects", {}).items())[:3]])
    top_col = list(c.get("top_colleges", {}).keys())[:1]
    exemplars = "".join(
        f'<li><span class="cc">{esc(e["course_code"])}</span> {esc(e["title"])}</li>'
        for e in c["exemplars"][:4]
    )
    college_bit = f'<div class="meta">{esc(top_col[0])}</div>' if top_col else ""
    return f"""
    <div class="cluster {side}">
      <div class="csize">{c["size"]:,} courses</div>
      <div class="cterms">{esc(terms)}</div>
      <div class="csubs">Top subjects: {esc(top_sub)}</div>
      {college_bit}
      <ul>{exemplars}</ul>
    </div>
    """


mutual_rows = "".join(
    f"""<tr>
      <td class="num">{p["similarity"]:.2f}</td>
      <td><span class="cc">{esc(p["asu_code"])}</span> <span class="tt">{esc(p["asu_title"])}</span><br><span class="meta">{esc(p.get("asu_college") or "")}</span></td>
      <td><span class="cc">{esc(p["utk_code"])}</span> <span class="tt">{esc(p["utk_title"])}</span></td>
      <td class="lvl">{esc(p["asu_level"])}</td>
    </tr>"""
    for p in mutual_pairs[:60]
)


# Subject pair map table rows
pair_rows = "".join(
    f"""<tr>
      <td class="cc">{esc(r["subject"])}</td>
      <td class="cc">{esc(r["asu_subject"])}</td>
      <td>{esc(r["asu_college"])}</td>
      <td class="num">{int(r["links"])}</td>
    </tr>"""
    for r in subject_pair_map
)


# Designation comparison panels
def render_desig_panel(system_name, rows, title, subtitle):
    chip_html = "".join(
        f'<div class="chip"><span class="chip-code">{esc(r["code"])}</span>'
        f'<span class="chip-count">{int(r["count"])}</span></div>'
        for r in rows[:12]
    )
    return f"""
    <div class="desig-panel">
      <div class="desig-title">{esc(title)}</div>
      <div class="desig-sub">{esc(subtitle)}</div>
      <div class="chips">{chip_html}</div>
    </div>
    """


gs_gold_rows = designations["systems"].get("ASU_GS_GOLD", [])
gs_maroon_rows = designations["systems"].get("ASU_GS_MAROON", [])
volcore_rows = designations["systems"].get("UTK_VOLCORE", [])
gened_legacy_rows = designations["systems"].get("UTK_GENED_LEGACY", [])


# Top online subjects
online_rows = "".join(
    f'<tr><td class="cc">{esc(k)}</td><td class="num">{v}</td></tr>'
    for k, v in list(modality["top_online_subjects"].items())[:10]
)


# ----- Build HTML -----
html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>ASU &times; UTK Catalog Comparison</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root {{
    --ink:#1a1a1a;
    --ink-2:#424242;
    --ink-3:#6b6b6b;
    --paper:#fbfaf7;
    --paper-2:#f3f1ea;
    --rule:#d9d5cc;
    --asu:#8c1d40;
    --asu-soft:#b27288;
    --utk:#ff8200;
    --utk-soft:#ffb26b;
    --green:#1a5d3a;
    --rust:#c44536;
    --sand:#e8e2d2;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin:0; padding:0; }}
  body {{
    font-family: "Georgia", "Iowan Old Style", "Palatino Linotype", serif;
    background: var(--paper);
    color: var(--ink);
    line-height: 1.55;
  }}
  .page {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 60px 48px 120px;
  }}
  header.hero {{
    border-bottom: 2px solid var(--ink);
    padding-bottom: 32px;
    margin-bottom: 48px;
  }}
  .eyebrow {{
    text-transform: uppercase;
    letter-spacing: 3px;
    font-size: 12px;
    color: var(--ink-3);
    font-family: "Helvetica Neue", Arial, sans-serif;
    font-weight: 600;
  }}
  h1 {{
    font-size: 52px;
    line-height: 1.1;
    margin: 8px 0 14px;
    font-weight: 500;
    letter-spacing: -0.01em;
  }}
  h1 .amp {{ font-family:"Iowan Old Style", serif; font-style: italic; color: var(--ink-3); font-weight:300; margin:0 8px; }}
  .subtitle {{
    font-size: 18px;
    color: var(--ink-2);
    max-width: 820px;
  }}
  .dateline {{
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
    color: var(--ink-3);
    margin-top: 14px;
  }}

  h2 {{
    font-size: 28px;
    font-weight: 500;
    margin: 64px 0 8px;
    letter-spacing: -0.005em;
    border-top: 1px solid var(--rule);
    padding-top: 32px;
  }}
  h2 .num {{
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
    color: var(--ink-3);
    letter-spacing: 3px;
    display:block;
    text-transform:uppercase;
    margin-bottom:4px;
  }}
  h3 {{
    font-size: 18px;
    font-weight: 600;
    margin: 28px 0 8px;
  }}
  p {{ max-width: 780px; }}
  a {{ color: inherit; }}

  /* Summary tiles */
  .tiles {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 2px;
    background: var(--rule);
    border: 1px solid var(--rule);
    margin: 32px 0 8px;
  }}
  .tile {{
    background: var(--paper);
    padding: 24px 20px;
  }}
  .tile .lbl {{
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--ink-3);
  }}
  .tile .val {{
    font-size: 38px;
    font-weight: 500;
    line-height: 1.1;
    margin-top: 6px;
    letter-spacing:-0.01em;
  }}
  .tile .val small {{ font-size: 14px; color:var(--ink-3); font-weight:400; }}
  .tile .sub {{
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
    color: var(--ink-2);
    margin-top: 6px;
  }}

  /* Stacked overlap bars */
  .overlap-grid {{
    display:grid;
    grid-template-columns: 80px 1fr;
    gap: 12px 16px;
    align-items: center;
    margin: 20px 0;
  }}
  .olabel {{
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-weight: 600;
    font-size: 13px;
  }}
  .stackbar {{
    display:flex;
    height: 28px;
    border: 1px solid var(--ink);
    background: white;
  }}
  .stackbar .seg {{ height: 100%; }}
  .legend {{
    display:flex;
    gap: 18px;
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
    color: var(--ink-2);
    margin-top: 6px;
  }}
  .swatch {{
    display:inline-block; width:12px; height:12px; margin-right:6px; vertical-align:middle;
    border: 1px solid var(--ink);
  }}

  /* Cluster cards */
  .clusters {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin: 24px 0;
  }}
  .cluster {{
    border: 1px solid var(--ink);
    padding: 18px 18px 14px;
    background: white;
  }}
  .cluster.asu {{ border-left: 6px solid var(--asu); }}
  .cluster.utk {{ border-left: 6px solid var(--utk); }}
  .cluster .csize {{
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--ink-3);
  }}
  .cluster .cterms {{
    font-size: 17px;
    margin: 4px 0 6px;
    font-weight: 500;
  }}
  .cluster .csubs, .cluster .meta {{
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
    color: var(--ink-3);
  }}
  .cluster .meta {{ margin-top: 2px; }}
  .cluster ul {{
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    margin: 10px 0 0;
    padding-left: 16px;
    color: var(--ink-2);
  }}
  .cluster ul li {{ margin: 2px 0; }}

  /* Tables */
  table {{
    border-collapse: collapse;
    width: 100%;
    font-size: 14px;
    font-family:"Helvetica Neue", Arial, sans-serif;
  }}
  th {{
    text-align: left;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--ink-3);
    padding: 10px 8px;
    border-bottom: 1px solid var(--ink);
    background: var(--paper-2);
  }}
  td {{
    padding: 10px 8px;
    border-bottom: 1px solid var(--rule);
    vertical-align: top;
  }}
  td.num {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
  td.lvl {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--ink-3); }}
  .cc {{
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 12px;
    color: var(--ink);
    background: var(--paper-2);
    padding: 1px 6px;
    border-radius: 2px;
  }}
  .tt {{ color: var(--ink); }}
  .meta {{
    font-size: 11px;
    color: var(--ink-3);
  }}

  /* Designations */
  .desig {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
    margin-top: 20px;
  }}
  .desig-panel {{
    border: 1px solid var(--ink);
    padding: 18px;
    background: white;
  }}
  .desig-title {{
    font-size: 16px; font-weight: 600; letter-spacing:-0.005em;
  }}
  .desig-sub {{
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
    color: var(--ink-3);
    margin-bottom: 10px;
  }}
  .chips {{ display:flex; flex-wrap: wrap; gap: 6px; }}
  .chip {{
    display:flex;
    align-items: center;
    gap: 6px;
    border: 1px solid var(--rule);
    padding: 4px 8px 4px 4px;
    border-radius: 2px;
    background: var(--paper-2);
  }}
  .chip-code {{
    font-family:"SF Mono", Menlo, monospace;
    font-weight: 700;
    font-size: 12px;
    background: var(--ink);
    color: white;
    padding: 2px 6px;
    border-radius: 2px;
  }}
  .chip-count {{
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
    color: var(--ink-2);
  }}

  /* Recommendation cards */
  .recs {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-top: 20px;
  }}
  .rec {{
    border: 1px solid var(--ink);
    padding: 22px;
    background: white;
  }}
  .rec .rid {{
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-weight:700;
    font-size:12px;
    letter-spacing:2px;
    text-transform: uppercase;
    color: var(--ink-3);
  }}
  .rec h4 {{ margin: 6px 0 6px; font-size:18px; font-weight:600; letter-spacing:-0.005em; }}
  .rec p {{ font-family:"Helvetica Neue", Arial, sans-serif; font-size: 14px; color: var(--ink-2); margin: 0; }}
  .rec .tag {{
    display:inline-block;
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-size: 11px;
    background: var(--sand);
    border: 1px solid var(--rule);
    padding: 2px 8px;
    margin-top: 10px;
    margin-right: 4px;
  }}

  /* Two-column comparison */
  .two-col {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin: 24px 0;
  }}
  .col h3.asu {{ color: var(--asu); }}
  .col h3.utk {{ color: #b85e00; }}

  footer {{
    margin-top: 100px;
    padding-top: 24px;
    border-top: 1px solid var(--rule);
    font-family:"Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
    color: var(--ink-3);
  }}

  @media (max-width: 860px) {{
    .tiles {{ grid-template-columns: repeat(2, 1fr); }}
    .clusters, .desig, .recs, .two-col {{ grid-template-columns: 1fr; }}
    h1 {{ font-size: 36px; }}
    .page {{ padding: 36px 20px 80px; }}
  }}
</style>
</head>
<body>
<div class="page">

<header class="hero">
  <div class="eyebrow">Institutional Research · Course Catalog Analysis</div>
  <h1>Arizona State <span class="amp">&amp;</span> Tennessee–Knoxville</h1>
  <div class="subtitle">A data-driven comparison of {combined:,} courses across both universities' live catalogs, surfacing genuine content overlap, distinctive strengths, and opportunities for joint development between the two institutions.</div>
  <div class="dateline">Prepared April 2026 · ASU 2025–26 catalog · UTK Undergraduate 2026–27, Graduate 2025–26</div>
</header>

<section>
  <h2><span class="num">01</span>At a glance</h2>
  <div class="tiles">
    <div class="tile">
      <div class="lbl">Courses compared</div>
      <div class="val">{combined:,}</div>
      <div class="sub">ASU {asu_total:,} &middot; UTK {utk_total:,}</div>
    </div>
    <div class="tile">
      <div class="lbl">Subjects / programs</div>
      <div class="val">560</div>
      <div class="sub">ASU 333 &middot; UTK 227 distinct subject codes</div>
    </div>
    <div class="tile">
      <div class="lbl">1:1 equivalents</div>
      <div class="val">{mutual_count}<small> / {combined:,}</small></div>
      <div class="sub">Mutual-strong course pairs (&ge; 0.55 cosine, both directions)</div>
    </div>
    <div class="tile">
      <div class="lbl">ASU online offerings</div>
      <div class="val">{modality['asu_total_online']:,}<small> ({modality['asu_online_share_pct']}%)</small></div>
      <div class="sub">UTK: no per-course online flag in catalog</div>
    </div>
  </div>
</section>

<section>
  <h2><span class="num">02</span>How much of each catalog overlaps</h2>
  <p>Every course in each catalog was matched against every course in the other's by TF-IDF cosine similarity on title and description. Administrative shells (Thesis, Dissertation, Special Topics, Seminar, Internship) are bucketed separately to avoid inflating the overlap.</p>

  <div class="overlap-grid">
    <div class="olabel">ASU → UTK</div>
    {stacked_bar("ASU", md["asu_to_utk"], asu_total)}
    <div class="olabel">UTK → ASU</div>
    {stacked_bar("UTK", md["utk_to_asu"], utk_total)}
  </div>
  <div class="legend">
    <span><span class="swatch" style="background:#1a5d3a"></span>Strong (&ge; 0.55)</span>
    <span><span class="swatch" style="background:#6aa889"></span>Moderate (0.30–0.55)</span>
    <span><span class="swatch" style="background:#c44536"></span>Unique (&lt; 0.30)</span>
    <span><span class="swatch" style="background:#9ca3af"></span>Administrative shell</span>
  </div>

  <p style="margin-top: 24px;"><strong>Read:</strong> fewer than 3% of either catalog has a strong content-level counterpart at the other institution. Even when looser “related” content is counted, the majority of each catalog describes teaching that is distinctive to that school. ASU has proportionally more administrative shells — a consequence of its larger graduate research and multi-campus programs that use registration-shell course codes.</p>
</section>

<section>
  <h2><span class="num">03</span>Where the catalogs truly meet</h2>
  <p>{mutual_count} courses pair as clear 1:1 content equivalents: both schools' descriptions point the same direction, and each picks the other as its closest match. These are the cleanest candidates for a reciprocal credit agreement.</p>
  <table>
    <thead>
      <tr><th>Sim.</th><th>ASU</th><th>UTK</th><th>Level</th></tr>
    </thead>
    <tbody>
      {mutual_rows}
    </tbody>
  </table>
  <p class="meta" style="margin-top:12px;">Showing top 60 of {mutual_count} mutual-strong pairs by similarity. Full list in <code>data/analysis/top_mutual_pairs.csv</code>.</p>
</section>

<section>
  <h2><span class="num">04</span>What ASU uniquely teaches</h2>
  <p>Unsupervised clustering of the {asu_unique:,} ASU courses with no strong UTK counterpart surfaces the following themes. These represent the depth ASU brings that UTK does not currently mirror.</p>
  <div class="clusters">
    {''.join(render_cluster(c, "asu") for c in asu_clusters[:8])}
  </div>
</section>

<section>
  <h2><span class="num">05</span>What UTK uniquely teaches</h2>
  <p>The mirror view — themes drawn from the {utk_unique:,} UTK courses with no strong ASU counterpart. Notice the depth in music performance, agricultural sciences, and place-bound environmental studies.</p>
  <div class="clusters">
    {''.join(render_cluster(c, "utk") for c in utk_clusters[:8])}
  </div>
</section>

<section>
  <h2><span class="num">06</span>How the subject codes map across schools</h2>
  <p>UTK subjects that most often point into a single ASU subject — the natural "this-to-that" mapping, ranked by strong/moderate cross-school links.</p>
  <table>
    <thead>
      <tr><th>UTK subject</th><th>Most-linked ASU subject</th><th>ASU college</th><th>Links</th></tr>
    </thead>
    <tbody>{pair_rows}</tbody>
  </table>
</section>

<section>
  <h2><span class="num">07</span>Different philosophies of general education</h2>
  <p>Both schools tag courses that fulfill general-education requirements, but the frameworks reflect different pedagogical bets. ASU organises around traditional discipline buckets. UTK's VolCore puts <em>engaged inquiry</em> at the top of the list — more coursework is tagged EI (Engaged Inquiries) than any other category, signaling a pedagogy of application.</p>
  <div class="desig">
    {render_desig_panel("ASU_GS_GOLD", gs_gold_rows, "ASU — General Studies (Gold, current track)", f"{designations['asu_general_studies_tagged_courses']:,} courses tagged")}
    {render_desig_panel("UTK_VOLCORE", volcore_rows, "UTK — Volunteer Core (VolCore)", f"{designations['utk_volcore_tagged_courses']:,} courses tagged")}
  </div>
  <p style="margin-top:18px;"><strong>Points of convergence</strong>: both schools tag Written Communication, Arts &amp; Humanities, Social/Behavioral Sciences, Natural Sciences, and Global awareness. <strong>Points of divergence</strong>: UTK uniquely surfaces <em>Engaged Inquiries</em> (EI), <em>Applied Oral Communication</em> (AOC), and <em>Applied Arts &amp; Humanities</em> (AAH). ASU uniquely carries <em>Literacy and Critical Inquiry</em> (L) and a <em>Humanities Core</em> (HC) bucket. Cross-walking UTK's VolCore into an ASU equivalency is possible but UTK's applied categories have no clean ASU analog.</p>
</section>

<section>
  <h2><span class="num">08</span>The modality asymmetry</h2>
  <p>ASU reports {modality['asu_total_online']:,} online-delivered courses across its catalog, concentrated in professional and applied subjects. UTK's course catalog does not tag per-course modality; online delivery is recorded only in the Banner section timetable. For joint programs, this means ASU's online infrastructure is a substantial asset UTK could leverage.</p>
  <div class="two-col">
    <div class="col">
      <h3 class="asu">ASU subjects with the most online sections</h3>
      <table>
        <thead><tr><th>Subject</th><th>Online courses</th></tr></thead>
        <tbody>{online_rows}</tbody>
      </table>
    </div>
    <div class="col">
      <h3 class="utk">UTK online visibility</h3>
      <p style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;">The UTK catalog's <a href="https://catalog.utk.edu">preview_course pages</a> do not identify individual online sections. Distance-education offerings are captured at the <em>program</em> level on catalog.utk.edu, while section-level modality lives on the Banner timetable. A complete parity view would require pulling the Banner feed term-by-term, outside the scope of this catalog comparison.</p>
    </div>
  </div>
</section>

<section>
  <h2><span class="num">09</span>Opportunities for joint development</h2>
  <p>Five opportunities surfaced by the analysis, ordered from most-immediate to most-ambitious.</p>
  <div class="recs">

    <div class="rec">
      <div class="rid">Opportunity 01</div>
      <h4>Reciprocal-credit compact on {mutual_count} paired courses</h4>
      <p>The mutual-strong pairs cover foundational Law (Federal Courts, Criminal Law, Secured Transactions), core Math (Abstract Algebra, Combinatorics), Engineering foundations (Heat Transfer, CFD, Tissue Engineering), Linguistics/Language acquisition, Music performance fundamentals, and shared Humanities (Hebrew Bible, History of Film). A published crosswalk would remove re-evaluation friction for transfer students and study-abroad equivalencies.</p>
      <span class="tag">Fast</span><span class="tag">Registrar-led</span><span class="tag">Low risk</span>
    </div>

    <div class="rec">
      <div class="rid">Opportunity 02</div>
      <h4>Online-campus complement in applied health &amp; professional programs</h4>
      <p>ASU's online presence is strongest in PSY, CRJ, HCR (health care), PAF (public affairs), and BIO. UTK's applied and clinical programs (NURS, health sciences) are largely campus-delivered. A hybrid model — UTK campus practicum + ASU online didactic — could expand UTK program capacity without building new online infrastructure at UTK, while giving ASU a residential practicum partner.</p>
      <span class="tag">Medium term</span><span class="tag">Revenue share</span>
    </div>

    <div class="rec">
      <div class="rid">Opportunity 03</div>
      <h4>UTK-led certificate in music performance, online-delivered at ASU's reach</h4>
      <p>UTK's {next((c['size'] for c in utk_clusters if 'ensemble' in ' '.join(c['top_terms']).lower()), 800)}-course cluster on music ensembles, instrumental methods, and conducting is markedly deeper than ASU's. A UTK-curated stackable certificate in applied music performance, distributed through ASU's online learning platform, would monetize UTK content at ASU's audience scale.</p>
      <span class="tag">Content IP</span><span class="tag">Joint branding</span>
    </div>

    <div class="rec">
      <div class="rid">Opportunity 04</div>
      <h4>Agri-environmental bridge: ASU breadth × UTK depth</h4>
      <p>UTK's Forestry (FORS), Wildlife &amp; Fisheries (WFS), Plant Sciences (PLSC), and Animal Science (ANSC) are unmatched at ASU. ASU's Environmental and Sustainability breadth (SOS, EEE environmental engineering) provides frameworks UTK lacks at equivalent scale. A joint dual-listed graduate certificate in applied agro-ecology, with courses co-taught or cross-listed, leverages both in a growing employer space.</p>
      <span class="tag">Graduate</span><span class="tag">Sustainability</span>
    </div>

    <div class="rec">
      <div class="rid">Opportunity 05</div>
      <h4>Applied-engaged micro-credential mapped to both gen-ed systems</h4>
      <p>UTK's VolCore Engaged Inquiries (EI, 232 courses) and Applied Oral Communication (AOC, 96) categories have no direct ASU analog. Jointly designing a dual-tagged micro-credential whose capstone counts for UTK EI <em>and</em> ASU upper-division Literacy (L) addresses both frameworks at once. Differentiator: a transcript tag from both institutions on one credential.</p>
      <span class="tag">Pedagogical IP</span><span class="tag">Ambitious</span>
    </div>

    <div class="rec">
      <div class="rid">Opportunity 06</div>
      <h4>Specialty program swap: Aviation/ATC at ASU, Architecture design at UTK</h4>
      <p>ASU's Air Traffic Control (ATC), Aviation Management (AMT), and Aerospace Engineering (AEE, AEP) curricula are unmatched at UTK. UTK's six-year Architecture (ARCH) design studio sequence is unmatched at ASU. Formal articulation agreements would let interested students complete specialized tracks at the partner school without a separate admissions process.</p>
      <span class="tag">Low volume</span><span class="tag">High specificity</span>
    </div>
  </div>
</section>

<section>
  <h2><span class="num">10</span>Limitations &amp; caveats</h2>
  <ul style="font-family:'Helvetica Neue',Arial,sans-serif; font-size:14px; color:var(--ink-2); max-width:780px; line-height:1.6;">
    <li><strong>Catalog year mismatch.</strong> ASU and UTK-grad use 2025–26; UTK-undergrad uses 2026–27. Course churn between years affects roughly 3–5% of lines in a typical catalog; treat counts as indicative rather than exact.</li>
    <li><strong>TF-IDF similarity</strong> is a lexical signal, not a true semantic reading. Courses with distinct vocabulary but overlapping pedagogy can appear "unique" when they are substantively related. The mutual-strong filter (316 pairs) is the most defensible number.</li>
    <li><strong>Generic shells.</strong> Admin courses (Thesis, Special Topics, Seminar) were identified heuristically. A small number of genuine courses may be mis-classified; the bucket is reported separately rather than discarded.</li>
    <li><strong>Modality.</strong> ASU's online flag is drawn from the Spring/Summer 2026 term sections. UTK per-course modality is not published in the catalog. A complete parity view requires a Banner-timetable pull.</li>
    <li><strong>Subject code mapping</strong> was learned from data — the strongest-linked ASU subject for each UTK subject — rather than a CIP code crosswalk. This captures how the schools <em>actually</em> teach similar content, not a standards-body taxonomy. It trades accuracy for fidelity to real offerings.</li>
  </ul>
</section>

<footer>
  Built from a complete scrape of both live catalogs — 23,948 course records across 560 subject codes — on 24 April 2026.
  Source data and analysis scripts in <code>catalog-compare/</code>.
</footer>

</div>
</body>
</html>"""


OUT_HTML.write_text(html_doc, encoding="utf-8")
print(f"Wrote {OUT_HTML} ({len(html_doc):,} bytes)")
