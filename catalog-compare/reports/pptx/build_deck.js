const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

let pres = new pptxgen();
pres.defineLayout({ name: "ASU_WIDE", width: 20, height: 11.25 });
pres.layout = "ASU_WIDE";
pres.author = "EdPlus at ASU";
pres.title = "ASU × UTK Catalog Comparison";

// ── Brand constants ──
const COLORS = {
  GOLD: "FFC627",
  MAROON: "8C1D40",
  NEAR_BLACK: "191919",
  BLACK: "000000",
  GOLD_LIGHTEST: "FFFAEE",
  GOLD_LIGHT: "FFD04F",
  GOLD_DARK: "AD7F00",
  WHITE: "FFFFFF",
  OFF_WHITE: "FAFAFA",
  GRAY_LIGHTEST: "F7F7F7",
  GRAY_LIGHTER: "F3F3F3",
  GRAY_LIGHT: "ECEDEE",
  GRAY_MID: "CFCFCF",
  GRAY_DARK: "7D7D7D",
  TEXT_DARK: "333333",
  TEXT_SECONDARY: "666666",
  TEXT_MUTED: "888888",
  CORAL: "E8474C",
  ORANGE: "F5A623",
  TEAL: "00B4D8",
  GREEN: "2ECC71",
  BLUE_DARK: "2C3E7A",
  PURPLE: "7B61FF",
  OLIVE: "8B9A46",
  UTK_ORANGE: "FF8200",
  MINT: "D4EDE6",
  CREAM: "FFF3C4",
};
const FONT = {
  PRIMARY: "Arial",
  HERO: 150, TITLE_XL: 110, TITLE_LG: 80, TITLE_MD: 60, TITLE_SM: 48,
  SUBTITLE: 36, HEADING: 30, BODY_LG: 24, BODY: 20, BODY_SM: 16,
  CAPTION: 14, TINY: 11, STAT: 100, STAT_SM: 72,
};
const LAYOUT = {
  WIDTH: 20, HEIGHT: 11.25, MARGIN: 0.9, MARGIN_WIDE: 1.8, GUTTER: 0.5,
  HEADER_Y: 0.6, TITLE_Y: 1.8, GOLD_LINE_Y: 1.0,
};

// ── Helpers ──
function addGoldHighlight(slide, x, y, w, h) {
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: COLORS.GOLD } });
}
function addGoldLine(slide, y = LAYOUT.GOLD_LINE_Y, x = LAYOUT.MARGIN, w = LAYOUT.WIDTH - 2 * LAYOUT.MARGIN) {
  slide.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color: COLORS.GOLD, width: 2 } });
}
function addGoldAccentBlock(slide, x, y, w = 0.6, h = 0.25) {
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: COLORS.GOLD } });
}
function addGoldDots(slide, x, y, count = 5, dotSize = 0.12, gap = 0.25) {
  for (let i = 0; i < count; i++) {
    slide.addShape(pres.shapes.OVAL, {
      x: x + i * (dotSize + gap), y, w: dotSize, h: dotSize, fill: { color: COLORS.GOLD },
    });
  }
}
function addHeaderText(slide, text, opts = {}) {
  if (!text) return;
  slide.addText(text, {
    x: LAYOUT.MARGIN, y: LAYOUT.HEADER_Y, w: 14, h: 0.3,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY,
    color: opts.color || COLORS.TEXT_SECONDARY, bold: false,
  });
}
function addNumberCircle(slide, x, y, size, number, opts = {}) {
  const bgColor = opts.bgColor || COLORS.GOLD;
  const textColor = opts.textColor || COLORS.BLACK;
  slide.addShape(pres.shapes.OVAL, { x, y, w: size, h: size, fill: { color: bgColor } });
  slide.addText(String(number), {
    x, y, w: size, h: size,
    fontSize: size * 20, fontFace: FONT.PRIMARY, bold: true,
    color: textColor, align: "center", valign: "middle", margin: 0,
  });
}
function addPill(slide, x, y, w, h, text, bgColor, textColor = "FFFFFF") {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, fill: { color: bgColor }, rectRadius: h / 2,
  });
  slide.addText(text, {
    x, y, w, h,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true,
    color: textColor, align: "center", valign: "middle",
  });
}
function addMaroonBarPattern(slide, y, height) {
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y, w: LAYOUT.WIDTH, h: height, fill: { color: COLORS.MAROON } });
  for (let i = 0; i < 80; i++) {
    const barH = height * (0.3 + Math.random() * 0.7);
    slide.addShape(pres.shapes.RECTANGLE, {
      x: i * 0.25, y: y + (height - barH), w: 0.08, h: barH,
      fill: { color: "A0375C", transparency: 30 + Math.random() * 30 },
    });
  }
}
function addCategoryLabel(slide, x, y, text, opts = {}) {
  slide.addText("\u2726", {
    x: x - 0.3, y, w: 0.3, h: 0.3,
    fontSize: 14, fontFace: FONT.PRIMARY, color: opts.color || COLORS.GOLD,
  });
  slide.addText(text.toUpperCase(), {
    x, y, w: 10, h: 0.3,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY,
    bold: true, italic: true, color: opts.color || COLORS.GOLD_DARK,
  });
}
function addGeometricBlocks(slide, x, y) {
  const blocks = [
    { dx: 0.5, dy: 0, w: 4, h: 1.2, color: COLORS.MAROON },
    { dx: 0, dy: 1.4, w: 4.5, h: 1.2, color: COLORS.GOLD },
    { dx: 1, dy: 2.8, w: 3.5, h: 1.2, color: COLORS.NEAR_BLACK },
    { dx: 0.3, dy: 4.2, w: 4.2, h: 1.2, color: COLORS.UTK_ORANGE },
    { dx: 0.8, dy: 5.6, w: 3.8, h: 1.2, color: COLORS.GOLD },
  ];
  blocks.forEach((b) => {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x + b.dx, y: y + b.dy, w: b.w, h: b.h,
      fill: { color: b.color }, rectRadius: 0.05, rotate: -5,
    });
  });
}

