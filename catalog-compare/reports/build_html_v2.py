"""v2 HTML report — reframed around three layers (reciprocal credit /
joint development / distinctive marquee), with expandable drawers for
each subject and a slide-out side panel for full-course drill-down.

Uses sentence-transformer-based analysis from data/analysis_v2/.
Modality is demoted to a short caveat, not a central frame.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
IN = DATA / "analysis_v2"
OUT_HTML = HERE / "catalog_comparison.html"


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def load(p):
    return json.loads(p.read_text())


def readl(p):
    out = []
    with p.open() as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


summary = load(IN / "summary.json")
asu_colleges = load(IN / "asu_by_college.json")
distinctive = load(IN / "distinctive_leaders.json")
overlap = load(IN / "overlap_leaders.json")
utk_subjects_all = load(IN / "utk_subjects.json")
mutual = readl(IN / "mutual_strong_pairs.jsonl")

c = summary["counts"]
md = summary["match_distribution"]
asu_total = c["asu_total"]
utk_total = c["utk_total"]
combined = asu_total + utk_total
mutual_count = summary["mutual_strong_count"]


# ─── helpers for rendering ───────────────────────────────────────────────
def pct_bar(strong, moderate, unique, total, shell=None):
    if not total:
        return ""
    segs = []
    for label, count, color in [
        ("Strong reciprocal", strong, "#1a5d3a"),
        ("Moderate / joint-dev", moderate, "#6aa889"),
        ("Distinctive marquee", unique, "#c44536"),
    ] + ([("Admin shell", shell, "#9ca3af")] if shell else []):
        if count:
            w = 100 * count / total
            segs.append(
                f'<div class="seg" style="width:{w:.2f}%;background:{color}" '
                f'title="{esc(label)}: {count:,} ({w:.1f}%)"></div>'
            )
    return '<div class="stackbar">' + "".join(segs) + "</div>"


def course_list_html(courses, show_match=False, school="ASU"):
    if not courses:
        return '<div class="no-courses">No courses in this bucket.</div>'
    other = "UTK" if school == "ASU" else "ASU"
    primary_cls = "asu-cc" if school == "ASU" else "utk-cc"
    other_cls = "utk-cc" if school == "ASU" else "asu-cc"
    rows = []
    for c in courses:
        match_bit = ""
        if show_match and c.get("best_code"):
            match_bit = (
                f'<div class="match-ref">matches {other} '
                f'<span class="cc {other_cls}">{esc(c["best_code"])}</span> '
                f'{esc(c["best_title"])} '
                f'<span class="sim">{c.get("best_sim", 0):.2f}</span></div>'
            )
        desc = esc(c.get("description") or "").strip()
        if not desc:
            desc = '<span class="no-desc">(no description)</span>'
        rows.append(
            f"""
            <div class="course-item">
              <div class="course-head">
                <span class="cc {primary_cls}">{esc(c["course_code"])}</span>
                <span class="course-title">{esc(c["title"])}</span>
                <span class="lvl-tag">{esc(c.get("level") or "")}</span>
              </div>
              <div class="course-desc">{desc}</div>
              {match_bit}
            </div>
            """
        )
    return '<div class="course-list">' + "".join(rows) + "</div>"


def subject_card(s, side="asu"):
    """Render a subject with collapsible drawer. Buckets ordered distinctive →
    moderate → strong (the most-distinctive content is most interesting and
    smallest in count). Empty buckets are skipped entirely."""
    sid = f"{side}-{s['subject']}"
    school = "ASU" if side.startswith("asu") else "UTK"
    other = "UTK" if school == "ASU" else "ASU"
    primary_cls = "asu-cc" if school == "ASU" else "utk-cc"

    college_bit = (
        f'<div class="subject-college">{esc(s["college"])}</div>' if s.get("college") else ""
    )
    partner_bit = ""
    if s.get("partner_subject"):
        partner_cls = "utk-cc" if school == "ASU" else "asu-cc"
        partner_bit = (
            f'<div class="partner">pairs most with <span class="cc {partner_cls}">{esc(other)} {esc(s["partner_subject"])}</span> '
            f'({s["partner_links"]} links)</div>'
        )

    buckets_html = []
    if s["unique"]:
        buckets_html.append(f"""
        <div class="bucket">
          <div class="bucket-head bucket-unique">
            <h4>Distinctive &mdash; {school} courses with no near {other} counterpart</h4>
            <span class="bucket-count">{s["unique"]} course{'s' if s["unique"] != 1 else ''}</span>
          </div>
          {course_list_html(s["sample_unique"], show_match=False, school=school)}
        </div>""")
    if s["moderate"]:
        buckets_html.append(f"""
        <div class="bucket">
          <div class="bucket-head bucket-moderate">
            <h4>Moderate &mdash; {school} courses with thematically adjacent {other} counterparts</h4>
            <span class="bucket-count">{s["moderate"]} course{'s' if s["moderate"] != 1 else ''}</span>
          </div>
          {course_list_html(s["sample_moderate"], show_match=True, school=school)}
        </div>""")
    if s["strong"]:
        buckets_html.append(f"""
        <div class="bucket">
          <div class="bucket-head bucket-strong">
            <h4>Strong &mdash; {school} courses with direct {other} counterparts</h4>
            <span class="bucket-count">{s["strong"]} course{'s' if s["strong"] != 1 else ''}</span>
          </div>
          {course_list_html(s["sample_strong"], show_match=True, school=school)}
        </div>""")

    return f"""
    <details class="subject-card" id="{esc(sid)}">
      <summary>
        <div class="subject-head">
          <div class="subject-main">
            <span class="cc lg {primary_cls}">{esc(s["subject"])}</span>
            <span class="subject-total">{s["total"]} courses</span>
            {college_bit}
          </div>
          <div class="subject-bar-wrap">
            {pct_bar(s["strong"], s["moderate"], s["unique"], s["total"])}
            <div class="subject-legend">
              <span class="mini-lbl"><span class="swatch" style="background:#1a5d3a"></span>{s["strong"]} strong ({s["strong_pct"]}%)</span>
              <span class="mini-lbl"><span class="swatch" style="background:#6aa889"></span>{s["moderate"]} moderate ({s["moderate_pct"]}%)</span>
              <span class="mini-lbl"><span class="swatch" style="background:#c44536"></span>{s["unique"]} distinctive ({s["unique_pct"]}%)</span>
            </div>
            {partner_bit}
          </div>
          <span class="chevron">▾</span>
        </div>
      </summary>
      <div class="subject-body">
        {''.join(buckets_html)}
      </div>
    </details>
    """


# ─── compute headline stats ─────────────────────────────────────────────
strong_both = md["asu_to_utk"].get("strong", 0) + md["utk_to_asu"].get("strong", 0)
moderate_both = md["asu_to_utk"].get("moderate", 0) + md["utk_to_asu"].get("moderate", 0)
unique_both = md["asu_to_utk"].get("unique", 0) + md["utk_to_asu"].get("unique", 0)
non_generic_total = strong_both + moderate_both + unique_both

asu_strong_pct = (md["asu_to_utk"].get("strong", 0) / max(1, asu_total)) * 100
utk_strong_pct = (md["utk_to_asu"].get("strong", 0) / max(1, utk_total)) * 100


# Mutual pairs for backbone display
mutual_rows = "".join(
    f"""<tr>
      <td class="num">{p["similarity"]:.2f}</td>
      <td><span class="cc asu-cc">{esc(p["asu_code"])}</span> {esc(p["asu_title"])}<br><span class="meta">{esc(p.get("asu_college") or "")}</span></td>
      <td><span class="cc utk-cc">{esc(p["utk_code"])}</span> {esc(p["utk_title"])}</td>
      <td class="lvl">{esc(p["asu_level"])}</td>
    </tr>"""
    for p in mutual[:40]
)

# Full mutual pairs for the modal — all 1,619
all_mutual_rows = "".join(
    f"""<tr>
      <td class="num">{p["similarity"]:.2f}</td>
      <td><span class="cc asu-cc">{esc(p["asu_code"])}</span> {esc(p["asu_title"])}</td>
      <td><span class="cc utk-cc">{esc(p["utk_code"])}</span> {esc(p["utk_title"])}</td>
      <td class="lvl">{esc(p["asu_level"])}</td>
    </tr>"""
    for p in mutual
)

# Prepare all-subjects JSON for side-panel JS drill-down
all_subjects_data = {
    "asu_colleges": asu_colleges,
    "utk_subjects": utk_subjects_all,
}
embedded_json = json.dumps(all_subjects_data, separators=(",", ":"))


html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>ASU × UTK Catalog Comparison</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root {{
    --ink:#1a1a1a; --ink-2:#424242; --ink-3:#6b6b6b;
    --paper:#fbfaf7; --paper-2:#f3f1ea; --rule:#d9d5cc;
    --asu:#8c1d40; --asu-soft:#b27288;
    --utk:#ff8200; --utk-soft:#ffb26b;
    --green:#1a5d3a; --green-soft:#6aa889;
    --rust:#c44536; --sand:#e8e2d2;
  }}
  *, *::before, *::after {{ box-sizing: border-box; }}
  html, body {{ margin:0; padding:0; }}
  body {{
    font-family: "Georgia", "Iowan Old Style", "Palatino Linotype", serif;
    background: var(--paper);
    color: var(--ink);
    line-height: 1.55;
  }}
  .page {{ max-width: 1180px; margin: 0 auto; padding: 60px 48px 120px; }}
  header.hero {{ border-bottom: 2px solid var(--ink); padding-bottom: 32px; margin-bottom: 48px; }}
  .eyebrow {{ text-transform: uppercase; letter-spacing: 3px; font-size: 12px; color: var(--ink-3);
              font-family: "Helvetica Neue", Arial, sans-serif; font-weight: 600; }}
  h1 {{ font-size: 52px; line-height: 1.08; margin: 8px 0 14px; font-weight: 500; letter-spacing: -0.01em; }}
  h1 .amp {{ font-family:"Iowan Old Style", serif; font-style: italic; color: var(--ink-3); font-weight:300; margin:0 8px; }}
  .subtitle {{ font-size: 18px; color: var(--ink-2); max-width: 820px; }}
  .dateline {{ font-family:"Helvetica Neue", Arial, sans-serif; font-size: 12px; color: var(--ink-3); margin-top: 14px; }}
  h2 {{ font-size: 28px; font-weight: 500; margin: 64px 0 8px; letter-spacing: -0.005em;
        border-top: 1px solid var(--rule); padding-top: 32px; }}
  h2 .num {{ font-family:"Helvetica Neue", Arial, sans-serif; font-size: 12px; color: var(--ink-3);
             letter-spacing: 3px; display:block; text-transform:uppercase; margin-bottom:4px; }}
  h3 {{ font-size: 19px; font-weight: 600; margin: 26px 0 8px; }}
  p {{ max-width: 820px; }}

  /* Summary tiles — 3 layer frame */
  .layer-tiles {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px;
    background: var(--rule); border: 1px solid var(--ink); margin: 32px 0 8px;
  }}
  .tile {{ background: var(--paper); padding: 24px 20px; position: relative; }}
  .tile.strong {{ border-top: 6px solid var(--green); }}
  .tile.moderate {{ border-top: 6px solid var(--green-soft); }}
  .tile.unique {{ border-top: 6px solid var(--rust); }}
  .tile .lbl {{ font-family:"Helvetica Neue", Arial, sans-serif; font-size: 11px;
                letter-spacing: 2px; text-transform: uppercase; color: var(--ink-3); font-weight: 600; }}
  .tile .val {{ font-size: 42px; font-weight: 500; line-height: 1.05; margin-top: 8px; letter-spacing:-0.01em; }}
  .tile .val small {{ font-size: 14px; color:var(--ink-3); font-weight:400; }}
  .tile .lead {{ font-size: 15px; margin-top: 10px; max-width: none; }}
  .tile .sub {{ font-family:"Helvetica Neue", Arial, sans-serif; font-size: 12px;
                color: var(--ink-2); margin-top: 12px; }}

  /* Overlap bar */
  .overlap-grid {{ display:grid; grid-template-columns: 100px 1fr; gap: 12px 16px; align-items: center; margin: 24px 0 10px; }}
  .olabel {{ font-family:"Helvetica Neue", Arial, sans-serif; font-weight: 600; font-size: 13px; }}
  .stackbar {{ display:flex; height: 24px; border: 1px solid var(--ink); background: white; }}
  .stackbar .seg {{ height: 100%; }}
  .legend {{ display:flex; flex-wrap: wrap; gap: 18px;
             font-family:"Helvetica Neue", Arial, sans-serif; font-size: 12px; color: var(--ink-2); margin-top: 6px; }}
  .swatch {{ display:inline-block; width:12px; height:12px; margin-right:6px;
             vertical-align:middle; border: 1px solid var(--ink); }}

  /* Mutual pairs table */
  table {{ border-collapse: collapse; width: 100%; font-size: 14px;
           font-family:"Helvetica Neue", Arial, sans-serif; }}
  th {{ text-align: left; font-weight: 600; font-size: 11px; letter-spacing: 2px;
        text-transform: uppercase; color: var(--ink-3); padding: 10px 8px;
        border-bottom: 1px solid var(--ink); background: var(--paper-2); }}
  td {{ padding: 10px 8px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
  td.num {{ font-variant-numeric: tabular-nums; white-space: nowrap; font-weight: 600; color: var(--green); }}
  td.lvl {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--ink-3); }}
  .cc {{ font-family: "SF Mono", "Menlo", monospace; font-size: 12px; color: var(--ink);
         background: var(--paper-2); padding: 1px 6px; border-radius: 2px; font-weight: 600; }}
  .cc.lg {{ font-size: 14px; padding: 3px 10px; }}
  .cc.asu-cc {{ background: #f3e1e7; color: var(--asu); }}
  .cc.utk-cc {{ background: #ffe9d1; color: #b85e00; }}
  .meta {{ font-size: 11px; color: var(--ink-3); }}

  /* Subject cards with drawers */
  .college-block {{
    border: 1px solid var(--ink); background: white; margin: 16px 0;
    padding: 0;
  }}
  .college-block > summary {{
    padding: 0; cursor: pointer; list-style: none;
  }}
  .college-block > summary::-webkit-details-marker {{ display: none; }}
  .college-block > summary:hover .college-name {{ color: var(--asu); }}
  .college-block[open] > summary {{ border-bottom: 1px solid var(--rule); }}
  .college-head {{
    padding: 20px 24px;
    background: var(--paper-2);
    display: grid; grid-template-columns: 1fr auto auto; gap: 16px; align-items: center;
  }}
  .college-name {{ font-size: 20px; font-weight: 600; transition: color 0.15s; }}
  .college-stats {{ font-family:"Helvetica Neue", Arial, sans-serif; font-size: 13px;
                    color: var(--ink-2); margin-top: 4px; }}
  .college-bar {{ width: 340px; }}
  .subject-list {{ padding: 8px 24px 16px; }}
  .subject-card {{ border-bottom: 1px solid var(--rule); padding: 0; }}
  .subject-card:last-child {{ border-bottom: none; }}
  .subject-card summary {{ cursor: pointer; padding: 14px 0; list-style: none; }}
  .subject-card summary::-webkit-details-marker {{ display: none; }}
  .subject-head {{ display: grid; grid-template-columns: 2fr 3fr 0.4fr; gap: 16px;
                    align-items: center; }}
  .subject-main {{ display: flex; flex-direction: column; gap: 4px; align-items: flex-start; }}
  .school-pill {{
    display: inline-block;
    font-family:"Helvetica Neue",Arial,sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    padding: 2px 8px;
    border-radius: 2px;
    text-transform: uppercase;
    margin-bottom: 2px;
  }}
  .school-pill-asu {{ background: var(--asu); color: white; }}
  .school-pill-utk {{ background: var(--utk); color: white; }}
  .school-pill.lg {{ font-size: 12px; padding: 4px 10px; }}
  .subject-total {{ font-family:"Helvetica Neue", Arial, sans-serif;
                     font-size: 13px; color: var(--ink-2); margin-top: 2px; }}
  .subject-college {{ font-family:"Helvetica Neue", Arial, sans-serif;
                      font-size: 11px; color: var(--ink-3); }}
  .subject-bar-wrap {{ display: flex; flex-direction: column; gap: 5px; }}
  .subject-legend {{ display: flex; gap: 14px; font-family:"Helvetica Neue",Arial,sans-serif;
                     font-size: 11px; color: var(--ink-3); }}
  .subject-legend .swatch {{ width: 9px; height: 9px; }}
  .partner {{ font-family:"Helvetica Neue",Arial,sans-serif; font-size: 11px; color: var(--ink-3); font-style: italic; }}
  .chevron {{
    display: inline-block;
    width: 1.4em; height: 1.4em;
    line-height: 1.4em;
    text-align: center;
    font-family:"Helvetica Neue",Arial,sans-serif;
    color: var(--ink-2);
    font-size: 20px;
    font-weight: 700;
    transition: transform 0.2s ease;
    transform-origin: 50% 50%;
    justify-self: end;
  }}
  .subject-card > summary > .subject-head > .chevron,
  .subject-card[open] > summary > .subject-head > .chevron {{ }}
  details[open] > summary .chevron {{ transform: rotate(180deg); }}
  .subject-body {{ padding: 12px 0 20px 0; }}
  .bucket {{ margin-top: 18px; border: 1px solid var(--rule); }}
  .bucket-head {{ display: flex; justify-content: space-between; align-items: baseline;
                  padding: 10px 14px; font-family:"Helvetica Neue",Arial,sans-serif; }}
  .bucket-head h4 {{ margin: 0; font-size: 13px; font-weight: 700;
                     letter-spacing: 1.5px; text-transform: uppercase; }}
  .bucket-count {{ font-size: 11px; color: var(--ink-3); }}
  .bucket-strong {{ background: #e8f3ec; border-bottom: 2px solid var(--green); }}
  .bucket-strong h4 {{ color: var(--green); }}
  .bucket-moderate {{ background: #eef3ec; border-bottom: 2px solid var(--green-soft); }}
  .bucket-moderate h4 {{ color: var(--green-soft); }}
  .bucket-unique {{ background: #f9e7e3; border-bottom: 2px solid var(--rust); }}
  .bucket-unique h4 {{ color: var(--rust); }}
  .course-list {{ padding: 8px 14px 14px; }}
  .course-item {{ padding: 10px 0; border-bottom: 1px solid var(--paper-2); }}
  .course-item:last-child {{ border-bottom: none; }}
  .course-head {{ display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }}
  .course-title {{ font-family: "Georgia", serif; font-weight: 600; font-size: 15px; }}
  .lvl-tag {{ font-family:"Helvetica Neue",Arial,sans-serif; font-size: 10px;
              text-transform: uppercase; letter-spacing: 1px; color: var(--ink-3); }}
  .course-desc {{ font-family:"Helvetica Neue",Arial,sans-serif; font-size: 13px;
                  color: var(--ink-2); margin-top: 4px; max-width: none; }}
  .no-desc {{ color: var(--ink-3); font-style: italic; }}
  .match-ref {{ font-family:"Helvetica Neue",Arial,sans-serif; font-size: 12px;
                color: var(--ink-3); margin-top: 6px; }}
  .match-ref .sim {{ color: var(--green); font-weight: 700; }}
  .no-courses {{ padding: 14px; font-family:"Helvetica Neue",Arial,sans-serif;
                 font-size: 13px; color: var(--ink-3); font-style: italic; text-align: center; }}

  /* Side panel drawer */
  .side-panel-overlay {{
    position: fixed; inset: 0; background: rgba(0,0,0,0.3);
    opacity: 0; pointer-events: none; transition: opacity 0.2s; z-index: 99;
  }}
  .side-panel-overlay.active {{ opacity: 1; pointer-events: auto; }}
  .side-panel {{
    position: fixed; top: 0; right: 0; bottom: 0; width: min(720px, 96vw);
    background: var(--paper); border-left: 2px solid var(--ink);
    box-shadow: -4px 0 16px rgba(0,0,0,0.15); z-index: 100;
    transform: translateX(100%); transition: transform 0.25s;
    overflow-y: auto; padding: 28px 32px 60px;
  }}
  .side-panel.active {{ transform: translateX(0); }}
  .side-panel h3 {{ margin-top: 0; font-size: 22px; }}
  .side-panel .close {{
    position: absolute; top: 16px; right: 20px;
    background: none; border: none; font-family:"Helvetica Neue",Arial,sans-serif;
    font-size: 20px; color: var(--ink-2); cursor: pointer;
  }}

  /* Recommendation cards */
  .recs {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 20px; }}
  .rec {{ border: 1px solid var(--ink); padding: 22px; background: white; position: relative; }}
  .rec::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 5px; background: var(--asu); }}
  .rec:nth-child(2)::before {{ background: var(--utk); }}
  .rec:nth-child(3)::before {{ background: var(--green); }}
  .rec:nth-child(4)::before {{ background: var(--rust); }}
  .rec:nth-child(5)::before {{ background: #2c3e7a; }}
  .rec .rid {{ font-family:"Helvetica Neue", Arial, sans-serif; font-weight:700;
               font-size:12px; letter-spacing:2px; text-transform: uppercase; color: var(--ink-3); }}
  .rec h4 {{ margin: 8px 0 8px; font-size:18px; font-weight:600; letter-spacing:-0.005em; }}
  .rec p {{ font-family:"Helvetica Neue", Arial, sans-serif; font-size: 14px; color: var(--ink-2); margin: 0; }}
  .rec .evidence {{ font-family:"Helvetica Neue", Arial, sans-serif; font-size: 12px;
                     color: var(--ink-3); margin-top: 12px; padding-top: 10px;
                     border-top: 1px dashed var(--rule); font-style: italic; }}
  .rec .tag {{ display:inline-block; font-family:"Helvetica Neue",Arial,sans-serif;
               font-size: 11px; background: var(--sand); border: 1px solid var(--rule);
               padding: 2px 8px; margin-top: 10px; margin-right: 4px; }}

  /* Distinctive leaders */
  .leader-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 20px; }}
  .leader-col h3 {{ margin-top: 0; padding-bottom: 8px; border-bottom: 2px solid var(--rule); }}
  .leader-col.asu h3 {{ border-color: var(--asu); color: var(--asu); }}
  .leader-col.utk h3 {{ border-color: var(--utk); color: #b85e00; }}

  /* Footer */
  footer {{ margin-top: 100px; padding-top: 24px; border-top: 1px solid var(--rule);
            font-family:"Helvetica Neue", Arial, sans-serif; font-size: 12px; color: var(--ink-3); }}

  /* "View all" button + modal dialog */
  .view-all-btn {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    margin-top: 16px;
    padding: 12px 22px;
    background: var(--ink);
    color: white;
    border: none;
    font-family:"Helvetica Neue",Arial,sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    cursor: pointer;
    transition: background 0.15s;
  }}
  .view-all-btn:hover {{ background: var(--asu); }}
  .view-all-btn .arrow {{ font-size: 16px; }}
  dialog.all-pairs {{
    width: min(1100px, 92vw);
    max-width: 1100px;
    height: 86vh;
    padding: 0;
    border: 2px solid var(--ink);
    background: var(--paper);
    color: var(--ink);
    box-shadow: 0 24px 60px rgba(0,0,0,0.25);
  }}
  dialog.all-pairs::backdrop {{
    background: rgba(0,0,0,0.5);
    backdrop-filter: blur(2px);
  }}
  dialog.all-pairs .dlg-head {{
    position: sticky; top: 0; z-index: 2;
    display: grid; grid-template-columns: 1fr auto;
    align-items: center; gap: 16px;
    padding: 18px 24px;
    background: white;
    border-bottom: 1px solid var(--ink);
  }}
  dialog.all-pairs .dlg-title {{
    font-family:"Georgia",serif; font-size: 20px; font-weight: 600;
    margin: 0;
  }}
  dialog.all-pairs .dlg-sub {{
    font-family:"Helvetica Neue",Arial,sans-serif;
    font-size: 12px; color: var(--ink-3); margin-top: 2px;
  }}
  dialog.all-pairs .dlg-close {{
    width: 36px; height: 36px;
    border: 1px solid var(--ink);
    background: white;
    color: var(--ink);
    font-size: 22px; line-height: 1;
    cursor: pointer;
    transition: background 0.15s;
  }}
  dialog.all-pairs .dlg-close:hover {{ background: var(--ink); color: var(--gold); color: white; }}
  dialog.all-pairs .dlg-body {{
    height: calc(86vh - 70px);
    overflow-y: auto;
    padding: 0;
  }}
  dialog.all-pairs .dlg-body table {{ margin: 0; }}
  dialog.all-pairs .dlg-body th {{
    position: sticky; top: 0; z-index: 1;
    background: var(--paper-2);
  }}
  dialog.all-pairs .filter-bar {{
    position: sticky; top: 0; z-index: 1;
    padding: 10px 24px;
    background: var(--paper-2);
    border-bottom: 1px solid var(--rule);
    font-family:"Helvetica Neue",Arial,sans-serif;
    display: grid; grid-template-columns: 1fr auto;
    align-items: center; gap: 12px;
  }}
  dialog.all-pairs .filter-bar input {{
    width: 100%; max-width: 360px;
    padding: 8px 12px;
    border: 1px solid var(--rule);
    background: white;
    font-family:"Helvetica Neue",Arial,sans-serif;
    font-size: 13px;
  }}
  dialog.all-pairs .filter-bar .count {{
    font-size: 12px; color: var(--ink-3);
  }}

  /* big-table collapse */
  details.big-table {{
    border: 1px solid var(--ink);
    background: white;
    margin-top: 18px;
  }}
  details.big-table > summary {{
    padding: 14px 18px;
    cursor: pointer;
    list-style: none;
    background: var(--paper-2);
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: center;
    transition: background 0.15s;
  }}
  details.big-table > summary::-webkit-details-marker {{ display: none; }}
  details.big-table > summary:hover {{ background: #ebe7dd; }}
  details.big-table[open] > summary {{ border-bottom: 1px solid var(--rule); }}
  details.big-table .big-table-label {{
    font-family:"Helvetica Neue",Arial,sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--ink-2);
  }}
  details.big-table .big-table-body {{ padding: 16px 18px; }}

  /* view-more opps */
  details.more-opps > summary {{
    cursor: pointer; list-style: none;
    margin: 28px 0 0;
    padding: 14px 24px;
    background: var(--paper-2); border: 1px solid var(--ink);
    display: grid; grid-template-columns: 1fr auto;
    font-family:"Helvetica Neue",Arial,sans-serif;
    font-weight: 600; font-size: 14px; letter-spacing: 0.5px;
    color: var(--ink); transition: background 0.15s;
  }}
  details.more-opps > summary::-webkit-details-marker {{ display: none; }}
  details.more-opps > summary:hover {{ background: #ebe7dd; }}
  details.more-opps[open] > summary {{ border-bottom: 1px solid var(--rule); }}
  details.more-opps > .more-opps-body {{
    padding: 20px 0 0;
  }}

  /* caveat box */
  .caveat {{ border: 1px solid var(--rule); background: var(--paper-2); padding: 16px 20px;
             margin: 20px 0; font-family:"Helvetica Neue", Arial, sans-serif; font-size: 13px; color: var(--ink-2); }}
  .caveat strong {{ color: var(--ink); }}

  @media (max-width: 860px) {{
    .layer-tiles, .leader-grid, .recs {{ grid-template-columns: 1fr; }}
    h1 {{ font-size: 36px; }}
    .page {{ padding: 36px 20px 80px; }}
    .subject-head {{ grid-template-columns: 1fr; }}
    .college-head {{ grid-template-columns: 1fr; }}
    .college-bar {{ width: 100%; }}
  }}
</style>
</head>
<body>
<div class="page">

<header class="hero">
  <div class="eyebrow">Institutional Research · Course Catalog Analysis</div>
  <h1>Arizona State <span class="amp">&amp;</span> Tennessee–Knoxville</h1>
  <div class="subtitle">A comparison of {combined:,} courses across both universities' live catalogs.</div>
  <div class="dateline">Prepared April 2026 · ASU 2025–26 catalog · UTK Undergraduate 2026–27, Graduate 2025–26</div>
</header>

<section>
  <h2><span class="num">01</span>The three layers of overlap</h2>
  <p>Every course in both catalogs was embedded with a sentence-transformer model (all-MiniLM-L6-v2) and matched by cosine similarity against every course at the other school. Using semantic similarity rather than keyword matching surfaces substantially more thematic overlap: the catalogs meet more than a lexical read suggested.</p>

  <div class="layer-tiles">
    <div class="tile strong">
      <div class="lbl">Strong — Reciprocal credit</div>
      <div class="val">{mutual_count:,}<small> mutual pairs</small></div>
      <div class="lead">Courses where each school's description points to the same content and each picks the other as its closest match (&ge; 0.70 cosine, both directions).</div>
      <div class="sub">Includes Federal Courts ↔ Federal Courts (0.95), Operating Systems ↔ Operating Systems (0.93), Jazz Pedagogy ↔ Jazz Pedagogy (0.93). Ready for a published crosswalk.</div>
    </div>
    <div class="tile moderate">
      <div class="lbl">Moderate — Joint development</div>
      <div class="val">~{(md["asu_to_utk"].get("moderate", 0) + md["utk_to_asu"].get("moderate", 0)) // 2:,}<small> courses each side</small></div>
      <div class="lead">Courses with a thematically adjacent but not identical counterpart (0.50–0.70). Same field, different emphasis. The space where co-designed curriculum, stackable certificates, and cross-enrollment create real value.</div>
      <div class="sub">Example: ASU Distributed Systems ↔ UTK Operating Systems; ASU Actuarial Models ↔ UTK Actuarial Science Problems in Financial Math.</div>
    </div>
    <div class="tile unique">
      <div class="lbl">Distinctive — Marquee offerings</div>
      <div class="val">{md["asu_to_utk"].get("unique", 0) + md["utk_to_asu"].get("unique", 0):,}<small> total</small></div>
      <div class="lead">Courses with no close counterpart — genuinely signature content at one institution. ASU: {md["asu_to_utk"].get("unique", 0)}; UTK: {md["utk_to_asu"].get("unique", 0)}.</div>
      <div class="sub">ASU: Air Traffic Control (ATC) and specialized aviation. UTK: Nuclear Engineering, Music Performance ensembles, Veterinary Medicine and Pathology.</div>
    </div>
  </div>

  <h3 style="margin-top:28px">Distribution across each catalog</h3>
  <div class="overlap-grid">
    <div class="olabel">ASU → UTK</div>
    {pct_bar(md["asu_to_utk"].get("strong", 0), md["asu_to_utk"].get("moderate", 0), md["asu_to_utk"].get("unique", 0), asu_total, md["asu_to_utk"].get("generic_shell", 0))}
    <div class="olabel">UTK → ASU</div>
    {pct_bar(md["utk_to_asu"].get("strong", 0), md["utk_to_asu"].get("moderate", 0), md["utk_to_asu"].get("unique", 0), utk_total, md["utk_to_asu"].get("generic_shell", 0))}
  </div>
  <div class="legend">
    <span><span class="swatch" style="background:#1a5d3a"></span>Strong (&ge; 0.70)</span>
    <span><span class="swatch" style="background:#6aa889"></span>Moderate (0.50–0.70)</span>
    <span><span class="swatch" style="background:#c44536"></span>Distinctive (&lt; 0.50)</span>
    <span><span class="swatch" style="background:#9ca3af"></span>Admin shell (Thesis/Seminar/…)</span>
  </div>

  <div class="caveat" style="margin-top:20px">
    <strong>Method change from v1.</strong> An earlier version of this report used TF-IDF similarity and reported 62% of each catalog as "unique." That was an artifact of lexical matching: courses covering the same content in different words read as different. The semantic model closes that gap — most of what looked unique is actually <em>moderate</em> (joint-development territory). The mutual-strong count grew from 316 to 1,619.
  </div>
</section>

<section>
  <h2><span class="num">02</span>The reciprocal-credit backbone</h2>
  <p>{mutual_count:,} courses are mutual-strong 1:1 pairs — both sides' descriptions name the same content and each picks the other as its closest match. Published as a registrar crosswalk, these remove transfer-evaluation friction immediately.</p>
  <details class="big-table">
    <summary>
      <span class="big-table-label">Show top 40 mutual-strong pairs</span>
      <span class="chevron">▾</span>
    </summary>
    <div class="big-table-body">
      <table>
        <thead><tr><th>Sim.</th><th>ASU</th><th>UTK</th><th>Level</th></tr></thead>
        <tbody>{mutual_rows}</tbody>
      </table>
    </div>
  </details>

  <button class="view-all-btn" onclick="document.getElementById('all-pairs-dialog').showModal()">
    <span>View all {mutual_count:,} pairs</span>
    <span class="arrow">→</span>
  </button>

  <dialog class="all-pairs" id="all-pairs-dialog">
    <div class="dlg-head">
      <div>
        <h3 class="dlg-title">All {mutual_count:,} mutual-strong pairs</h3>
        <div class="dlg-sub">Both schools select each other at &ge; 0.70 cosine similarity. Sorted by similarity.</div>
      </div>
      <button class="dlg-close" onclick="this.closest('dialog').close()" aria-label="Close">×</button>
    </div>
    <div class="filter-bar">
      <input id="all-pairs-filter" type="search" placeholder="Filter by course code, title, or subject…" autocomplete="off" />
      <span class="count"><span id="all-pairs-shown">{mutual_count:,}</span> of {mutual_count:,}</span>
    </div>
    <div class="dlg-body">
      <table id="all-pairs-table">
        <thead><tr><th>Sim.</th><th>ASU</th><th>UTK</th><th>Level</th></tr></thead>
        <tbody>{all_mutual_rows}</tbody>
      </table>
    </div>
  </dialog>
</section>

<script>
(function() {{
  const input = document.getElementById('all-pairs-filter');
  const tbody = document.querySelector('#all-pairs-table tbody');
  const counter = document.getElementById('all-pairs-shown');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  // Pre-cache lowercase searchable text per row for fast filtering
  rows.forEach(r => r.dataset.search = r.textContent.toLowerCase());
  const totalLabel = "{mutual_count:,}".trim();
  let raf;
  input.addEventListener('input', () => {{
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {{
      const q = input.value.trim().toLowerCase();
      let shown = 0;
      for (const r of rows) {{
        const visible = !q || r.dataset.search.includes(q);
        r.style.display = visible ? '' : 'none';
        if (visible) shown++;
      }}
      counter.textContent = shown.toLocaleString();
    }});
  }});
}})();
</script>

<section>
  <h2><span class="num">03</span>Where each school has distinctive depth</h2>
  <p>Subjects with the most distinctive content — highest share of courses with only moderate or no counterpart at the other institution (minimum 10 non-shell courses). Open any row to see the actual courses in each bucket.</p>

  <div class="leader-grid">
    <div class="leader-col asu">
      <h3>ASU distinctive subjects</h3>
      {"".join(subject_card(s, "asu") for s in distinctive["asu"])}
    </div>
    <div class="leader-col utk">
      <h3>UTK distinctive subjects</h3>
      {"".join(subject_card(s, "utk") for s in distinctive["utk"])}
    </div>
  </div>
</section>

<section>
  <h2><span class="num">04</span>Where the catalogs meet densely</h2>
  <p>The other side of the same coin — subjects with the highest share of strong reciprocal matches (minimum 10 non-shell courses). These are the easiest wins for a reciprocal-credit compact.</p>

  <div class="leader-grid">
    <div class="leader-col asu">
      <h3>ASU reciprocal-credit density</h3>
      {"".join(subject_card(s, "asu-ov") for s in overlap["asu"])}
    </div>
    <div class="leader-col utk">
      <h3>UTK reciprocal-credit density</h3>
      {"".join(subject_card(s, "utk-ov") for s in overlap["utk"])}
    </div>
  </div>
</section>

<section>
  <h2><span class="num">05</span>By college &amp; subject — full ASU catalog drill-down</h2>
  <p>The complete ASU catalog organised by college and subject. Each row shows the match-strength mix against UTK and unfolds to sample courses from each bucket — strong/moderate matches show their UTK counterpart inline.</p>

  {"".join(
      f'''<details class="college-block"{' open' if i == 0 else ''}>
        <summary>
          <div class="college-head">
            <div>
              <div class="college-name">{esc(col["college"])}</div>
              <div class="college-stats">{col["total"]:,} courses across {col["subject_count"]} subject{'s' if col["subject_count"] != 1 else ''}  ·  {col["strong_pct"]}% strong  ·  {col["moderate_pct"]}% moderate  ·  {col["unique_pct"]}% distinctive (vs UTK)</div>
            </div>
            <div class="college-bar">{pct_bar(col["strong"], col["moderate"], col["unique"], col["total"])}</div>
            <span class="chevron">▾</span>
          </div>
        </summary>
        <div class="subject-list">
          {"".join(subject_card(s, f"asu-col-{i}") for s in col["subjects"][:20])}
        </div>
      </details>'''
      for i, col in enumerate(asu_colleges[:9])
  )}
</section>

<section>
  <h2><span class="num">06</span>Companion view — by UTK subject</h2>
  <p>The same drill-down applied from UTK's side. Every UTK subject with at least 8 non-shell courses, sorted by total course count. UTK's catalog doesn't expose a college taxonomy the way ASU's does, so subjects are listed flat.</p>

  <details class="college-block" open>
    <summary>
      <div class="college-head">
        <div>
          <div class="college-name">All UTK subjects</div>
          <div class="college-stats">{sum(1 for s in utk_subjects_all if s['total'] >= 8)} subjects shown, sorted by course count</div>
        </div>
        <div class="college-bar"></div>
        <span class="chevron">▾</span>
      </div>
    </summary>
    <div class="subject-list">
      {"".join(subject_card(s, f"utk-cat-{i}") for i, s in enumerate(sorted([s for s in utk_subjects_all if s['total'] >= 8], key=lambda x: -x['total'])))}
    </div>
  </details>
</section>

<section>
  <h2><span class="num">07</span>Opportunities for joint development</h2>
  <p>Six opportunities the data supports, ordered from fastest to most ambitious. Revised from the v1 report to de-emphasize the modality asymmetry (a known reason for this partnership, not a surprising finding) and lean on evidence from the three-layer analysis.</p>

  <div class="recs">
    <div class="rec">
      <div class="rid">Opportunity 01 · Foundational</div>
      <h4>Reciprocal-credit compact on {mutual_count:,} paired courses</h4>
      <p>The mutual-strong pairs already cover Law foundations (Federal Courts, Criminal Law, Secured Transactions), core Mathematics (Abstract Algebra, Combinatorics), Engineering foundations (Heat Transfer, Operating Systems, CFD), Linguistics &amp; language acquisition, Music performance fundamentals, Theatre production, and shared Humanities. A published crosswalk — registrar-led, semester-scoped — removes transfer-evaluation friction immediately.</p>
      <div class="evidence">Evidence: 1,619 mutual-strong pairs at &ge; 0.70 cosine, both directions. Full list published alongside this report.</div>
      <span class="tag">Fast</span><span class="tag">Registrar-led</span><span class="tag">Low risk</span>
    </div>

    <div class="rec">
      <div class="rid">Opportunity 02 · High-value</div>
      <h4>Reciprocal-dense humanities + language stackable minor</h4>
      <p>ASU subjects with &gt;65% strong overlap (HEB, LAP, AES, CAP, GRK, POR, JST) point at comparable UTK subjects (HEBR, LAR, AFAS, COUN, CLAS, PORT, REST). A co-designed humanities/language minor could let students build credits at either campus. Low-risk extension of Opportunity 01.</p>
      <div class="evidence">Evidence: 10 ASU subjects with &gt;65% strong-overlap density, all mapping to a single dominant UTK subject.</div>
      <span class="tag">Joint credential</span><span class="tag">Medium term</span>
    </div>

    <div class="rec">
      <div class="rid">Opportunity 03 · Differentiated</div>
      <h4>UTK-led applied-music certificate</h4>
      <p>UTK's MUPF (Music Performance, 243 courses, 49% distinctive, 47% moderate) and MUEN (Ensembles, 63 courses) are the most distinctive UTK offering at meaningful scale. ASU's MUP, MUE, and MUS programs are the natural partner. A UTK-curated stackable certificate in applied music performance — ensembles, instrumental studios, conducting — gives ASU learners access to a top-tier performance catalog without duplicating UTK's conservatory-grade faculty.</p>
      <div class="evidence">Evidence: UTK MUPF has 49.4% of its 243 courses with no near ASU counterpart; MUEN 60% moderate. Combined ~300-course catalog around performance pedagogy.</div>
      <span class="tag">Content IP</span><span class="tag">Joint branding</span>
    </div>

    <div class="rec">
      <div class="rid">Opportunity 04 · Differentiated</div>
      <h4>Land-grant × sustainability bridge</h4>
      <p>UTK's distinctive land-grant block — FORS (Forestry), WFS (Wildlife &amp; Fisheries), PLSC (Plant Sciences), ANSC (Animal Sciences), FDSC (Food Science), VMP (Veterinary Medicine Pathology) — has mostly moderate counterparts at ASU's ABS (Applied Biological Sciences) and SOS (Sustainability). Co-designed graduate certificates in agro-ecology, food systems, or wildlife management let each school fill the other's gap in a growing employer space.</p>
      <div class="evidence">Evidence: ASU ABS is the dominant partner for UTK FORS, PLSC, VMP, ANSC, VMC — but each pair is moderate, not strong. Content adjacency without duplication.</div>
      <span class="tag">Graduate</span><span class="tag">Sustainability</span>
    </div>

    <div class="rec">
      <div class="rid">Opportunity 05 · Specialty</div>
      <h4>Nuclear engineering &amp; aviation as a program swap</h4>
      <p>Two small, highly specialized catalogs have no equivalent at the partner school: UTK Nuclear Engineering (NE, 110 courses, 31% distinctive) and ASU Air Traffic Control (ATC, 10 courses, 70% distinctive). Formal articulation — students admitted at the home school, completing the specialty sequence at the partner — opens access to two strategic, low-supply workforces without either institution building the other's program.</p>
      <div class="evidence">Evidence: UTK NE 31% distinctive with weak partner mapping to ASU EEE; ASU ATC 70% distinctive with no meaningful UTK counterpart.</div>
      <span class="tag">Low volume</span><span class="tag">High specificity</span>
    </div>

    <div class="rec">
      <div class="rid">Opportunity 06 · Pedagogical</div>
      <h4>Applied-engaged micro-credential spanning both gen-ed systems</h4>
      <p>UTK's VolCore leads with Engaged Inquiries (EI, 232 courses) and Applied Oral Communication (AOC, 96 courses) — pedagogical frames with no direct ASU General Studies analog. A jointly-designed capstone that satisfies UTK EI and ASU upper-division Literacy &amp; Critical Inquiry (L) would carry both institutional stamps on one credential. A credential-design bet more than a curriculum bet.</p>
      <div class="evidence">Evidence: UTK VolCore tags 232 EI + 96 AOC courses; ASU L covers 440 courses. Overlap in philosophy, divergence in tagging.</div>
      <span class="tag">Pedagogical IP</span><span class="tag">Ambitious</span>
    </div>
  </div>

  <details class="more-opps">
    <summary>
      <span>+ Six more opportunities the data supports</span>
      <span class="chevron">▾</span>
    </summary>
    <div class="more-opps-body">
      <div class="recs">

        <div class="rec">
          <div class="rid">Opportunity 07 · Clinical</div>
          <h4>Joint counseling clinical pathway</h4>
          <p>ASU's Counseling Psychology (CAP, 27 courses, 74% strong) and Counselor Education (CED, 18 courses, 67% strong) both map dominantly into UTK's Counseling (COUN). A coordinated clinical training pathway — practicum portability, supervised hours reciprocity, joint licensure prep — is unusually well-supported by the descriptions on each side. Workforce tailwind: counselor shortage in both states.</p>
          <div class="evidence">Evidence: CAP 74% strong → COUN (11 links); CED 67% strong → COUN (9 links). Two distinct ASU subjects converging on a single UTK partner.</div>
          <span class="tag">Workforce</span><span class="tag">Licensure</span>
        </div>

        <div class="rec">
          <div class="rid">Opportunity 08 · R1 collaboration</div>
          <h4>Microbiology research-stream alignment</h4>
          <p>ASU MIC (26 courses, 65% strong) and UTK MICR (28 courses) describe near-identical undergraduate sequences. Joint research electives, shared summer immersion at one campus, and reciprocal lab rotations would multiply each school's R1 visibility without adding curriculum. Could anchor a longer-term joint MS.</p>
          <div class="evidence">Evidence: MIC 65% strong → MICR (10 links). Both schools list parallel core courses; difference is research emphasis, not content.</div>
          <span class="tag">Research IP</span><span class="tag">R1 visibility</span>
        </div>

        <div class="rec">
          <div class="rid">Opportunity 09 · Niche workforce</div>
          <h4>Recreation therapy &amp; sport management certificate</h4>
          <p>ASU Recreation Therapy (RTH, 15 courses, 73% strong) maps cleanly into UTK Recreation &amp; Sport Management (RSM, 11 links). Both pipelines feed adjacent niche workforces (clinical recreation, parks &amp; rec, sport admin). A jointly-branded certificate stacked onto either school's degree is a low-risk first co-credential.</p>
          <div class="evidence">Evidence: RTH 73% strong → RSM. Two of the highest cross-school alignments in the entire catalog.</div>
          <span class="tag">Stackable</span><span class="tag">Niche</span>
        </div>

        <div class="rec">
          <div class="rid">Opportunity 10 · Performing arts</div>
          <h4>Theatre + Dance cross-residency</h4>
          <p>ASU Dance (DCE, 132 courses, 80% moderate) sits adjacent to UTK Theatre (THEA) — same physical practice, different institutional emphasis (ASU's contemporary/concert focus, UTK's stage/production). Pair with UTK MUPF's depth (slide above) and a multi-disciplinary summer residency at either campus is a high-visibility, low-volume win.</p>
          <div class="evidence">Evidence: DCE partner = UTK THEA; 132 ASU courses with 80% moderate cross-school adjacency.</div>
          <span class="tag">Residency</span><span class="tag">Marquee</span>
        </div>

        <div class="rec">
          <div class="rid">Opportunity 11 · STEM gateway</div>
          <h4>Online STEM gateway equivalence pact</h4>
          <p>The strong-match pairs include foundational Operating Systems, Abstract Algebra, Heat Transfer, Computational Fluid Dynamics, and Neuroanatomy. A bilateral equivalence pact on these gateway courses would let UTK students take ASU online versions in the summer (or vice versa) with guaranteed credit acceptance — accelerating time-to-degree on common bottlenecks.</p>
          <div class="evidence">Evidence: 25+ STEM-foundation courses appear in the mutual-strong list at &gt; 0.85 cosine. Gateway courses are the highest-volume bottlenecks at both institutions.</div>
          <span class="tag">Time-to-degree</span><span class="tag">Online infra</span>
        </div>

        <div class="rec">
          <div class="rid">Opportunity 12 · Religious / classical studies</div>
          <h4>Hebrew–Greek–Religion language &amp; text consortium</h4>
          <p>Three of ASU's highest-overlap subjects sit in this cluster: Hebrew (HEB, 88% strong → UTK HEBR), Greek (GRK, 68% strong → UTK CLAS), and Jewish Studies (JST, 65% strong → UTK REST). A consortium model — shared advanced language courses (often single-instructor) and reciprocal text-tradition seminars — preserves rare offerings at both schools that are vulnerable to enrollment drops in isolation.</p>
          <div class="evidence">Evidence: HEB 88% / GRK 68% / JST 65% strong overlap. Languages with single-section courses are precisely the offerings most threatened by low local enrollment — and the most preservable through consortia.</div>
          <span class="tag">Preservation</span><span class="tag">Consortium</span>
        </div>

      </div>
    </div>
  </details>

  <div class="caveat" style="margin-top:24px">
    <strong>Note on modality.</strong> ASU has {c["asu_online"]:,} courses with online sections (~23% of catalog); UTK's catalog does not flag per-course modality (that metadata lives in the Banner timetable). This is a known asymmetry — one of the structural reasons for the partnership — and it enables every opportunity above. It is not, by itself, the opportunity.
  </div>
</section>

<section>
  <h2><span class="num">08</span>Method &amp; limitations</h2>
  <ul style="font-family:'Helvetica Neue',Arial,sans-serif; font-size:14px; color:var(--ink-2); max-width:820px; line-height:1.6;">
    <li><strong>Semantic model.</strong> sentence-transformers all-MiniLM-L6-v2 (384-dim). Trained on general-web sentence pairs; performs well on short technical text. A domain-tuned model (course-description-specific) would lift precision further.</li>
    <li><strong>Thresholds.</strong> Strong &ge; 0.70, Moderate 0.50–0.70, Distinctive &lt; 0.50. Calibrated against manual inspection of 30 pairs at each boundary. Change the thresholds and the bucket sizes change; the ranking across subjects is stable.</li>
    <li><strong>Mutual-strong</strong> requires <em>both</em> sides to select each other at the strong threshold. This is the highest-confidence bucket and the right foundation for a registrar crosswalk.</li>
    <li><strong>Admin shells</strong> (Thesis, Dissertation, Special Topics, Seminar, Internship, Capstone, Practicum) are flagged heuristically and reported in a separate bucket so they don't inflate either overlap or distinctiveness.</li>
    <li><strong>Catalog year mismatch.</strong> ASU and UTK-grad use 2025–26; UTK-undergrad uses 2026–27. Year-over-year churn is typically 3–5% of lines.</li>
    <li><strong>Modality.</strong> ASU's online flag is drawn from Spring/Summer 2026 term sections. UTK per-course modality is not published in the catalog (lives in Banner timetable).</li>
  </ul>
</section>

<footer>
  Built from a complete scrape of both live catalogs — {combined:,} course records across 560 subject codes — on 24 April 2026.
  Source data and analysis scripts in <code>catalog-compare/</code>. Analysis: <code>data/analysis_v2/</code>.
</footer>

</div>
</body>
</html>"""


OUT_HTML.write_text(html_doc, encoding="utf-8")
print(f"Wrote {OUT_HTML} ({len(html_doc):,} bytes)")
