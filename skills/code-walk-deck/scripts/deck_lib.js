// deck_lib.js — the drawing layer for a code-walk deck.
//
//   const { createDeck } = require("<skill>/scripts/deck_lib.js");
//   const D = createDeck({ title: "...", author: "...", palette: { accent: "D9731A" } });
//   const { pres, C, W, H, M, text, title, box, line, label, legend, pill,
//           code, footer, card, tbl, save } = D;
//
// Everything is drawn as native, editable PowerPoint shapes. Never an image: the
// audience for these decks opens the file and edits it, and an exported PNG of a
// diagram is a dead end for them.
//
// Two things in here are load-bearing rather than convenience:
//
//   code()  solves its own line spacing for the box it was handed and WARNS at build
//           time if the type would fall below MIN_PT. A fixed point size silently
//           overflows the moment a snippet gains a line, and an overflowing code block
//           on a projector is the one failure a code walk cannot ship with.
//
//   DASH    ties line style to how real a thing is — solid runs for real, dotted is
//           built but never exercised, dashed is designed and not built. The audience
//           for a code walk reads diagrams literally, so this carries meaning that
//           colour alone must not.

let pptxgen;
try {
  pptxgen = require("pptxgenjs");
} catch (e) {
  if (e.code !== "MODULE_NOT_FOUND") throw e;
  console.error(
    "pptxgenjs not found. Install it into a scratch directory and point NODE_PATH at it:\n" +
    "  npm install --prefix /tmp/deckdeps pptxgenjs\n" +
    "  NODE_PATH=/tmp/deckdeps/node_modules node build_deck.js\n" +
    "Do not add it as a dependency of the project the deck is about."
  );
  process.exit(1);
}

// Page geometry for LAYOUT_WIDE, in inches. M is the side gutter everything aligns to.
const W = 13.333, H = 7.5, M = 0.5;

// Serif for headings so titles read as titles; mono for anything quoted from a file.
const HF = "Cambria", BF = "Calibri", MF = "Consolas";

const DASH = { built: "solid", tested: "sysDot", planned: "dash" };

// A neutral base palette. Override any key via createDeck({ palette: {...} }). The
// role names matter more than the hexes: pick one role per layer of the system and
// use it consistently, so a reader learns the code once and it holds all deck long.
const BASE_PALETTE = {
  ink: "16222B", text: "22303C", muted: "5E6B75", rule: "C9D1D8", panel: "EEF2F5",
  white: "FFFFFF",
  a: "3B4E8C", aTint: "E9EDF7",         // layer A — e.g. the decision/policy layer
  b: "1E6470", bTint: "E3F0F1",         // layer B — e.g. the runtime
  c: "2E7D5B", cTint: "E4F1EA",         // layer C — e.g. validation
  d: "7A4A8C", dTint: "F3EAF6",         // layer D — e.g. tools
  accent: "D9731A", accentTint: "FCEBDD", // the one vendor/third party worth spotting
  fail: "C0392B", failTint: "F9E0DD",
  good: "2E7D4F",
};

const MIN_PT = 8.5;