// ── LOGOS ──
function saveASULogos() {
  const logoB64 = "iVBORw0KGgoAAAANSUhEUgAAAhkAAABrCAYAAADab5BoAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAOdEVYdFNvZnR3YXJlAEZpZ21hnrGWYwAASktJREFUeAHtnQd8VFX2+M99b2bSA6ELmSR0FBEQEJA2SRBQFCuou2v7W1fXAkkA2xq7koLgz13dtbdVsKCoKC0TBAEVpSs9FSmBkDqZ8u79n/tCICTvTWaSmTAT7/fzmbyXua/ceeXec8859xwAgUAgEAgEAoFAIBAIBAKBQCAQCAQCgUAgEAgEAoFAIBAIBAKBQCAQCAQCgUAgEAgEAoFAIBAIBAKBQCAQCAQCgUAgEAgEAoFAIBAIBAKBQCAQCAQCgUAgEAgEAoFAIBAIBAKBQCAQCAQCg=";
  const pitchforkB64 = "iVBORw0KGgoAAAANSUhEUgAAAFwAAAAnCAYAAACCCi9aAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAOdEVYdFNvZnR3YXJlAEZpZ21hnrGWYwAABWVJREFUeAHtnX1SHDc=";
  const dir = path.dirname(require.main.filename);
  const logoPath = path.join(dir, "asu-logo.png");
  const pitchforkPath = path.join(dir, "asu-pitchfork.png");
  try {
    if (!fs.existsSync(logoPath)) fs.writeFileSync(logoPath, Buffer.from(logoB64, "base64"));
    if (!fs.existsSync(pitchforkPath)) fs.writeFileSync(pitchforkPath, Buffer.from(pitchforkB64, "base64"));
  } catch (e) { /* non-fatal if logo write fails */ }
  return { logoPath, pitchforkPath };
}
const { logoPath, pitchforkPath } = saveASULogos();

function addEdPlusLogo(slide, x, y, opts = {}) {
  const scale = opts.scale || 1;
  const color = opts.color || COLORS.BLACK;
  slide.addText([
    { text: "ASU", options: { fontSize: 14 * scale, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MAROON } },
    { text: "  ·  EdPlus", options: { fontSize: 14 * scale, fontFace: FONT.PRIMARY, bold: true, color } },
  ], { x, y, w: 3 * scale, h: 0.4 * scale, margin: 0 });
  slide.addText("Arizona State University", {
    x, y: y + 0.28 * scale, w: 3 * scale, h: 0.2 * scale,
    fontSize: 8 * scale, fontFace: FONT.PRIMARY,
    color: opts.subtitleColor || COLORS.TEXT_SECONDARY,
  });
}

// ====================================================================
// SLIDE 1 — Title: Gold Hero
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.GOLD };

  s.addText("Two Catalogs.\nOne Opportunity.", {
    x: LAYOUT.MARGIN, y: 1.2, w: 18, h: 6,
    fontSize: 130, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK,
    valign: "top", lineSpacingMultiple: 0.9, margin: 0,
  });

  s.addText([
    { text: "A data-driven comparison of ", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, color: COLORS.BLACK } },
    { text: "23,948 courses", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK } },
    { text: " across ", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, color: COLORS.BLACK } },
    { text: "Arizona State University", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MAROON } },
    { text: " and the ", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, color: COLORS.BLACK } },
    { text: "University of Tennessee, Knoxville.", options: { fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, bold: true, color: COLORS.NEAR_BLACK } },
  ], { x: LAYOUT.MARGIN, y: 8, w: 17, h: 1.2, margin: 0 });

  s.addText("Prepared for ASU Online Leadership  ·  April 2026", {
    x: LAYOUT.MARGIN, y: 9.4, w: 14, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY,
    color: COLORS.TEXT_DARK, italic: true,
  });

  addEdPlusLogo(s, LAYOUT.MARGIN, 10.2, { scale: 1.3 });
}

