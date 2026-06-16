const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

let pres = new pptxgen();
pres.defineLayout({ name: "ASU_WIDE", width: 20, height: 11.25 });
pres.layout = "ASU_WIDE";
pres.author = "EdPlus at ASU";
pres.title = "ASU × UTK Catalog Comparison v2";

const COLORS = {
  GOLD: "FFC627", MAROON: "8C1D40", NEAR_BLACK: "191919", BLACK: "000000",
  GOLD_LIGHTEST: "FFFAEE", GOLD_LIGHT: "FFD04F", GOLD_DARK: "AD7F00",
  WHITE: "FFFFFF", GRAY_LIGHTEST: "F7F7F7", GRAY_LIGHTER: "F3F3F3",
  GRAY_LIGHT: "ECEDEE", GRAY_MID: "CFCFCF", GRAY_DARK: "7D7D7D",
  TEXT_DARK: "333333", TEXT_SECONDARY: "666666", TEXT_MUTED: "888888",
  CORAL: "E8474C", ORANGE: "F5A623", TEAL: "00B4D8", GREEN: "2ECC71",
  BLUE_DARK: "2C3E7A", PURPLE: "7B61FF", OLIVE: "8B9A46",
  UTK_ORANGE: "FF8200", MINT: "D4EDE6",
  MATCH_STRONG: "1A5D3A", MATCH_MOD: "6AA889", MATCH_UNIQUE: "C44536",
};
const FONT = {
  PRIMARY: "Arial", HERO: 150, TITLE_XL: 110, TITLE_LG: 80, TITLE_MD: 60,
  TITLE_SM: 48, SUBTITLE: 36, HEADING: 30, BODY_LG: 24, BODY: 20,
  BODY_SM: 16, CAPTION: 14, TINY: 11, STAT: 100, STAT_SM: 72,
};
const LAYOUT = {
  WIDTH: 20, HEIGHT: 11.25, MARGIN: 0.9, MARGIN_WIDE: 1.8, GUTTER: 0.5,
  HEADER_Y: 0.6, TITLE_Y: 1.8, GOLD_LINE_Y: 1.0,
};