function createDeck(opts = {}) {
  const C = Object.assign({}, BASE_PALETTE, opts.palette || {});
  const pres = new pptxgen();
  pres.layout = opts.layout || "LAYOUT_WIDE";
  if (opts.title) pres.title = opts.title;
  if (opts.author) pres.author = opts.author;

  const warnings = [];

  function text(s, t, x, y, w, h, o = {}) {
    s.addText(t, Object.assign({ x, y, w, h, fontFace: BF, fontSize: 14, color: C.text,
      margin: 0, valign: "top", isTextBox: true }, o));
  }

  // A slide title, with an optional small kicker above it naming the section. The
  // kicker is what lets someone who looked away for a minute re-orient without
  // reading the whole slide.
  function title(s, t, kicker, o = {}) {
    if (kicker) text(s, kicker.toUpperCase(), M, 0.35, 9, 0.3,
      { fontSize: 12, bold: true, color: o.kickerColor || C.b, charSpacing: 2 });
    text(s, t, M, 0.62, W - 2 * M, 0.8,
      { fontFace: HF, fontSize: o.fs || 28, bold: true, color: o.color || C.ink });
  }

  // A labelled block. `status` picks the border dash, so a box that has never run
  // for real says so without a legend entry of its own.
  function box(s, x, y, w, h, o = {}) {
    const status = o.status || "built";
    s.addShape(o.round === false ? pres.shapes.RECTANGLE : pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w, h, rectRadius: o.round === false ? undefined : 0.08,
      fill: { color: o.fill || C.white },
      line: { color: o.line || C.muted, width: o.lw || 1.5, dashType: DASH[status] },
    });
    if (o.title || o.sub) {
      const runs = [];
      if (o.title) runs.push({ text: o.title, options: { bold: true, fontSize: o.fs || 14,
        color: o.tc || C.ink, breakLine: !!o.sub } });
      if (o.sub) runs.push({ text: o.sub, options: { fontSize: o.sfs || 10.5,
        color: o.sc || C.muted, fontFace: o.subMono ? MF : BF } });
      text(s, runs, x + 0.08, y + 0.05, w - 0.16, h - 0.1,
        { valign: o.valign || "middle", align: o.align || "center" });
    }
  }

  // pptxgenjs draws a line as a zero-area shape with flip flags, which is fiddly
  // enough to get wrong every time. This hides it: give it two points.
  function line(s, x1, y1, x2, y2, o = {}) {
    s.addShape(pres.shapes.LINE, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.max(Math.abs(x2 - x1), 0.0001),
      h: Math.max(Math.abs(y2 - y1), 0.0001), flipH: x2 < x1, flipV: y2 < y1,
      line: { color: o.color || C.muted, width: o.w || 1.5, dashType: DASH[o.status || "built"],
        endArrowType: o.noArrow ? undefined : "triangle",
        beginArrowType: o.both ? "triangle" : undefined },
    });
  }

  function label(s, t, x, y, w, o = {}) {
    text(s, t, x, y, w, o.h || 0.26, Object.assign({ fontSize: 10.5, color: C.muted,
      fontFace: o.mono ? MF : BF, align: o.align || "center", valign: "middle" }, o));
  }

  // The status legend. Put it on any slide that mixes dash styles; leave it off
  // slides that use only one, where it is noise.
  function legend(s, x, y, o = {}) {
    const items = o.items || [["built, runs for real", "built"],
                              ["built and tested, never run for real", "tested"],
                              ["designed for, not implemented", "planned"]];
    const tw = o.tw || 3.0;
    items.forEach(([t, st], i) => {
      const yy = y + i * 0.25;
      s.addShape(pres.shapes.LINE, { x, y: yy + 0.12, w: 0.42, h: 0,
        line: { color: C.text, width: 1.75, dashType: DASH[st] } });
      text(s, t, x + 0.52, yy, tw, 0.25, { fontSize: 9.5, color: C.muted, valign: "middle" });
    });
    if (o.accentLabel) {
      const yy = y + items.length * 0.25;
      s.addShape(pres.shapes.RECTANGLE, { x: x + 0.08, y: yy + 0.04, w: 0.24, h: 0.16,
        fill: { color: C.accentTint }, line: { color: C.accent, width: 1.5 } });
      text(s, o.accentLabel, x + 0.52, yy, tw, 0.25,
        { fontSize: 9.5, color: C.accent, bold: true, valign: "middle" });
    }
  }

  function pill(s, t, x, y, w, color, o = {}) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: o.h || 0.3, rectRadius: 0.15,
      fill: { color: o.fill || color }, line: { color, width: 1 } });
    text(s, t, x, y, w, o.h || 0.3, { fontSize: o.fs || 10.5, bold: true,
      color: o.tc || C.white, align: "center", valign: "middle" });
  }

  // `lines` is an array of source lines. Pass `anchor` to print the file:line and the
  // fidelity mark under the block — a quoted snippet with no citation is worth less
  // than no snippet, because nobody can check it.
  function code(s, lines, x, y, w, h, o = {}) {
    const want = o.ls || 13;
    let ls = Math.min(want, ((h - 0.2) * 72) / lines.length);
    if (ls < MIN_PT) {
      const msg = `code block at y=${y} needs ${lines.length} lines in ${h}" ` +
        `(${ls.toFixed(1)}pt < ${MIN_PT}pt floor) - shorten it or grow the box`;
      warnings.push(msg);
      console.warn("  ! " + msg);
      ls = MIN_PT;
    }
    const fs = Math.min(o.fs || 10.5, ls * 0.80);
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h,
      fill: { color: o.fill || C.ink }, line: { color: o.fill || C.ink } });
    text(s, lines.join("\n"), x + 0.11, y + 0.1, w - 0.22, h - 0.2,
      { fontFace: MF, fontSize: fs, color: o.color || "DCE5EC", lineSpacing: ls });
    if (o.anchor) text(s, o.anchor, x, y + h + 0.02, w, 0.2,
      { fontFace: MF, fontSize: 8.5, color: C.muted, align: "right" });
  }

  function footer(s, t) {
    text(s, t, M, H - 0.4, W - 2 * M, 0.25, { fontSize: 10, color: C.muted, italic: true });
  }

  // A tinted panel with a heading and bullets. Keep headings short — the heading box
  // is a single line, and a heading that wraps lands on top of the first bullet.
  function card(s, x, y, w, h, heading, body, o = {}) {
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h,
      fill: { color: o.fill || C.panel }, line: { color: o.line || o.fill || C.panel } });
    text(s, heading, x + 0.14, y + 0.09, w - 0.28, 0.3,
      { fontSize: o.hfs || 13, bold: true, color: o.hc || C.ink });
    if (Array.isArray(body)) {
      text(s, body.map((t, j) => ({ text: t,
        options: { bullet: true, breakLine: j < body.length - 1 } })),
        x + 0.14, y + 0.43, w - 0.28, h - 0.52,
        { fontSize: o.fs || 11.5, color: C.text, paraSpaceAfter: 4 });
    } else {
      text(s, body, x + 0.14, y + 0.43, w - 0.28, h - 0.52,
        { fontSize: o.fs || 11.5, color: C.text });
    }
  }

  // An act divider: the dimension, the definition you are using for it, the claims the
  // act will make, and -- in red, before the act rather than after it -- the weakest of
  // them. Geometry is fixed on purpose: three identical dividers read as a structure,
  // three artful ones read as three slides.
  //
  //   divider(s, { n: 2, name: "Performance", definition: "...",
  //                claims: [["heading", "one line of evidence"], ...],
  //                caveat: "the one you would rather not say" });
  //
  // Three claims is the budget. A fourth pushes the caveat band into the footer, and a
  // divider that needs four claims is really a content slide.
  function divider(s, o) {
    s.background = { color: C.ink };
    text(s, `ACT ${o.n}${o.of ? ` OF ${o.of}` : ""}`, M, 0.85, 4, 0.3,
      { fontSize: 13, bold: true, color: C.muted, charSpacing: 3 });
    text(s, String(o.name).toUpperCase(), M, 1.2, 9.5, 0.95,
      { fontFace: HF, fontSize: 46, bold: true, color: C.white, charSpacing: 1 });
    text(s, o.definition, M, 2.3, W - 2 * M - 0.2, 0.6,
      { fontSize: 16, color: "C8D4DD", italic: true });
    (o.claims || []).forEach(([h, b], i) => {
      const y = 3.2 + i * 0.86;
      s.addShape(pres.shapes.RECTANGLE, { x: M, y: y + 0.04, w: 0.06, h: 0.6,
        fill: { color: C.accent }, line: { color: C.accent } });
      // A warm mid-tone, not accentTint: the tints are fills, and on an ink
      // background they come out close enough to white to lose the hierarchy.
      text(s, h, M + 0.24, y, W - 2 * M - 0.24, 0.3,
        { fontSize: 15, bold: true, color: "F0C898" });
      text(s, b, M + 0.24, y + 0.3, W - 2 * M - 0.24, 0.32, { fontSize: 12, color: "C8D4DD" });
    });
    if (o.caveat) {
      s.addShape(pres.shapes.RECTANGLE, { x: M, y: 6.1, w: W - 2 * M, h: 0.84,
        fill: { color: "3A2222" }, line: { color: C.fail, width: 2 } });
      text(s, [
        { text: "The weakest claim in this act:  ", options: { bold: true, color: "E8A0A0" } },
        { text: o.caveat, options: { color: C.white } },
      ], M + 0.18, 6.22, W - 2 * M - 0.36, 0.64, { fontSize: 13 });
    }
  }

  // `mono`/`center` are column indices. `cell(i, j, value)` may return extra options
  // for one cell, which is how a "refused"/"ok" column gets coloured by its content.
  function tbl(s, hdr, rows, x, y, cw, o = {}) {
    const mono = o.mono || [], ctr = o.center || [];
    const body = rows.map((r, i) => r.map((c, j) => ({ text: String(c), options: Object.assign({
      fontFace: mono.includes(j) ? MF : BF,
      fontSize: mono.includes(j) ? (o.mfs || 9.5) : (o.fs || 11.5),
      bold: o.boldFirst !== false && j === 0,
      color: mono.includes(j) ? C.muted : C.text,
      align: ctr.includes(j) ? "center" : "left",
      fill: { color: i % 2 ? C.white : C.panel } }, (o.cell && o.cell(i, j, c)) || {}) })));
    const head = hdr.map(h => ({ text: h, options: { bold: true, color: C.white,
      fill: { color: o.hfill || C.b }, fontSize: o.hfs || 11 } }));
    s.addTable([head].concat(body), { x, y, w: cw.reduce((a, b) => a + b), colW: cw,
      border: { type: "solid", color: C.rule, pt: 0.75 }, fontFace: BF, valign: "middle",
      rowH: o.rowH, margin: o.margin || 0.07 });
  }

  // Writes the file and reports any code-block warnings together at the end, where
  // they are hard to scroll past.
  function save(fileName) {
    return pres.writeFile({ fileName }).then(f => {
      if (warnings.length) {
        console.warn(`\n  ${warnings.length} code block(s) below the ${MIN_PT}pt floor — ` +
          "fix these before presenting.");
      }
      console.log("wrote", f);
      return f;
    });
  }

  return { pres, C, W, H, M, HF, BF, MF, DASH, MIN_PT, warnings,
           text, title, divider, box, line, label, legend, pill, code, footer, card, tbl, save };
}

module.exports = { createDeck, BASE_PALETTE, W, H, M, HF, BF, MF, DASH, MIN_PT };