// ====================================================================
// SLIDE 2 — Stats: At-a-glance gold cards
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };

  addHeaderText(s, "AT A GLANCE");

  addGoldHighlight(s, LAYOUT.MARGIN_WIDE, 1.2, 6.5, 0.9);
  s.addText("What the catalogs show us", {
    x: LAYOUT.MARGIN_WIDE, y: 1.1, w: 14, h: 1.2,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.BLACK, margin: 0,
  });
  addGoldDots(s, LAYOUT.MARGIN_WIDE, 2.8);

  s.addText("Every course in both live catalogs was scraped, normalized, and matched. A complete view of scale, overlap, and distinctiveness from the ground truth — not from program directories.", {
    x: LAYOUT.MARGIN_WIDE, y: 3.3, w: 15, h: 1.8,
    fontSize: FONT.BODY, fontFace: FONT.PRIMARY, color: COLORS.TEXT_DARK,
  });

  const cards = [
    { v: "23,948", l: "Courses compared\n14,497 ASU  ·  9,451 UTK" },
    { v: "316", l: "Mutual-strong 1:1 pairs\n(both schools agree \u2265 0.55 cosine)" },
    { v: "62%", l: "of each catalog has\nno strong counterpart" },
    { v: "3,367", l: "ASU online offerings\n(UTK: no catalog-level flag)" },
  ];
  const cardW = 4.1, gap = 0.35;
  const totalW = cards.length * cardW + (cards.length - 1) * gap;
  const startX = (LAYOUT.WIDTH - totalW) / 2;
  cards.forEach((c, i) => {
    const x = startX + i * (cardW + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 5.6, w: cardW, h: 4.8,
      fill: { color: COLORS.GOLD_LIGHTEST }, rectRadius: 0.15,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 5.6, w: cardW, h: 0.2, fill: { color: COLORS.GOLD },
    });
    s.addText(c.v, {
      x, y: 6.0, w: cardW, h: 2.4,
      fontSize: c.v.length > 4 ? 78 : FONT.STAT, fontFace: FONT.PRIMARY, bold: true,
      color: COLORS.GOLD_DARK, align: "center", valign: "middle", margin: 0,
    });
    s.addText(c.l, {
      x: x + 0.25, y: 8.5, w: cardW - 0.5, h: 1.8,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY,
      color: COLORS.TEXT_DARK, align: "center",
    });
  });
}

// ====================================================================
// SLIDE 3 — Section: Scale & Overlap (3D blocks)
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };
  addGoldLine(s);

  s.addText("SECTION 01", {
    x: LAYOUT.MARGIN_WIDE, y: 2.5, w: 9, h: 0.5,
    fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true, italic: true,
    color: COLORS.GOLD_DARK, margin: 0,
  });
  s.addText("Scale &\nOverlap", {
    x: LAYOUT.MARGIN_WIDE, y: 3.2, w: 11, h: 5,
    fontSize: FONT.TITLE_XL, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.NEAR_BLACK, valign: "top", lineSpacingMultiple: 0.95, margin: 0,
  });
  s.addText("How much of each catalog meets the other — and how much doesn't.", {
    x: LAYOUT.MARGIN_WIDE, y: 7.8, w: 10, h: 1.5,
    fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, color: COLORS.BLACK,
  });

  addGeometricBlocks(s, 14, 2.2);
}

// ====================================================================
// SLIDE 4 — Content: Overlap breakdown
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };
  addHeaderText(s, "OVERLAP \u00B7 ASU \u2192 UTK / UTK \u2192 ASU");
  addGoldHighlight(s, LAYOUT.MARGIN_WIDE, 1.4, 7, 0.9);

  s.addText("Most content is distinctive.", {
    x: LAYOUT.MARGIN_WIDE, y: 1.2, w: 14, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.BLACK, margin: 0,
  });
  s.addText("TF-IDF cosine similarity on title + description across every cross-school pair. Administrative shells (Thesis, Special Topics, Seminar, Internship) bucketed separately so they don't inflate the overlap.", {
    x: LAYOUT.MARGIN_WIDE, y: 2.8, w: 16, h: 1.2,
    fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY,
  });

  // Stacked bars
  const barY1 = 4.6, barY2 = 6.8, barX = 3.8, barW = 14, barH = 1.3;
  s.addText("ASU \u2192 UTK", {
    x: LAYOUT.MARGIN_WIDE, y: barY1 + 0.3, w: 2, h: 0.5,
    fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MAROON, margin: 0,
  });
  s.addText("UTK \u2192 ASU", {
    x: LAYOUT.MARGIN_WIDE, y: barY2 + 0.3, w: 2, h: 0.5,
    fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true, color: COLORS.UTK_ORANGE, margin: 0,
  });

  // Values (from summary.json re-run with generic_shell filter):
  // asu_to_utk: unique 7270, generic 4339, moderate 2494, strong 394  (total 14497)
  // utk_to_asu: unique 5011, moderate 2460, generic 1534, strong 446  (total 9451)
  function stacked(y, total, segments) {
    let x = barX;
    segments.forEach(seg => {
      const w = (seg.count / total) * barW;
      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w, h: barH, fill: { color: seg.color }, line: { color: COLORS.BLACK, width: 0.5 },
      });
      if (w > 0.9) {
        s.addText(`${seg.count.toLocaleString()}\n${((seg.count / total) * 100).toFixed(1)}%`, {
          x, y, w, h: barH,
          fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true,
          color: seg.textColor || COLORS.WHITE, align: "center", valign: "middle", margin: 0,
        });
      }
      x += w;
    });
  }
  stacked(barY1, 14497, [
    { count: 394, color: "1A5D3A", textColor: COLORS.WHITE },
    { count: 2494, color: "6AA889", textColor: COLORS.WHITE },
    { count: 7270, color: COLORS.CORAL, textColor: COLORS.WHITE },
    { count: 4339, color: "9CA3AF", textColor: COLORS.BLACK },
  ]);
  stacked(barY2, 9451, [
    { count: 446, color: "1A5D3A", textColor: COLORS.WHITE },
    { count: 2460, color: "6AA889", textColor: COLORS.WHITE },
    { count: 5011, color: COLORS.CORAL, textColor: COLORS.WHITE },
    { count: 1534, color: "9CA3AF", textColor: COLORS.BLACK },
  ]);

  // Legend
  const legendItems = [
    { lbl: "Strong \u2265 0.55", color: "1A5D3A" },
    { lbl: "Moderate 0.30\u20130.55", color: "6AA889" },
    { lbl: "Unique < 0.30", color: COLORS.CORAL },
    { lbl: "Admin shell (Thesis/Seminar/\u2026)", color: "9CA3AF" },
  ];
  legendItems.forEach((it, i) => {
    const x = LAYOUT.MARGIN_WIDE + i * 4;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 8.6, w: 0.3, h: 0.3, fill: { color: it.color }, line: { color: COLORS.BLACK, width: 0.5 },
    });
    s.addText(it.lbl, {
      x: x + 0.4, y: 8.55, w: 3.6, h: 0.4,
      fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, color: COLORS.TEXT_DARK, margin: 0,
    });
  });

  // Bottom insight
  s.addText([
    { text: "The headline: ", options: { bold: true, fontSize: FONT.BODY } },
    { text: "only 316 courses are mutual-strong 1:1 equivalents.", options: { fontSize: FONT.BODY } },
    { text: " The rest is either uniquely taught (62% of each catalog) or administratively shaped to look similar.", options: { fontSize: FONT.BODY, italic: true, color: COLORS.TEXT_SECONDARY } },
  ], {
    x: LAYOUT.MARGIN_WIDE, y: 9.4, w: 16, h: 1.5, fontFace: FONT.PRIMARY, color: COLORS.BLACK,
  });
}