// ── helpers ──
function addGoldHighlight(s, x, y, w, h) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: COLORS.GOLD } });
}
function addGoldLine(s, y = LAYOUT.GOLD_LINE_Y, x = LAYOUT.MARGIN, w = LAYOUT.WIDTH - 2 * LAYOUT.MARGIN) {
  s.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color: COLORS.GOLD, width: 2 } });
}
function addGoldAccentBlock(s, x, y, w = 0.6, h = 0.25) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: COLORS.GOLD } });
}
function addGoldDots(s, x, y, count = 5, dotSize = 0.12, gap = 0.25) {
  for (let i = 0; i < count; i++) {
    s.addShape(pres.shapes.OVAL, {
      x: x + i * (dotSize + gap), y, w: dotSize, h: dotSize, fill: { color: COLORS.GOLD },
    });
  }
}
function addHeaderText(s, text, opts = {}) {
  if (!text) return;
  s.addText(text, {
    x: LAYOUT.MARGIN, y: LAYOUT.HEADER_Y, w: 14, h: 0.3,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY,
    color: opts.color || COLORS.TEXT_SECONDARY,
  });
}
function addCategoryLabel(s, x, y, text, opts = {}) {
  s.addText("\u2726", {
    x: x - 0.3, y, w: 0.3, h: 0.3,
    fontSize: 14, fontFace: FONT.PRIMARY, color: opts.color || COLORS.GOLD,
  });
  s.addText(text.toUpperCase(), {
    x, y, w: 10, h: 0.3,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY,
    bold: true, italic: true, color: opts.color || COLORS.GOLD_DARK,
  });
}
function addPill(s, x, y, w, h, text, bgColor, textColor = "FFFFFF") {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, fill: { color: bgColor }, rectRadius: h / 2,
  });
  s.addText(text, {
    x, y, w, h, fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true,
    color: textColor, align: "center", valign: "middle",
  });
}
function addMaroonBarPattern(s, y, height) {
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y, w: LAYOUT.WIDTH, h: height, fill: { color: COLORS.MAROON } });
  for (let i = 0; i < 80; i++) {
    const barH = height * (0.3 + Math.random() * 0.7);
    s.addShape(pres.shapes.RECTANGLE, {
      x: i * 0.25, y: y + (height - barH), w: 0.08, h: barH,
      fill: { color: "A0375C", transparency: 30 + Math.random() * 30 },
    });
  }
}
function addEdPlusLogo(s, x, y, opts = {}) {
  const scale = opts.scale || 1, color = opts.color || COLORS.BLACK;
  s.addText([
    { text: "ASU", options: { fontSize: 14 * scale, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MAROON } },
    { text: "  ·  EdPlus", options: { fontSize: 14 * scale, fontFace: FONT.PRIMARY, bold: true, color } },
  ], { x, y, w: 3 * scale, h: 0.4 * scale, margin: 0 });
  s.addText("Arizona State University", {
    x, y: y + 0.28 * scale, w: 3 * scale, h: 0.2 * scale,
    fontSize: 8 * scale, fontFace: FONT.PRIMARY,
    color: opts.subtitleColor || COLORS.TEXT_SECONDARY,
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 1 — Title: Gold hero
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.GOLD };
  s.addText("Two Catalogs.\nMore in Common\nThan You'd Think.", {
    x: LAYOUT.MARGIN, y: 0.9, w: 18, h: 7,
    fontSize: 110, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK,
    valign: "top", lineSpacingMultiple: 0.92, margin: 0,
  });
  s.addText([
    { text: "A ", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, color: COLORS.BLACK } },
    { text: "semantic", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, bold: true, italic: true, color: COLORS.BLACK } },
    { text: " comparison of ", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, color: COLORS.BLACK } },
    { text: "23,948 courses", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK } },
    { text: " across ", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, color: COLORS.BLACK } },
    { text: "Arizona State", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MAROON } },
    { text: " and the ", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, color: COLORS.BLACK } },
    { text: "University of Tennessee, Knoxville.", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, bold: true, color: COLORS.NEAR_BLACK } },
  ], { x: LAYOUT.MARGIN, y: 8.4, w: 17, h: 1.2, margin: 0 });
  s.addText("Prepared for ASU Online Leadership  ·  v2, April 2026  ·  Method: sentence-transformer embeddings", {
    x: LAYOUT.MARGIN, y: 9.6, w: 16, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, color: COLORS.TEXT_DARK, italic: true,
  });
  addEdPlusLogo(s, LAYOUT.MARGIN, 10.3, { scale: 1.3 });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 2 — The reframe (v1 → v2)
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };
  addHeaderText(s, "THE REFRAME  \u00B7  LEXICAL \u2192 SEMANTIC");
  addGoldHighlight(s, LAYOUT.MARGIN_WIDE, 1.2, 9, 0.9);
  s.addText("We were reading the catalogs wrong.", {
    x: LAYOUT.MARGIN_WIDE, y: 1.1, w: 16, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
  });
  addGoldDots(s, LAYOUT.MARGIN_WIDE, 2.8);

  s.addText("An initial lexical comparison (TF-IDF) suggested most of each catalog was unique to its school. Replacing it with a sentence-transformer model (semantic similarity on descriptions) shows the opposite: the catalogs overlap substantially, and the interesting story is in the middle layer — courses that teach similar things, differently.", {
    x: LAYOUT.MARGIN_WIDE, y: 3.3, w: 16, h: 2.5,
    fontSize: FONT.BODY, fontFace: FONT.PRIMARY, color: COLORS.TEXT_DARK,
  });

  // Before/after comparison blocks
  const blockY = 6, blockH = 4;
  const blockW = 7.8, gap = 0.4;
  const startX = (LAYOUT.WIDTH - (2 * blockW + gap)) / 2;

  // v1
  s.addShape(pres.shapes.RECTANGLE, {
    x: startX, y: blockY, w: blockW, h: blockH,
    fill: { color: COLORS.GRAY_LIGHTEST }, line: { color: COLORS.GRAY_MID, width: 1 },
  });
  s.addText("v1 · Lexical (TF-IDF)", {
    x: startX + 0.3, y: blockY + 0.3, w: blockW - 0.6, h: 0.4,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.TEXT_MUTED, margin: 0,
  });
  [
    { k: "Mutual-strong 1:1 pairs", v: "316" },
    { k: "Courses with strong match", v: "~840" },
    { k: "Catalog flagged as unique", v: "62%" },
    { k: "Narrative", v: "\u201Cmostly distinct\u201D" },
  ].forEach((r, i) => {
    const y = blockY + 0.9 + i * 0.7;
    s.addText(r.k, {
      x: startX + 0.3, y, w: blockW - 3, h: 0.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_DARK, valign: "middle", margin: 0,
    });
    s.addText(r.v, {
      x: startX + blockW - 3, y, w: 2.6, h: 0.5,
      fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, bold: true, color: COLORS.TEXT_MUTED,
      align: "right", valign: "middle", margin: 0,
    });
  });

  // v2
  const x2 = startX + blockW + gap;
  s.addShape(pres.shapes.RECTANGLE, {
    x: x2, y: blockY, w: blockW, h: blockH,
    fill: { color: COLORS.GOLD_LIGHTEST }, line: { color: COLORS.GOLD, width: 2 },
  });
  s.addText("v2 · Semantic (sentence-transformer)", {
    x: x2 + 0.3, y: blockY + 0.3, w: blockW - 0.6, h: 0.4,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MAROON, margin: 0,
  });
  [
    { k: "Mutual-strong 1:1 pairs", v: "1,619" },
    { k: "Courses with strong match", v: "~7,000" },
    { k: "Catalog truly distinctive", v: "~3%" },
    { k: "Narrative", v: "three layers: deep overlap + joint-dev + marquee" },
  ].forEach((r, i) => {
    const y = blockY + 0.9 + i * 0.7;
    s.addText(r.k, {
      x: x2 + 0.3, y, w: blockW - 3, h: 0.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.BLACK, valign: "middle", margin: 0,
    });
    s.addText(r.v, {
      x: x2 + blockW - 3, y, w: 2.6, h: 0.5,
      fontSize: r.v.length > 10 ? FONT.BODY_SM : FONT.BODY_LG, fontFace: FONT.PRIMARY, bold: true,
      color: COLORS.GOLD_DARK, align: "right", valign: "middle", margin: 0,
    });
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 3 — The three layers
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };
  addHeaderText(s, "THE THREE LAYERS OF OVERLAP");
  addGoldHighlight(s, LAYOUT.MARGIN, 1.2, 11, 0.9);
  s.addText("Three layers, three strategies.", {
    x: LAYOUT.MARGIN, y: 1, w: 18, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
  });

  const layers = [
    {
      lbl: "STRONG", label: "RECIPROCAL-CREDIT BACKBONE",
      stat: "1,619", statLbl: "mutual 1:1 pairs",
      body: "Both schools teach the same content and each picks the other as its closest match (\u2265 0.70 cosine, both directions). Ready for a published registrar crosswalk.",
      ex: "Federal Courts \u2194 Federal Courts (0.95)\nOperating Systems \u2194 Operating Systems (0.93)\nJazz Pedagogy \u2194 Jazz Pedagogy (0.93)\nNeuroanatomy \u2194 Neuroanatomy (0.95)",
      color: COLORS.MATCH_STRONG, bgColor: "E8F3EC",
    },
    {
      lbl: "MODERATE", label: "JOINT-DEVELOPMENT SPACE",
      stat: "~5,000", statLbl: "per school",
      body: "Courses with a thematically adjacent but not identical counterpart (0.50\u20130.70). Same field, different emphasis. The space where stackable certificates and co-designed curriculum create real value.",
      ex: "Distributed Systems \u2194 Operating Systems\nActuarial Models \u2194 Actuarial Science Problems\nApplied Herpetology \u2194 Herpetology\nMany language & culture studies",
      color: COLORS.MATCH_MOD, bgColor: "EEF3EC",
    },
    {
      lbl: "DISTINCTIVE", label: "MARQUEE OFFERINGS",
      stat: "~600", statLbl: "total across both",
      body: "Courses with no close counterpart at the partner institution. These are genuinely signature programs \u2014 small in count, high in strategic value.",
      ex: "ASU: Air Traffic Control (ATC), specialized aviation\nUTK: Nuclear Engineering (NE), Music Performance\n(MUPF ensembles), Veterinary Medicine &\nPathology, Forestry/Wildlife & Fisheries",
      color: COLORS.MATCH_UNIQUE, bgColor: "F9E7E3",
    },
  ];

  const cardW = 5.95, cardH = 7.4, gapX = 0.3;
  const startX = LAYOUT.MARGIN;
  const startY = 2.8;
  layers.forEach((l, i) => {
    const x = startX + i * (cardW + gapX);
    s.addShape(pres.shapes.RECTANGLE, { x, y: startY, w: cardW, h: 0.35, fill: { color: l.color } });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: startY + 0.35, w: cardW, h: cardH - 0.35,
      fill: { color: l.bgColor }, line: { color: l.color, width: 1 },
    });
    s.addText(l.lbl, {
      x: x + 0.35, y: startY + 0.55, w: cardW - 0.7, h: 0.35,
      fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true,
      color: l.color, margin: 0,
    });
    s.addText(l.label, {
      x: x + 0.35, y: startY + 0.9, w: cardW - 0.7, h: 0.6,
      fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true,
      color: COLORS.BLACK, margin: 0,
    });
    s.addText(l.stat, {
      x: x + 0.35, y: startY + 1.6, w: cardW - 0.7, h: 1.6,
      fontSize: FONT.STAT_SM, fontFace: FONT.PRIMARY, bold: true,
      color: l.color, margin: 0,
    });
    s.addText(l.statLbl, {
      x: x + 0.35, y: startY + 3.3, w: cardW - 0.7, h: 0.4,
      fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, italic: true,
      color: COLORS.TEXT_SECONDARY, margin: 0,
    });
    s.addText(l.body, {
      x: x + 0.35, y: startY + 3.9, w: cardW - 0.7, h: 1.8,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_DARK,
    });
    // Examples box
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.35, y: startY + 5.7, w: cardW - 0.7, h: 1.5,
      fill: { color: COLORS.WHITE }, line: { color: l.color, width: 0.5 },
    });
    s.addText(l.ex, {
      x: x + 0.5, y: startY + 5.8, w: cardW - 1, h: 1.3,
      fontSize: FONT.TINY, fontFace: FONT.PRIMARY, color: COLORS.TEXT_DARK,
      valign: "top",
    });
  });

  s.addText("Three different partnership strategies. The deck that follows walks each one.", {
    x: LAYOUT.MARGIN, y: 10.5, w: 18, h: 0.5,
    fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, italic: true,
    color: COLORS.TEXT_SECONDARY, align: "center",
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 4 — Reciprocal-credit backbone table
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };
  addHeaderText(s, "LAYER 01 \u00B7 RECIPROCAL CREDIT");
  addGoldHighlight(s, LAYOUT.MARGIN, 1.4, 6, 0.9);
  s.addText("1,619 clean 1:1 pairs.", {
    x: LAYOUT.MARGIN, y: 1.3, w: 18, h: 1.2,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
  });
  s.addText("Sample of highest-similarity mutual-strong pairs. Both sides describe the same content and each picks the other as its closest match. The low-friction foundation for automatic credit recognition.", {
    x: LAYOUT.MARGIN, y: 2.7, w: 18, h: 1.2,
    fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY,
  });

  const pairs = [
    { sim: "0.95", asu: "LAW 613",  asuT: "Federal Courts",                      utk: "LAW 916",  utkT: "Federal Courts" },
    { sim: "0.95", asu: "NEU 426",  asuT: "Neuroanatomy",                         utk: "NEUR 200", utkT: "Introductory Neuroanatomy" },
    { sim: "0.93", asu: "CSE 330",  asuT: "Operating Systems",                    utk: "COSC 361", utkT: "Operating Systems" },
    { sim: "0.93", asu: "MUE 560",  asuT: "Jazz Pedagogy",                        utk: "MUJZ 420", utkT: "Jazz Pedagogy" },
    { sim: "0.92", asu: "MAE 587",  asuT: "Radiation Heat Transfer",              utk: "ME 613",   utkT: "Advanced Radiation Heat Transfer" },
    { sim: "0.92", asu: "THP 517",  asuT: "Stage Management",                     utk: "THEA 330", utkT: "Stage Management" },
    { sim: "0.92", asu: "ABS 260",  asuT: "Fundamentals of Sustainable Horticulture", utk: "PLSC 210", utkT: "Horticulture: Principles and Practices" },
    { sim: "0.92", asu: "LAP 371",  asuT: "Landscape Architecture Professional Practice I", utk: "LAR 582", utkT: "Professional Practices" },
    { sim: "0.91", asu: "MAT 443",  asuT: "Introduction to Abstract Algebra",     utk: "MATH 351", utkT: "Introduction to Abstract Algebra" },
    { sim: "0.89", asu: "SLC 515",  asuT: "Second-Language Acquisition",          utk: "LING 476", utkT: "Second Language Acquisition" },
    { sim: "0.86", asu: "ARB 102",  asuT: "Elementary Arabic II",                 utk: "ARAB 122", utkT: "Elementary Arabic II" },
    { sim: "0.85", asu: "LAW 516",  asuT: "Criminal Law",                         utk: "LAW 809",  utkT: "Criminal Law" },
  ];

  const rowY = 4.1, rowH = 0.52;
  const cols = { sim: 1.2, asu: 7.9, utk: 7.9 };
  s.addShape(pres.shapes.RECTANGLE, {
    x: LAYOUT.MARGIN, y: rowY, w: LAYOUT.WIDTH - 2 * LAYOUT.MARGIN, h: 0.5,
    fill: { color: COLORS.NEAR_BLACK },
  });
  const hdrOpts = { fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.GOLD, valign: "middle", margin: 0 };
  s.addText("SIM.", { x: LAYOUT.MARGIN + 0.2, y: rowY, w: cols.sim, h: 0.5, ...hdrOpts });
  s.addText("ASU", { x: LAYOUT.MARGIN + cols.sim + 0.3, y: rowY, w: cols.asu, h: 0.5, ...hdrOpts });
  s.addText("UTK", { x: LAYOUT.MARGIN + cols.sim + cols.asu + 0.5, y: rowY, w: cols.utk, h: 0.5, ...hdrOpts });

  pairs.forEach((p, i) => {
    const y = rowY + 0.55 + i * rowH;
    if (i % 2 === 0) {
      s.addShape(pres.shapes.RECTANGLE, {
        x: LAYOUT.MARGIN, y, w: LAYOUT.WIDTH - 2 * LAYOUT.MARGIN, h: rowH,
        fill: { color: COLORS.GOLD_LIGHTEST }, line: { color: "ffffff", width: 0 },
      });
    }
    s.addText(p.sim, {
      x: LAYOUT.MARGIN + 0.2, y, w: cols.sim, h: rowH,
      fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true,
      color: COLORS.GOLD_DARK, valign: "middle", margin: 0,
    });
    s.addText([
      { text: p.asu + "   ", options: { bold: true, color: COLORS.MAROON, fontSize: FONT.BODY_SM } },
      { text: p.asuT, options: { color: COLORS.BLACK, fontSize: FONT.BODY_SM } },
    ], { x: LAYOUT.MARGIN + cols.sim + 0.3, y, w: cols.asu, h: rowH, fontFace: FONT.PRIMARY, valign: "middle", margin: 0 });
    s.addText([
      { text: p.utk + "   ", options: { bold: true, color: COLORS.UTK_ORANGE, fontSize: FONT.BODY_SM } },
      { text: p.utkT, options: { color: COLORS.BLACK, fontSize: FONT.BODY_SM } },
    ], { x: LAYOUT.MARGIN + cols.sim + cols.asu + 0.5, y, w: cols.utk, h: rowH, fontFace: FONT.PRIMARY, valign: "middle", margin: 0 });
  });

  s.addText("Full list of 1,619 pairs published alongside this deck.", {
    x: LAYOUT.MARGIN, y: 10.7, w: 18, h: 0.4,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, italic: true, color: COLORS.TEXT_MUTED, align: "center",
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 5 — Reciprocal density hotspots
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };
  addHeaderText(s, "LAYER 01 \u00B7 DENSITY HOTSPOTS");
  addGoldHighlight(s, LAYOUT.MARGIN, 1.4, 8, 0.9);
  s.addText("Where reciprocal credit is already dense.", {
    x: LAYOUT.MARGIN, y: 1.3, w: 18, h: 1.2,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
  });
  s.addText("ASU subjects with the highest share of strong cross-school pairs (min. 10 non-shell courses). Each maps to a single dominant UTK subject. These are the clearest places to start a published crosswalk — agreement is already implicit in course content.", {
    x: LAYOUT.MARGIN, y: 2.7, w: 18, h: 1.3,
    fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY,
  });

  // Sideways bar chart-like table
  const hotspots = [
    { asu: "HEB",  lbl: "Hebrew",                     pct: 88, utk: "HEBR", n: 17 },
    { asu: "LAP",  lbl: "Landscape Architecture",     pct: 82, utk: "LAR",  n: 22 },
    { asu: "AES",  lbl: "Asian Studies",              pct: 75, utk: "AFAS", n: 16 },
    { asu: "CAP",  lbl: "Counseling Psychology",      pct: 74, utk: "COUN", n: 27 },
    { asu: "RTH",  lbl: "Recreation Therapy",         pct: 73, utk: "RSM",  n: 15 },
    { asu: "POR",  lbl: "Portuguese",                 pct: 69, utk: "PORT", n: 13 },
    { asu: "GRK",  lbl: "Greek (Classical)",          pct: 68, utk: "CLAS", n: 19 },
    { asu: "CED",  lbl: "Counselor Education",        pct: 67, utk: "COUN", n: 18 },
    { asu: "MIC",  lbl: "Microbiology",               pct: 65, utk: "MICR", n: 26 },
    { asu: "JST",  lbl: "Jewish Studies",             pct: 65, utk: "REST", n: 31 },
  ];

  const chartY = 4.3, rowH = 0.55;
  hotspots.forEach((h, i) => {
    const y = chartY + i * rowH;
    s.addText(h.asu, {
      x: LAYOUT.MARGIN, y, w: 1.2, h: rowH,
      fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MAROON, valign: "middle", margin: 0,
    });
    s.addText(h.lbl, {
      x: LAYOUT.MARGIN + 1.3, y, w: 4.5, h: rowH,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.BLACK, valign: "middle", margin: 0,
    });
    // Bar
    const barX = LAYOUT.MARGIN + 6, maxBar = 8;
    const w = (h.pct / 100) * maxBar;
    s.addShape(pres.shapes.RECTANGLE, {
      x: barX, y: y + 0.12, w: maxBar, h: rowH - 0.24,
      fill: { color: COLORS.GRAY_LIGHTER }, line: { color: "ffffff", width: 0 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: barX, y: y + 0.12, w, h: rowH - 0.24,
      fill: { color: COLORS.MATCH_STRONG }, line: { color: "ffffff", width: 0 },
    });
    s.addText(`${h.pct}% strong`, {
      x: barX + w + 0.1, y, w: 1.6, h: rowH,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MATCH_STRONG, valign: "middle", margin: 0,
    });
    s.addText(`\u2192 UTK ${h.utk}`, {
      x: LAYOUT.MARGIN + 16.5, y, w: 2.4, h: rowH,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, bold: true, color: COLORS.UTK_ORANGE,
      align: "right", valign: "middle", margin: 0,
    });
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 6 — Section divider: distinctive depth
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.NEAR_BLACK };
  s.addText("Where each school\nhas distinctive depth.", {
    x: LAYOUT.MARGIN, y: 3, w: 18, h: 6.5,
    fontSize: 100, fontFace: FONT.PRIMARY, bold: true, color: COLORS.WHITE,
    lineSpacingMultiple: 0.95, margin: 0,
  });
  addGoldAccentBlock(s, LAYOUT.MARGIN, 9.3, 1, 0.3);
  s.addText("LAYERS 02 + 03  \u00B7  JOINT-DEV SPACE + MARQUEE OFFERINGS", {
    x: LAYOUT.MARGIN + 1.2, y: 9.25, w: 16, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.GOLD,
    valign: "middle", margin: 0,
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 7 — ASU distinctive subjects (updated)
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };
  addCategoryLabel(s, 1.2, 0.8, "ASU distinctive subjects", { color: COLORS.MAROON });
  addGoldHighlight(s, LAYOUT.MARGIN, 1.6, 10, 0.9);
  s.addText("ASU's signature depth — not taught at UTK.", {
    x: LAYOUT.MARGIN, y: 1.4, w: 18, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
  });
  s.addText("Subjects ranked by distinctiveness (unique + moderate share). Each has a meaningful course count and no strong counterpart at UTK.", {
    x: LAYOUT.MARGIN, y: 2.9, w: 18, h: 1,
    fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY,
  });

  const subs = [
    { code: "ATC", lbl: "Air Traffic Control",        n: 10,  uniq: 70, mod: 10, ex: "Tower Ops, TRACON, IFR Ground School" },
    { code: "DCE", lbl: "Dance",                      n: 132, uniq: 10, mod: 80, ex: "Partner: UTK THEA" },
    { code: "BMD", lbl: "Biomedical Diagnostics",     n: 19,  uniq: 26, mod: 63, ex: "Anatomic, Cytology, Pathology studies" },
    { code: "HCA", lbl: "Health Care Admin.",         n: 10,  uniq: 10, mod: 90, ex: "No direct UTK counterpart" },
    { code: "NAV", lbl: "Naval Science / ROTC",       n: 10,  uniq: 30, mod: 30, ex: "Leadership, naval ops" },
    { code: "IBC", lbl: "Integrated Behav. Health",   n: 43,  uniq:  7, mod: 84, ex: "Partner: UTK NURS (moderate)" },
    { code: "HSD", lbl: "Human Systems Dev.",         n: 20,  uniq: 10, mod: 80, ex: "Interdisciplinary futures / sustainability" },
    { code: "NAN", lbl: "Nanoscience",                n: 10,  uniq: 10, mod: 90, ex: "Partner: UTK MSE (moderate)" },
    { code: "AMT", lbl: "Aviation Management",        n: 76,  uniq:  5, mod: 65, ex: "Flight Instructor series, airline ops" },
    { code: "BMY", lbl: "Biomimicry",                 n: 21,  uniq: 10, mod: 76, ex: "A distinctly ASU interdisciplinary program" },
  ];

  const cols = 2;
  const cardW = 8.9, cardH = 3.5, gapX = 0.3, gapY = 0.25;
  const startX = LAYOUT.MARGIN, startY = 4;
  subs.forEach((sub, i) => {
    if (i >= 10) return;
    const r = Math.floor(i / cols), c = i % cols;
    const x = startX + c * (cardW + gapX);
    const y = startY + r * (cardH + gapY);
    if (r >= 2) return;  // keep to 4 cards
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.12, h: cardH, fill: { color: COLORS.MAROON } });
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.12, y, w: cardW - 0.12, h: cardH,
      fill: { color: COLORS.GRAY_LIGHTEST } });
    s.addText(sub.code, {
      x: x + 0.3, y: y + 0.25, w: 2.7, h: 1, valign: "top",
      fontSize: 52, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MAROON, margin: 0,
    });
    s.addText(sub.lbl, {
      x: x + 3.1, y: y + 0.35, w: cardW - 3.3, h: 0.6,
      fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
    });
    s.addText(`${sub.n} courses  \u00B7  ${sub.uniq}% distinctive  \u00B7  ${sub.mod}% moderate`, {
      x: x + 3.1, y: y + 1, w: cardW - 3.3, h: 0.4,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY, margin: 0,
    });
    s.addText(sub.ex, {
      x: x + 0.3, y: y + 2.1, w: cardW - 0.6, h: 1.2,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, italic: true, color: COLORS.TEXT_DARK,
    });
  });

  s.addText("Six more ASU distinctive subjects (ATC runner-ups in aviation, biomimicry, health administration) detailed in the HTML report drill-down.", {
    x: LAYOUT.MARGIN, y: 10.5, w: 18, h: 0.4,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, italic: true, color: COLORS.TEXT_MUTED, align: "center",
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 8 — UTK distinctive subjects (updated)
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };
  addCategoryLabel(s, 1.2, 0.8, "UTK distinctive subjects", { color: COLORS.UTK_ORANGE });
  addGoldHighlight(s, LAYOUT.MARGIN, 1.6, 10, 0.9);
  s.addText("UTK's signature depth — not taught at ASU.", {
    x: LAYOUT.MARGIN, y: 1.4, w: 18, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
  });
  s.addText("The concentration of distinctiveness at UTK is sharper: Music Performance, Nuclear Engineering, and the land-grant agricultural sciences dominate.", {
    x: LAYOUT.MARGIN, y: 2.9, w: 18, h: 1,
    fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY,
  });

  const subs = [
    { code: "MUPF", lbl: "Music Performance",        n: 243, uniq: 49, mod: 47, ex: "Ensembles, instrumental studios, conducting. Conservatory-grade." },
    { code: "NE",   lbl: "Nuclear Engineering",      n: 110, uniq: 31, mod: 58, ex: "Radiochemistry, nuclear thermal hydraulics. ASU has no equivalent." },
    { code: "PLSC", lbl: "Plant Sciences",           n: 100, uniq: 17, mod: 54, ex: "Land-grant depth: cultivation, horticulture, plant breeding" },
    { code: "ANSC", lbl: "Animal Sciences",          n:  56, uniq: 23, mod: 55, ex: "Large-animal husbandry, reproduction, nutrition" },
    { code: "VMP",  lbl: "Vet. Medicine Pathology",  n:  71, uniq: 16, mod: 79, ex: "Veterinary specialty; ASU ABS partial partner" },
    { code: "FORS", lbl: "Forestry",                 n:  38, uniq: 16, mod: 63, ex: "Silviculture, urban forestry, arboriculture" },
    { code: "FDSC", lbl: "Food Science",             n:  46, uniq: 17, mod: 65, ex: "Vines and Wines, food chemistry, regulation" },
    { code: "MUEN", lbl: "Music Ensembles",          n:  63, uniq: 14, mod: 60, ex: "Orchestra, band, choir, chamber" },
  ];

  const cols = 2;
  const cardW = 8.9, cardH = 2.8, gapX = 0.3, gapY = 0.2;
  const startX = LAYOUT.MARGIN, startY = 4;
  subs.forEach((sub, i) => {
    if (i >= 8) return;
    const r = Math.floor(i / cols), c = i % cols;
    const x = startX + c * (cardW + gapX);
    const y = startY + r * (cardH + gapY);
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.12, h: cardH, fill: { color: COLORS.UTK_ORANGE } });
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.12, y, w: cardW - 0.12, h: cardH,
      fill: { color: COLORS.GRAY_LIGHTEST } });
    s.addText(sub.code, {
      x: x + 0.3, y: y + 0.2, w: 2.7, h: 0.9, valign: "top",
      fontSize: 40, fontFace: FONT.PRIMARY, bold: true, color: COLORS.UTK_ORANGE, margin: 0,
    });
    s.addText(sub.lbl, {
      x: x + 3.1, y: y + 0.3, w: cardW - 3.3, h: 0.5,
      fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
    });
    s.addText(`${sub.n} courses  \u00B7  ${sub.uniq}% distinctive  \u00B7  ${sub.mod}% moderate`, {
      x: x + 3.1, y: y + 0.85, w: cardW - 3.3, h: 0.35,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY, margin: 0,
    });
    s.addText(sub.ex, {
      x: x + 0.3, y: y + 1.5, w: cardW - 0.6, h: 1.1,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, italic: true, color: COLORS.TEXT_DARK,
    });
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 9 — Designation philosophies
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };
  addCategoryLabel(s, 1.2, 0.8, "Gen-ed philosophies");
  addGoldHighlight(s, LAYOUT.MARGIN, 1.6, 11, 0.9);
  s.addText("Different bets on what gen-ed is for.", {
    x: LAYOUT.MARGIN, y: 1.4, w: 18, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
  });
  s.addText("ASU tags general-ed along traditional discipline axes. UTK's VolCore leads with pedagogy \u2014 Engaged Inquiries is tagged more widely than any discipline category. A real divergence that creates room for a co-designed credential.", {
    x: LAYOUT.MARGIN, y: 2.9, w: 18, h: 1.2,
    fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY,
  });

  const panelY = 4.5, panelH = 5.5;
  s.addShape(pres.shapes.RECTANGLE, {
    x: LAYOUT.MARGIN, y: panelY, w: 8.8, h: panelH,
    fill: { color: COLORS.GOLD_LIGHTEST }, line: { color: COLORS.GOLD, width: 2 },
  });
  s.addText("ASU GENERAL STUDIES (GOLD)", {
    x: LAYOUT.MARGIN + 0.3, y: panelY + 0.3, w: 8, h: 0.4,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MAROON, margin: 0,
  });
  s.addText("2,455 courses tagged", {
    x: LAYOUT.MARGIN + 0.3, y: panelY + 0.7, w: 8, h: 0.4,
    fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, italic: true, color: COLORS.TEXT_SECONDARY, margin: 0,
  });
  const asuD = [["G", "Global awareness", "575"], ["SB", "Social-Behavioral Sci.", "524"],
                ["HU", "Humanities", "507"], ["L", "Literacy & Critical Inquiry", "440"],
                ["H", "Historical Awareness", "322"], ["C", "Cultural Diversity", "294"]];
  asuD.forEach((d, i) => {
    const y = panelY + 1.3 + i * 0.6;
    s.addShape(pres.shapes.RECTANGLE, {
      x: LAYOUT.MARGIN + 0.3, y: y + 0.05, w: 0.9, h: 0.4, fill: { color: COLORS.MAROON },
    });
    s.addText(d[0], {
      x: LAYOUT.MARGIN + 0.3, y: y + 0.05, w: 0.9, h: 0.4,
      fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.WHITE,
      align: "center", valign: "middle", margin: 0,
    });
    s.addText(d[1], {
      x: LAYOUT.MARGIN + 1.4, y, w: 5.5, h: 0.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.BLACK, valign: "middle", margin: 0,
    });
    s.addText(d[2], {
      x: LAYOUT.MARGIN + 6.9, y, w: 1.6, h: 0.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, bold: true, color: COLORS.GOLD_DARK,
      align: "right", valign: "middle", margin: 0,
    });
  });

  s.addShape(pres.shapes.RECTANGLE, {
    x: LAYOUT.MARGIN + 9.3, y: panelY, w: 8.8, h: panelH,
    fill: { color: "FFF6EB" }, line: { color: COLORS.UTK_ORANGE, width: 2 },
  });
  s.addText("UTK VOLUNTEER CORE (VOLCORE)", {
    x: LAYOUT.MARGIN + 9.6, y: panelY + 0.3, w: 8, h: 0.4,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.UTK_ORANGE, margin: 0,
  });
  s.addText("1,113 courses tagged", {
    x: LAYOUT.MARGIN + 9.6, y: panelY + 0.7, w: 8, h: 0.4,
    fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, italic: true, color: COLORS.TEXT_SECONDARY, margin: 0,
  });
  const utkD = [["EI", "Engaged Inquiries", "232"], ["AH", "Arts & Humanities", "191"],
                ["GCI", "Global Citizenship \u2014 Intl.", "154"], ["AOC", "Applied Oral Communication", "96"],
                ["NS", "Natural Sciences", "84"], ["WC", "Written Communication", "80"]];
  utkD.forEach((d, i) => {
    const y = panelY + 1.3 + i * 0.6;
    const isApplied = ["EI", "AOC", "AAH"].includes(d[0]);
    s.addShape(pres.shapes.RECTANGLE, {
      x: LAYOUT.MARGIN + 9.6, y: y + 0.05, w: 0.9, h: 0.4,
      fill: { color: isApplied ? COLORS.UTK_ORANGE : COLORS.NEAR_BLACK },
    });
    s.addText(d[0], {
      x: LAYOUT.MARGIN + 9.6, y: y + 0.05, w: 0.9, h: 0.4,
      fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.WHITE,
      align: "center", valign: "middle", margin: 0,
    });
    s.addText(d[1], {
      x: LAYOUT.MARGIN + 10.7, y, w: 5.5, h: 0.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.BLACK,
      bold: isApplied, valign: "middle", margin: 0,
    });
    s.addText(d[2], {
      x: LAYOUT.MARGIN + 16.2, y, w: 1.6, h: 0.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, bold: true, color: COLORS.UTK_ORANGE,
      align: "right", valign: "middle", margin: 0,
    });
  });
  s.addText("UTK's top tag is pedagogical (Engaged Inquiries), not disciplinary.", {
    x: LAYOUT.MARGIN + 9.6, y: panelY + 4.8, w: 8, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, italic: true, bold: true, color: COLORS.UTK_ORANGE, margin: 0,
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 10 — Section: Joint development
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };
  addMaroonBarPattern(s, 0, LAYOUT.HEIGHT);
  s.addText("Six ways\nto work together.", {
    x: LAYOUT.MARGIN, y: 3, w: 18, h: 6,
    fontSize: FONT.TITLE_XL, fontFace: FONT.PRIMARY, bold: true, color: COLORS.WHITE, margin: 0,
  });
  addGoldAccentBlock(s, LAYOUT.MARGIN, 8.5, 1.2, 0.3);
  s.addText("FROM THREE LAYERS TO SIX OPPORTUNITIES", {
    x: LAYOUT.MARGIN + 1.5, y: 8.45, w: 12, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.GOLD, valign: "middle", margin: 0,
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 11 — 6 opportunities (revised)
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };
  addHeaderText(s, "OPPORTUNITIES EVIDENCE-BACKED");
  addGoldHighlight(s, LAYOUT.MARGIN, 1.2, 9, 0.9);
  s.addText("Six opportunities the data supports.", {
    x: LAYOUT.MARGIN, y: 1, w: 18, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
  });

  const opps = [
    { n: "01", t: "Reciprocal-credit compact",
      d: "Publish a crosswalk for the 1,619 mutual-strong pairs. Removes transfer-evaluation friction.",
      ev: "1,619 pairs \u2265 0.70 cosine, both directions",
      c: COLORS.GOLD, tag: "FAST" },
    { n: "02", t: "Humanities + language stackable minor",
      d: "Co-designed minor built from 10 ASU subjects with >65% strong overlap (HEB, LAP, AES, GRK, POR, JST).",
      ev: "HEB 88% \u00B7 LAP 82% \u00B7 AES 75% \u00B7 GRK 68%",
      c: COLORS.CORAL, tag: "JOINT CREDENTIAL" },
    { n: "03", t: "UTK-led applied-music certificate",
      d: "Stackable UTK certificate delivered at ASU online scale. MUPF (243) + MUEN (63) as backbone.",
      ev: "MUPF 49% distinctive, 47% moderate",
      c: COLORS.UTK_ORANGE, tag: "CONTENT IP" },
    { n: "04", t: "Land-grant \u00D7 sustainability bridge",
      d: "UTK FORS / PLSC / ANSC / VMP \u2194 ASU ABS / SOS. Moderate content adjacency without duplication.",
      ev: "6 UTK subjects, ~350 combined courses",
      c: COLORS.GREEN, tag: "GRADUATE" },
    { n: "05", t: "Nuclear & aviation program swap",
      d: "UTK NE (110 courses, 31% distinctive) and ASU ATC (10 courses, 70% distinctive) \u2014 articulation agreements.",
      ev: "Two highly-specialized, low-supply workforces",
      c: COLORS.PURPLE, tag: "SPECIALTY" },
    { n: "06", t: "Applied-engaged micro-credential",
      d: "Capstone tagged for UTK VolCore EI + ASU upper-div. L. Both institutional stamps on one credential.",
      ev: "UTK EI: 232 courses; ASU L: 440 courses",
      c: COLORS.TEAL, tag: "AMBITIOUS" },
  ];

  const cols = 3;
  const cardW = 5.95, cardH = 3.95, gapX = 0.25, gapY = 0.35;
  const startX = LAYOUT.MARGIN, startY = 2.8;
  opps.forEach((o, i) => {
    const r = Math.floor(i / cols), c = i % cols;
    const x = startX + c * (cardW + gapX);
    const y = startY + r * (cardH + gapY);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: cardW, h: cardH,
      fill: { color: COLORS.WHITE }, line: { color: COLORS.GRAY_MID, width: 1 },
    });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: cardW, h: 0.35, fill: { color: o.c } });
    s.addText(o.n, {
      x: x + 0.35, y: y + 0.6, w: 1.2, h: 1.1,
      fontSize: FONT.STAT_SM, fontFace: FONT.PRIMARY, bold: true, color: o.c, margin: 0,
    });
    s.addText(o.t, {
      x: x + 1.6, y: y + 0.7, w: cardW - 1.8, h: 1.2,
      fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
    });
    s.addText(o.d, {
      x: x + 0.35, y: y + 1.95, w: cardW - 0.7, h: 1.2,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_DARK,
    });
    // Evidence line
    s.addText("EVIDENCE", {
      x: x + 0.35, y: y + cardH - 1.15, w: cardW - 0.7, h: 0.3,
      fontSize: 9, fontFace: FONT.PRIMARY, bold: true, color: COLORS.TEXT_MUTED, margin: 0,
    });
    s.addText(o.ev, {
      x: x + 0.35, y: y + cardH - 0.85, w: cardW - 0.7, h: 0.5,
      fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, italic: true, color: COLORS.TEXT_SECONDARY, margin: 0,
    });
    // Tag
    addPill(s, x + 0.35, y + cardH - 0.5, Math.max(1.6, 0.3 + o.tag.length * 0.1), 0.35, o.tag, COLORS.NEAR_BLACK, COLORS.GOLD);
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 12 — Method + limitations + next steps
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };
  addHeaderText(s, "METHOD \u00B7 LIMITATIONS \u00B7 NEXT STEPS");
  addGoldHighlight(s, LAYOUT.MARGIN, 1.2, 8, 0.9);
  s.addText("Trust, but verify.", {
    x: LAYOUT.MARGIN, y: 1, w: 18, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
  });

  // Left: method + limitations
  s.addText("WHAT THE ANALYSIS IS", {
    x: LAYOUT.MARGIN, y: 3, w: 9, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MAROON, margin: 0,
  });
  const method = [
    { h: "Semantic embeddings", d: "sentence-transformers all-MiniLM-L6-v2, cosine similarity on title + description." },
    { h: "Mutual-strong filter", d: "Both sides must pick each other at \u2265 0.70 cosine. The highest-confidence bucket." },
    { h: "Shell bucket", d: "Thesis / Seminar / Internship / Special Topics filtered out of overlap counts heuristically." },
    { h: "Catalog year note", d: "ASU + UTK-grad on 2025\u201326; UTK-undergrad on 2026\u201327. 3\u20135% churn typical." },
  ];
  method.forEach((l, i) => {
    const y = 3.6 + i * 1.4;
    s.addShape(pres.shapes.RECTANGLE, { x: LAYOUT.MARGIN, y, w: 0.12, h: 1.1, fill: { color: COLORS.MAROON } });
    s.addText(l.h, {
      x: LAYOUT.MARGIN + 0.3, y, w: 8.5, h: 0.4,
      fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
    });
    s.addText(l.d, {
      x: LAYOUT.MARGIN + 0.3, y: y + 0.45, w: 8.5, h: 0.8,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY,
    });
  });

  // Right: next steps
  s.addText("WHAT TO DO NEXT", {
    x: LAYOUT.MARGIN + 9.5, y: 3, w: 9, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.GOLD_DARK, margin: 0,
  });
  const next = [
    { h: "Registrar review of 1,619 mutual pairs", d: "Fastest transfer of value from this analysis. Likely 90%+ accept-as-equivalent." },
    { h: "Share with UTK Provost / Online Ed.", d: "Confirm appetite for 1\u20132 opportunities. Opp. 01 + Opp. 03 are the natural first pair." },
    { h: "Model revenue for top-2 opportunities", d: "Build financial case. ASU online + UTK content IP arithmetic." },
    { h: "Domain-tune the embedding model", d: "Fine-tune on catalog-description pairs to lift precision on the moderate\u2194strong boundary." },
  ];
  next.forEach((l, i) => {
    const y = 3.6 + i * 1.4;
    s.addShape(pres.shapes.RECTANGLE, { x: LAYOUT.MARGIN + 9.5, y, w: 0.12, h: 1.1, fill: { color: COLORS.GOLD } });
    s.addText(l.h, {
      x: LAYOUT.MARGIN + 9.8, y, w: 8.5, h: 0.4,
      fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
    });
    s.addText(l.d, {
      x: LAYOUT.MARGIN + 9.8, y: y + 0.45, w: 8.5, h: 0.8,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY,
    });
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 13 — Closing
// ══════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: COLORS.GOLD };
  s.addText("Let's build what\nneither school can\nbuild alone.", {
    x: LAYOUT.MARGIN, y: 1.5, w: 18, h: 7,
    fontSize: 110, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK,
    lineSpacingMultiple: 0.95, valign: "top", margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: LAYOUT.MARGIN, y: 8.6, w: 1.2, h: 0.2, fill: { color: COLORS.NEAR_BLACK } });
  s.addText([
    { text: "Built from a complete scrape of both live catalogs \u2014 ", options: { fontSize: FONT.BODY_SM } },
    { text: "23,948 courses across 560 subject codes", options: { fontSize: FONT.BODY_SM, bold: true } },
    { text: " \u2014 on 24 April 2026. Semantic matching with sentence-transformers.", options: { fontSize: FONT.BODY_SM } },
  ], { x: LAYOUT.MARGIN, y: 8.9, w: 17, h: 0.5, fontFace: FONT.PRIMARY, color: COLORS.BLACK, margin: 0 });
  s.addText("Full drill-down available in the companion HTML report.", {
    x: LAYOUT.MARGIN, y: 9.4, w: 17, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, italic: true, color: COLORS.TEXT_DARK, margin: 0,
  });
  addEdPlusLogo(s, LAYOUT.MARGIN, 10.3, { scale: 1.2, color: COLORS.BLACK, subtitleColor: COLORS.TEXT_DARK });
}

const outPath = "/Users/apratlif/Documents/PM Skills/catalog-compare/reports/ASU_UTK_catalog_comparison.pptx";
pres.writeFile({ fileName: outPath })
  .then(() => console.log("Saved:", outPath))
  .catch((err) => { console.error(err); process.exit(1); });