// ====================================================================
// SLIDE 5 — Content: Top mutual pairs (backbone)
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };

  addHeaderText(s, "THE RECIPROCAL-CREDIT BACKBONE");
  addGoldHighlight(s, LAYOUT.MARGIN, 1.4, 5, 0.9);
  s.addText("316 clean 1:1 pairs", {
    x: LAYOUT.MARGIN, y: 1.3, w: 14, h: 1.2,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.BLACK, margin: 0,
  });
  s.addText("Sample of the highest-confidence equivalents — both schools name the same content and each picks the other as its closest match. These are the low-friction candidates for automatic credit recognition.", {
    x: LAYOUT.MARGIN, y: 2.8, w: 18, h: 1.2,
    fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY,
  });

  const pairs = [
    { sim: "0.91", asu: "MAT 443", asuT: "Introduction to Abstract Algebra", utk: "MATH 351", utkT: "Introduction to Abstract Algebra" },
    { sim: "0.91", asu: "MAE 587", asuT: "Radiation Heat Transfer", utk: "ME 613",  utkT: "Advanced Radiation Heat Transfer" },
    { sim: "0.89", asu: "SLC 515", asuT: "Second-Language Acquisition", utk: "LING 476", utkT: "Second Language Acquisition" },
    { sim: "0.88", asu: "LAW 613", asuT: "Federal Courts", utk: "LAW 916", utkT: "Federal Courts" },
    { sim: "0.87", asu: "AEE 471", asuT: "Computational Fluid Dynamics", utk: "BME 518", utkT: "Computational Fluid Dynamics" },
    { sim: "0.86", asu: "THP 441", asuT: "Scene Painting", utk: "THEA 455", utkT: "Scene Painting" },
    { sim: "0.86", asu: "REL 315", asuT: "Hebrew Bible (Old Testament)", utk: "JST 311", utkT: "Hebrew Bible/Old Testament" },
    { sim: "0.85", asu: "ARB 102", asuT: "Elementary Arabic II", utk: "ARAB 122", utkT: "Elementary Arabic II" },
    { sim: "0.85", asu: "LAW 516", asuT: "Criminal Law", utk: "LAW 809", utkT: "Criminal Law" },
    { sim: "0.84", asu: "ENG 365", asuT: "History of Film", utk: "ART 100", utkT: "History of Film" },
  ];

  // Header row
  const rowY = 4.3, rowH = 0.55;
  const cols = { sim: 1.2, asu: 7.5, utk: 7.5 };
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
}

// ====================================================================
// SLIDE 6 — Section: Distinctive Strengths
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.NEAR_BLACK };

  s.addText("Where each school\nstands alone.", {
    x: LAYOUT.MARGIN, y: 3, w: 18, h: 7,
    fontSize: 110, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.WHITE, lineSpacingMultiple: 0.95, margin: 0,
  });
  addGoldAccentBlock(s, LAYOUT.MARGIN, 9.6, 1, 0.3);
  s.addText("SECTION 02  \u00B7  WHAT UTK HAS THAT ASU DOESN'T, AND VICE VERSA", {
    x: LAYOUT.MARGIN + 1.2, y: 9.55, w: 16, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.GOLD, valign: "middle", margin: 0,
  });
}

// ====================================================================
// SLIDE 7 — ASU unique strengths
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };

  addCategoryLabel(s, 1.2, 0.8, "ASU uniquely teaches", { color: COLORS.MAROON });

  addGoldHighlight(s, LAYOUT.MARGIN, 1.6, 9, 0.9);
  s.addText("Scale, aviation, transborder, digital.", {
    x: LAYOUT.MARGIN, y: 1.4, w: 18, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.BLACK, margin: 0,
  });

  const themes = [
    { n: "1,437", t: "Advanced research & methods", d: "Analysis, systems, data methods — the signature scale of a R1 online research university.", ex: "Bionanotechnology \u00B7 Actuarial Ratemaking" },
    { n: "882", t: "Transborder / transnational studies", d: "Social, global, political, justice frames. ASU's commitment to Southwest and hemispheric studies.", ex: "Latino and Transnational Issues \u00B7 Transborder Community Dev." },
    { n: "361", t: "Aviation & Air Traffic Control", d: "ATC Tower Operations, TRACON, Instrument Pilot Ground School. Unmatched at UTK.", ex: "ATC 432 TRACON  \u00B7  AMT 222 IFR Ground School" },
    { n: "380", t: "Career & professional development", d: "Leadership, civility, cross-cultural negotiation, professional networking — embedded throughout the catalog.", ex: "Communicating Across Cultures \u00B7 Professional Educator Series" },
    { n: "333", t: "Applied health promotion", d: "Public health, community health, transborder health — tightly coupled to underserved populations.", ex: "Transborder Community Dev. and Health" },
    { n: "267", t: "Digital media & film", d: "Misinformation, military veterans in media, photography, documentary filmmaking.", ex: "Misinformation and Society \u00B7 Military & Veterans in Media" },
  ];

  const cols = 3, rowCount = 2;
  const cardW = 5.8, cardH = 3.7, gapX = 0.35, gapY = 0.3;
  const startX = LAYOUT.MARGIN, startY = 3.1;
  themes.forEach((t, i) => {
    const r = Math.floor(i / cols), c = i % cols;
    const x = startX + c * (cardW + gapX);
    const y = startY + r * (cardH + gapY);
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.15, h: cardH, fill: { color: COLORS.MAROON } });
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.15, y, w: cardW - 0.15, h: cardH,
      fill: { color: COLORS.GRAY_LIGHTEST } });
    s.addText(t.n, {
      x: x + 0.35, y: y + 0.2, w: cardW - 0.5, h: 0.9,
      fontSize: FONT.STAT_SM, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MAROON, margin: 0,
    });
    s.addText("courses", {
      x: x + 0.35, y: y + 1.1, w: cardW - 0.5, h: 0.3,
      fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY, italic: true, margin: 0,
    });
    s.addText(t.t, {
      x: x + 0.35, y: y + 1.5, w: cardW - 0.5, h: 0.6,
      fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
    });
    s.addText(t.d, {
      x: x + 0.35, y: y + 2.2, w: cardW - 0.5, h: 1.2,
      fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, color: COLORS.TEXT_DARK,
    });
    s.addText(t.ex, {
      x: x + 0.35, y: y + 3.3, w: cardW - 0.5, h: 0.3,
      fontSize: FONT.TINY, fontFace: FONT.PRIMARY, italic: true,
      color: COLORS.TEXT_MUTED, margin: 0,
    });
  });
}

// ====================================================================
// SLIDE 8 — UTK unique strengths
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };

  addCategoryLabel(s, 1.2, 0.8, "UTK uniquely teaches", { color: COLORS.UTK_ORANGE });

  addGoldHighlight(s, LAYOUT.MARGIN, 1.6, 9, 0.9);
  s.addText("Music depth, land-grant science, studio practice.", {
    x: LAYOUT.MARGIN, y: 1.4, w: 18, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.BLACK, margin: 0,
  });

  const themes = [
    { n: "812", t: "Music performance & ensembles", d: "Organ, trumpet, tuba, saxophone, horn — a conservatory-grade performance catalog ASU does not mirror.", ex: "MUKB trumpet studio \u00B7 MUVC voice lit." },
    { n: "323", t: "Architecture design studios", d: "Six-year sequenced design studios (ARCH 496 Design IX, collaborative engagement sections). ASU has none at equivalent depth.", ex: "ARCH 496 Design IX: Provocations" },
    { n: "230", t: "Data science & programming", d: "Applied statistics, modeling, reproducibility, simulation. Emerging UTK strength at the grad level.", ex: "BAES 330 Data Analysis Reproducibility" },
    { n: "246", t: "Clinical & nursing practice", d: "Accelerated nursing, maternal-newborn, clinical practicum. Campus-delivered.", ex: "NURS 415 Maternal-Newborn (Accelerated)" },
    { n: "179", t: "Ecology, environment & paleobiology", d: "Climate change, geochemical modeling, taphonomy, trace fossils — deep EEPS coverage.", ex: "EEPS 520 Trace Fossils \u00B7 Geochemical Modeling" },
    { n: "962", t: "Applied agriculture (land-grant)", d: "Forestry, wildlife & fisheries, plant sciences, nuclear engineering — the land-grant signature.", ex: "FORS Silviculture \u00B7 FDSC Vines and Wines" },
  ];

  const cols = 3;
  const cardW = 5.8, cardH = 3.7, gapX = 0.35, gapY = 0.3;
  const startX = LAYOUT.MARGIN, startY = 3.1;
  themes.forEach((t, i) => {
    const r = Math.floor(i / cols), c = i % cols;
    const x = startX + c * (cardW + gapX);
    const y = startY + r * (cardH + gapY);
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.15, h: cardH, fill: { color: COLORS.UTK_ORANGE } });
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.15, y, w: cardW - 0.15, h: cardH,
      fill: { color: COLORS.GRAY_LIGHTEST } });
    s.addText(t.n, {
      x: x + 0.35, y: y + 0.2, w: cardW - 0.5, h: 0.9,
      fontSize: FONT.STAT_SM, fontFace: FONT.PRIMARY, bold: true, color: COLORS.UTK_ORANGE, margin: 0,
    });
    s.addText("courses", {
      x: x + 0.35, y: y + 1.1, w: cardW - 0.5, h: 0.3,
      fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY, italic: true, margin: 0,
    });
    s.addText(t.t, {
      x: x + 0.35, y: y + 1.5, w: cardW - 0.5, h: 0.6,
      fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
    });
    s.addText(t.d, {
      x: x + 0.35, y: y + 2.2, w: cardW - 0.5, h: 1.2,
      fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, color: COLORS.TEXT_DARK,
    });
    s.addText(t.ex, {
      x: x + 0.35, y: y + 3.3, w: cardW - 0.5, h: 0.3,
      fontSize: FONT.TINY, fontFace: FONT.PRIMARY, italic: true,
      color: COLORS.TEXT_MUTED, margin: 0,
    });
  });
}

// ====================================================================
// SLIDE 9 — Designation philosophy comparison
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };

  addCategoryLabel(s, 1.2, 0.8, "Gen-ed philosophies");
  addGoldHighlight(s, LAYOUT.MARGIN, 1.6, 11, 0.9);
  s.addText("Different bets on what gen-ed is for.", {
    x: LAYOUT.MARGIN, y: 1.4, w: 18, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.BLACK, margin: 0,
  });
  s.addText("ASU tags general-ed along traditional discipline axes. UTK's VolCore leads with pedagogy — \u201CEngaged Inquiries\u201D is tagged more widely than any discipline category. That's a different bet on what general education is for.", {
    x: LAYOUT.MARGIN, y: 2.9, w: 18, h: 1.2,
    fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_SECONDARY,
  });

  // Two-column comparison
  const panelY = 4.5, panelH = 5.5;
  // ASU (left)
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
  const asuDesig = [
    ["G", "Global awareness", "575"],
    ["SB", "Social-Behavioral Sci.", "524"],
    ["HU", "Humanities", "507"],
    ["L", "Literacy & Critical Inquiry", "440"],
    ["H", "Historical Awareness", "322"],
    ["C", "Cultural Diversity", "294"],
  ];
  asuDesig.forEach((d, i) => {
    const y = panelY + 1.3 + i * 0.6;
    s.addShape(pres.shapes.RECTANGLE, {
      x: LAYOUT.MARGIN + 0.3, y: y + 0.05, w: 0.9, h: 0.4, fill: { color: COLORS.MAROON },
    });
    s.addText(d[0], {
      x: LAYOUT.MARGIN + 0.3, y: y + 0.05, w: 0.9, h: 0.4,
      fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.WHITE, align: "center", valign: "middle", margin: 0,
    });
    s.addText(d[1], {
      x: LAYOUT.MARGIN + 1.4, y, w: 5.5, h: 0.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.BLACK, valign: "middle", margin: 0,
    });
    s.addText(d[2], {
      x: LAYOUT.MARGIN + 6.9, y, w: 1.6, h: 0.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, bold: true, color: COLORS.GOLD_DARK, align: "right", valign: "middle", margin: 0,
    });
  });

  // UTK (right)
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
  const utkDesig = [
    ["EI", "Engaged Inquiries", "232"],
    ["AH", "Arts & Humanities", "191"],
    ["GCI", "Global Citizenship \u2014 Intl.", "154"],
    ["AOC", "Applied Oral Communication", "96"],
    ["NS", "Natural Sciences", "84"],
    ["WC", "Written Communication", "80"],
  ];
  utkDesig.forEach((d, i) => {
    const y = panelY + 1.3 + i * 0.6;
    const isApplied = ["EI", "AOC", "AAH"].includes(d[0]);
    s.addShape(pres.shapes.RECTANGLE, {
      x: LAYOUT.MARGIN + 9.6, y: y + 0.05, w: 0.9, h: 0.4,
      fill: { color: isApplied ? COLORS.UTK_ORANGE : COLORS.NEAR_BLACK },
    });
    s.addText(d[0], {
      x: LAYOUT.MARGIN + 9.6, y: y + 0.05, w: 0.9, h: 0.4,
      fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.WHITE, align: "center", valign: "middle", margin: 0,
    });
    s.addText(d[1], {
      x: LAYOUT.MARGIN + 10.7, y, w: 5.5, h: 0.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY,
      color: COLORS.BLACK, bold: isApplied, valign: "middle", margin: 0,
    });
    s.addText(d[2], {
      x: LAYOUT.MARGIN + 16.2, y, w: 1.6, h: 0.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, bold: true,
      color: COLORS.UTK_ORANGE, align: "right", valign: "middle", margin: 0,
    });
  });

  s.addText("UTK's top tag is pedagogical (Engaged Inquiries), not disciplinary.", {
    x: LAYOUT.MARGIN + 9.6, y: panelY + 4.8, w: 8, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, italic: true, bold: true,
    color: COLORS.UTK_ORANGE, margin: 0,
  });
}

// ====================================================================
// SLIDE 10 — Modality asymmetry (dark bg, gold numbers)
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.NEAR_BLACK };

  s.addText("THE MODALITY ASYMMETRY", {
    x: LAYOUT.MARGIN, y: 0.7, w: 14, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.GOLD, margin: 0,
  });
  s.addText("3,367", {
    x: LAYOUT.MARGIN, y: 1.4, w: 12, h: 4.2,
    fontSize: 180, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.GOLD, margin: 0, valign: "top",
  });
  s.addText("ASU courses with online sections (23% of catalog).", {
    x: LAYOUT.MARGIN, y: 5.6, w: 13, h: 0.8,
    fontSize: FONT.HEADING, fontFace: FONT.PRIMARY, bold: true, color: COLORS.WHITE, margin: 0,
  });
  s.addText("UTK's catalog does not flag per-course modality. Section-level online/in-person lives in the Banner timetable only — outside the catalog's surface.", {
    x: LAYOUT.MARGIN, y: 6.7, w: 12, h: 2,
    fontSize: FONT.BODY, fontFace: FONT.PRIMARY, color: COLORS.GRAY_MID,
  });

  // Right side: top online subjects
  s.addText("TOP ASU ONLINE SUBJECTS", {
    x: 13.5, y: 1.5, w: 6, h: 0.4,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.GOLD, margin: 0,
  });
  const online = [
    ["BIO", "Biological Sciences", 79],
    ["PSY", "Psychology", 77],
    ["CRJ", "Criminal Justice", 73],
    ["HCR", "Health Care", 65],
    ["SDO", "Sustainable Devt. & Org.", 61],
    ["PAF", "Public Administration", 59],
    ["EEE", "Electrical Engineering", 56],
    ["IFT", "Information Technology", 55],
  ];
  online.forEach((r, i) => {
    const y = 2.1 + i * 0.7;
    s.addText(r[0], {
      x: 13.5, y, w: 1.3, h: 0.5,
      fontSize: FONT.BODY, fontFace: FONT.PRIMARY, bold: true, color: COLORS.GOLD, valign: "middle", margin: 0,
    });
    s.addText(r[1], {
      x: 14.8, y, w: 3.8, h: 0.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.WHITE, valign: "middle", margin: 0,
    });
    s.addText(String(r[2]), {
      x: 18.5, y, w: 0.8, h: 0.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.GRAY_MID, align: "right", valign: "middle", margin: 0,
    });
  });

  s.addText("Implication: ASU's online delivery infrastructure is a strategic asset UTK doesn't have at the catalog layer. A natural exchange value.", {
    x: LAYOUT.MARGIN, y: 9.6, w: 18, h: 1,
    fontSize: FONT.BODY, fontFace: FONT.PRIMARY, italic: true, color: COLORS.GOLD,
  });
}

// ====================================================================
// SLIDE 11 — Section: Joint development
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };

  addMaroonBarPattern(s, 0, LAYOUT.HEIGHT);
  s.addText("Six ways to work together.", {
    x: LAYOUT.MARGIN, y: 3, w: 18, h: 5,
    fontSize: FONT.TITLE_XL, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.WHITE, margin: 0,
  });
  addGoldAccentBlock(s, LAYOUT.MARGIN, 8, 1.2, 0.3);
  s.addText("SECTION 03  \u00B7  FROM ANALYSIS TO OPPORTUNITY", {
    x: LAYOUT.MARGIN + 1.5, y: 7.95, w: 12, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.GOLD, valign: "middle", margin: 0,
  });
}

// ====================================================================
// SLIDE 12 — 6 joint development opportunities
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };

  addHeaderText(s, "JOINT DEVELOPMENT ROADMAP");
  addGoldHighlight(s, LAYOUT.MARGIN, 1.2, 8, 0.9);
  s.addText("Six opportunities the data supports.", {
    x: LAYOUT.MARGIN, y: 1, w: 18, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true,
    color: COLORS.BLACK, margin: 0,
  });

  const opps = [
    { n: "01", t: "Reciprocal-credit compact", d: "Publish a crosswalk for the 316 mutual-strong pairs. Removes re-evaluation friction for transfer and study-abroad.", c: COLORS.GOLD, tag: "FAST \u00B7 REGISTRAR" },
    { n: "02", t: "Online-campus hybrid in applied health", d: "ASU online didactic (PSY, CRJ, HCR) + UTK campus practicum (NURS, clinical). Expands UTK capacity without UTK online build-out.", c: COLORS.CORAL, tag: "MEDIUM TERM" },
    { n: "03", t: "UTK music certificate, ASU online reach", d: "UTK curates a stackable applied-music certificate (ensembles, performance, pedagogy). ASU delivers it at online scale.", c: COLORS.UTK_ORANGE, tag: "CONTENT IP" },
    { n: "04", t: "Agri-environmental graduate bridge", d: "UTK depth (Forestry, Wildlife, Plant Sci.) + ASU breadth (sustainability, environmental eng.) \u2192 dual-listed graduate certificate.", c: COLORS.GREEN, tag: "GRADUATE" },
    { n: "05", t: "Applied-engaged micro-credential", d: "A shared capstone tagged for UTK VolCore EI + ASU upper-div. L. Students earn a credential counted by both frameworks.", c: COLORS.PURPLE, tag: "AMBITIOUS" },
    { n: "06", t: "Specialty program swap", d: "ASU Aviation/ATC/Aerospace  \u2194  UTK Architecture design studios. Articulation agreements for interested students at the partner school.", c: COLORS.TEAL, tag: "LOW VOLUME \u00B7 HIGH SPECIFICITY" },
  ];

  const cols = 3, rowCount = 2;
  const cardW = 5.95, cardH = 3.85, gapX = 0.25, gapY = 0.35;
  const startX = LAYOUT.MARGIN, startY = 2.8;
  opps.forEach((o, i) => {
    const r = Math.floor(i / cols), c = i % cols;
    const x = startX + c * (cardW + gapX);
    const y = startY + r * (cardH + gapY);
    // card
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: cardW, h: cardH,
      fill: { color: COLORS.WHITE }, line: { color: COLORS.GRAY_MID, width: 1 },
    });
    // colored top stripe
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: cardW, h: 0.35, fill: { color: o.c },
    });
    // number big
    s.addText(o.n, {
      x: x + 0.35, y: y + 0.6, w: 1.2, h: 1.1,
      fontSize: FONT.STAT_SM, fontFace: FONT.PRIMARY, bold: true,
      color: o.c, margin: 0,
    });
    // title
    s.addText(o.t, {
      x: x + 1.6, y: y + 0.7, w: cardW - 1.8, h: 1.2,
      fontSize: FONT.BODY_LG, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
    });
    // description
    s.addText(o.d, {
      x: x + 0.35, y: y + 1.9, w: cardW - 0.7, h: 1.5,
      fontSize: FONT.BODY_SM, fontFace: FONT.PRIMARY, color: COLORS.TEXT_DARK,
    });
    // tag pill
    addPill(s, x + 0.35, y + cardH - 0.65, Math.max(2, 0.25 + o.tag.length * 0.11), 0.4, o.tag, COLORS.NEAR_BLACK, COLORS.GOLD);
  });
}

// ====================================================================
// SLIDE 13 — Limitations & Next Steps
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.WHITE };

  addHeaderText(s, "METHOD \u00B7 LIMITATIONS \u00B7 NEXT STEPS");
  addGoldHighlight(s, LAYOUT.MARGIN, 1.2, 8, 0.9);
  s.addText("Trust, but verify.", {
    x: LAYOUT.MARGIN, y: 1, w: 18, h: 1.3,
    fontSize: FONT.TITLE_MD, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK, margin: 0,
  });

  // Two columns
  // Left: limitations
  s.addText("WHAT TO WATCH", {
    x: LAYOUT.MARGIN, y: 3, w: 9, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, bold: true, color: COLORS.MAROON, margin: 0,
  });
  const limits = [
    { h: "Catalog year mismatch", d: "ASU and UTK-grad on 2025\u201326; UTK-undergrad on 2026\u201327. Year-over-year churn is typically 3\u20135% of lines." },
    { h: "Lexical, not semantic", d: "TF-IDF reads vocabulary overlap. Real pedagogical equivalence may read as \u201Cunique\u201D when the language is different." },
    { h: "Admin shell heuristic", d: "Thesis/Seminar/Special-Topics filter is pattern-based. A small number of real courses may be mis-bucketed." },
    { h: "UTK per-course modality absent", d: "Section-level modality lives in Banner. A full parity view requires a term-by-term Banner pull." },
  ];
  limits.forEach((l, i) => {
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
    { h: "Validate the 316 mutual pairs", d: "Registrar-led review. This is the fastest transfer of value from this analysis." },
    { h: "Introduce UTK academic leadership", d: "Share findings with UTK Provost / Online Ed. office. Confirm appetite for one or two opportunities." },
    { h: "Pull UTK Banner modality", d: "Complete the parity view on online delivery. Needed for any revenue-share modeling." },
    { h: "Model revenue for top-2 opportunities", d: "Pick Opp. 01 (reciprocal credit) + one program opportunity. Build the financial case." },
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

// ====================================================================
// SLIDE 14 — Closing: Thank you / Contact
// ====================================================================
{
  let s = pres.addSlide();
  s.background = { color: COLORS.GOLD };

  s.addText("Let's build what\nneither school can\nbuild alone.", {
    x: LAYOUT.MARGIN, y: 1.5, w: 18, h: 7,
    fontSize: 110, fontFace: FONT.PRIMARY, bold: true, color: COLORS.BLACK,
    lineSpacingMultiple: 0.95, valign: "top", margin: 0,
  });

  s.addShape(pres.shapes.RECTANGLE, {
    x: LAYOUT.MARGIN, y: 8.6, w: 1.2, h: 0.2, fill: { color: COLORS.NEAR_BLACK },
  });

  s.addText([
    { text: "Built from a complete scrape of both live catalogs — ", options: { fontSize: FONT.BODY_SM } },
    { text: "23,948 courses across 560 subject codes", options: { fontSize: FONT.BODY_SM, bold: true } },
    { text: " — on 24 April 2026.", options: { fontSize: FONT.BODY_SM } },
  ], { x: LAYOUT.MARGIN, y: 8.9, w: 17, h: 0.5, fontFace: FONT.PRIMARY, color: COLORS.BLACK, margin: 0 });

  s.addText("Source data and analysis scripts: catalog-compare/", {
    x: LAYOUT.MARGIN, y: 9.4, w: 17, h: 0.5,
    fontSize: FONT.CAPTION, fontFace: FONT.PRIMARY, italic: true,
    color: COLORS.TEXT_DARK, margin: 0,
  });

  addEdPlusLogo(s, LAYOUT.MARGIN, 10.3, { scale: 1.2, color: COLORS.BLACK, subtitleColor: COLORS.TEXT_DARK });
}

// Save
const outPath = "/Users/apratlif/Documents/PM Skills/catalog-compare/reports/ASU_UTK_catalog_comparison.pptx";
pres.writeFile({ fileName: outPath })
  .then(() => console.log("Saved:", outPath))
  .catch((err) => { console.error(err); process.exit(1); });
