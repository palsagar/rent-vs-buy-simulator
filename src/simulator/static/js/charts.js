// Plotly.js builders — one shared GitHub-dark theme. Buy #f0883e,
// Rent #58a6ff; bands/neutrals muted; direct line labels, no legends.

import { INPUT_DEFS } from "./fields.js";
import { MINUS, fmtMoney, getCurrencySymbol } from "./format.js";

const BUY = "#f0883e";
const RENT = "#58a6ff";
const MUTED = "#8b949e";
const TEXT = "#e6edf3";
const GRID = "rgba(48,54,61,0.6)";

// Tornado bars. Neutral on purpose: the tinted halves behind them carry
// the Buy and Rent colours, and the tested value printed at each bar end
// says which way the number moved, so the bar itself encodes nothing.
const BAR = "#6e7681";

// Below this chart width the tornado's category labels took half the plot,
// so they move above their bars and the bars get the full width.
const NARROW_CHART_PX = 480;

// Plotly's tickprefix renders before EVERYTHING, minus sign included, so
// a prefixed axis reads "EUR-30M". d3-format's currency type puts the
// symbol after the sign instead -- "-EUR30M", how money is normally
// written, and what fmtTick already produces on the symlog axis. Plotly
// takes the symbol from a registered locale rather than from the format
// string, hence the registration below.
const CURRENCY_LOCALE = "app-currency";

// Registration is per layout build, not once at load: the active
// currency changes with the region, and re-registering an existing name
// does take effect. An unregistered name falls back to "$" SILENTLY, so
// this must stay next to the getCurrencySymbol() read rather than drift
// into module scope where it would run once with whatever loaded first.
function currencyTickformat() {
  Plotly.register({
    moduleType: "locale",
    name: CURRENCY_LOCALE,
    dictionary: {},
    format: { currency: [getCurrencySymbol(), ""], minus: MINUS },
  });
  return "$~s";
}

// Hover money is formatted in JS and carried in customdata, NOT by a d3
// format spec in the template. Two reasons, both verified on 2.35.2:
//
//   - a hand-built `${symbol}%{x}` prefix renders "EUR-3,986,681", for
//     the same reason tickprefix renders "EUR-30M";
//   - the d3 currency type fixes that ordering, but its minus is a
//     hard-coded ASCII hyphen. Plotly rewrites the sign to U+2212 on the
//     TICK path only, and the locale's own `minus` key does not reach
//     hovers either -- so the hover would spell the sign differently
//     from the axis tick sitting directly behind it.
//
// fmtMoney settles both: one symbol position, one glyph, everywhere.
function moneyHover(values) {
  return Array.from(values, fmtMoney);
}

// The mode bar is for a mouse: on touch it would sit over the chart and a
// drag mode would capture the page scroll. Zooming a category chart means
// nothing, so the bar charts only offer the image.
const CHART_EXPORTS = {
  "decision-chart": { file: "rent-or-buy-net-value", zoom: true },
  "fan-chart": { file: "rent-or-buy-futures", zoom: true },
  "tornado-chart": { file: "rent-or-buy-what-could-change", zoom: false },
  "outflow-chart": { file: "rent-or-buy-out-of-pocket", zoom: true },
  "breakdown-chart": { file: "rent-or-buy-ownership-costs", zoom: false },
};

function plotConfig(el) {
  const base = { responsive: true, locale: CURRENCY_LOCALE, displaylogo: false };
  const mouse = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const spec = CHART_EXPORTS[el.id];
  if (!mouse || !spec) return { ...base, displayModeBar: false };
  // Plotly's own title for this is "Download plot as a png".
  const save = {
    name: "save-image",
    title: "Save as image",
    icon: Plotly.Icons.camera,
    click: (gd) => Plotly.downloadImage(gd, { format: "png", scale: 2, filename: spec.file }),
  };
  return {
    ...base,
    displayModeBar: "hover",
    modeBarButtons: [spec.zoom ? ["zoom2d", "pan2d", "resetScale2d", save] : [save]],
  };
}

function baseLayout(xTitle) {
  return {
    paper_bgcolor: "#161b22",
    plot_bgcolor: "#161b22",
    font: { color: MUTED, family: "-apple-system, 'Segoe UI', sans-serif", size: 12 },
    margin: { t: 16, r: 64, b: 40, l: 56 },
    showlegend: false,
    hovermode: "x unified",
    // No drag-to-zoom: on a touch screen it captures the swipe, so a page
    // scroll that starts on a chart zooms the chart instead. Taps still hover.
    dragmode: false,
    // Upright in the right margin, clear of the labels along the top.
    modebar: { orientation: "v", bgcolor: "rgba(0,0,0,0)", color: MUTED, activecolor: TEXT },
    xaxis: { title: { text: xTitle }, gridcolor: GRID, zerolinecolor: "#30363d" },
    yaxis: {
      gridcolor: GRID,
      zerolinecolor: "#30363d",
      tickformat: currencyTickformat(),
    },
  };
}

// Horizontal-bar charts put money on X and categories on Y, so the base
// layout's money formatting has to MOVE axes, not just come off Y.
// Deleting it alone left the money axis with no currency and no SI
// compaction at all -- the tornado read "-0.5M" where every other chart
// reads "-EUR500k".
//
// Plotly ignores a tickformat on a category axis, so leaving the Y copy
// in place would be harmless to render -- it is deleted anyway so the
// layout says what it means, and so the guard below has something
// unambiguous to test.
// Not idempotent by construction, so it refuses to run twice: a second
// call would read the already-deleted y-axis key and assign undefined,
// silently wiping the currency it just installed.
function moveCurrencyToXAxis(layout) {
  if (layout.yaxis.tickformat === undefined) return;
  layout.xaxis.tickformat = layout.yaxis.tickformat;
  delete layout.yaxis.tickformat;
}

// `fwd`, when given, maps dollars to symlog space (see maybeSymlog). The raw
// dollar value rides along in customdata so hover still reads in dollars.
function strategyTraces(x, buyY, rentY, fwd) {
  const mk = (yRaw, color, name) => {
    const base = { x, mode: "lines", line: { color, width: 2 }, name };
    return fwd
      ? { ...base, y: yRaw.map(fwd), customdata: moneyHover(yRaw), hovertemplate: `${name} %{customdata}<extra></extra>` }
      : { ...base, y: yRaw, customdata: moneyHover(yRaw), hovertemplate: `${name} %{customdata}<extra></extra>` };
  };
  return [mk(buyY, BUY, "Buy"), mk(rentY, RENT, "Rent")];
}

// End labels closer than this are pushed apart so they never overprint.
// Larger than the ~15px text box because Plotly pads the autorange ~5%,
// which makes the estimate below slightly generous.
const LABEL_GAP_PX = 18;

// The plot area's height: the chart div minus the top and bottom margins.
function plotHeight(el, layout) {
  return el.clientHeight - layout.margin.t - layout.margin.b;
}

// `plotHeightPx` turns the data-space distance between the two end values
// into pixels, so the labels are pushed apart only when they would touch.
function endLabelAnnotations(x, buyY, rentY, fwd, plotHeightPx) {
  const y = (v) => (fwd ? fwd(v) : v);
  let lo = Infinity;
  let hi = -Infinity;
  for (const arr of [buyY, rentY]) {
    for (const v of arr) {
      const t = y(v);
      if (t < lo) lo = t;
      if (t > hi) hi = t;
    }
  }
  const buyEnd = y(buyY.at(-1));
  const rentEnd = y(rentY.at(-1));
  const gapPx = hi > lo ? (Math.abs(buyEnd - rentEnd) / (hi - lo)) * plotHeightPx : 0;
  const push = Math.max(0, (LABEL_GAP_PX - gapPx) / 2);
  const buyUp = buyEnd >= rentEnd ? 1 : -1;
  return [
    { x: x.at(-1), y: buyEnd, yshift: buyUp * push, text: "Buy", font: { color: BUY, size: 12 }, showarrow: false, xanchor: "left", xshift: 6 },
    { x: x.at(-1), y: rentEnd, yshift: -buyUp * push, text: "Rent", font: { color: RENT, size: 12 }, showarrow: false, xanchor: "left", xshift: 6 },
  ];
}

// --- Adaptive y-scale ----------------------------------------------------
// Net-worth and outflow curves can span orders of magnitude at long horizons.
// When the two final outcomes diverge by at least this factor, a linear axis
// squashes the smaller curve against the baseline, so we switch to a symlog
// scale: sign-preserving, ~linear near zero, log-like for large magnitudes.
const SCALE_DISPARITY = 10;

// Symlog forward transform. `t` is the linear-region half-width: below |t| the
// mapping is ~linear (so it survives sign changes and zero crossings), above it
// compresses logarithmically.
function symlogFwd(y, t) {
  return Math.sign(y) * Math.log10(1 + Math.abs(y) / t);
}

// True when the larger final outcome dwarfs the smaller by >= SCALE_DISPARITY.
function outcomesDisparate(buyY, rentY) {
  const a = Math.abs(buyY.at(-1));
  const b = Math.abs(rentY.at(-1));
  return Math.max(a, b) / Math.max(Math.min(a, b), 1) >= SCALE_DISPARITY;
}

// Compact tick label (1k / 30k / 1.0M in the active currency). Like
// fmtCompact but compacts down to 1k so a symlog axis never mixes
// "1,000" with "10k".
//
// Signs come from MINUS, the same glyph the registered locale gives
// Plotly, so hand-formatted and Plotly-formatted labels agree.
function fmtTick(v) {
  const sign = v < 0 ? MINUS : "";
  const cur = getCurrencySymbol();
  const a = Math.abs(v);
  if (a >= 1e6) return `${sign}${cur}${(a / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `${sign}${cur}${Math.round(a / 1e3)}k`;
  return `${sign}${cur}${Math.round(a)}`;
}

// Nice dollar tick values (…, -1M, -300k, 0, 300k, 1M, …) at 1x/3x per decade
// across the top ~3 decades of the range, clipped to the data's [min, max].
// Limiting to the top decades keeps labels from crowding near zero, where
// symlog compresses every decade into a shrinking band.
// Precondition: peak > 0 (guaranteed by maybeSymlog's guard) — a zero peak
// makes topExp -Infinity and the loop below never terminates.
function symlogTicks(min, max) {
  const peak = Math.max(Math.abs(min), Math.abs(max));
  const topExp = Math.floor(Math.log10(peak));
  const vals = new Set([0]);
  for (let e = topExp - 2; e <= topExp; e++) {
    for (const m of [1, 3]) {
      vals.add(m * 10 ** e);
      vals.add(-m * 10 ** e);
    }
  }
  return [...vals].filter((v) => v >= min && v <= max).sort((a, b) => a - b);
}

// If the two series' outcomes are disparate, install a symlog y-axis on
// `layout` (custom dollar ticks) and return the forward transform for the
// caller to plot data and annotations through. Returns null to keep linear.
function maybeSymlog(layout, buyY, rentY) {
  if (!outcomesDisparate(buyY, rentY)) return null;
  // One pass for the data range — no spreading the full monthly series into
  // Math.min/max(...), which would cap out on the argument count as it grows.
  let min = Infinity;
  let max = -Infinity;
  for (const arr of [buyY, rentY]) {
    for (const v of arr) {
      if (v < min) min = v;
      if (v > max) max = v;
    }
  }
  const peak = Math.max(Math.abs(min), Math.abs(max));
  if (!(peak > 0)) return null;
  const t = peak / 1e4; // linear knee at 0.01% of peak; everything else compresses
  const fwd = (y) => symlogFwd(y, t);
  const ticks = symlogTicks(min, max);
  layout.yaxis.tickmode = "array";
  layout.yaxis.tickvals = ticks.map(fwd);
  layout.yaxis.ticktext = ticks.map(fmtTick);
  delete layout.yaxis.tickformat;
  return fwd;
}

// Past this fraction of the x-range the breakeven label sits to the left of
// its line, so a breakeven near the horizon keeps its label inside the plot.
// At the midpoint the ~85px label fits on either side of the line: 102px of
// room each side on a 390px phone, 87px on a 360px one.
const BREAKEVEN_FLIP_FRACTION = 0.5;

export function renderDecisionChart(el, series, breakevenYear) {
  const x = series.year;
  const layout = baseLayout("Years");
  // End at the horizon: autorange also fits the end labels, which stretched
  // the axis to ~1.8x the horizon and left the right of the plot empty.
  layout.xaxis.range = [x[0], x.at(-1)];
  // The series is monthly, so the raw hover x reads "6.416667".
  layout.xaxis.hoverformat = ".1f";
  const fwd = maybeSymlog(layout, series.netBuy, series.netRent);
  layout.annotations = endLabelAnnotations(x, series.netBuy, series.netRent, fwd, plotHeight(el, layout));
  if (breakevenYear != null) {
    const labelLeft = (breakevenYear - x[0]) / (x.at(-1) - x[0]) > BREAKEVEN_FLIP_FRACTION;
    layout.shapes = [
      { type: "line", x0: breakevenYear, x1: breakevenYear, yref: "paper", y0: 0, y1: 1, line: { color: "#484f58", width: 1, dash: "dash" } },
    ];
    layout.annotations.push({
      x: breakevenYear, yref: "paper", y: 1, yanchor: "bottom", xanchor: labelLeft ? "right" : "left", xshift: labelLeft ? -4 : 4,
      text: `breakeven ${breakevenYear.toFixed(1)}y`, font: { color: MUTED, size: 11 }, showarrow: false,
    });
  }
  Plotly.react(el, strategyTraces(x, series.netBuy, series.netRent, fwd), layout, plotConfig(el));
}

export function renderFanChart(el, mc) {
  const x = mc.yearAxis;
  const row = Object.fromEntries(mc.percentileLevels.map((level, i) => [level, mc.differencePercentiles[i]]));
  const traces = [
    { x, y: row[95], mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
    { x, y: row[5], mode: "lines", line: { width: 0 }, fill: "tonexty", fillcolor: "rgba(139,148,158,0.14)", hoverinfo: "skip", showlegend: false },
    { x, y: row[75], mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
    { x, y: row[25], mode: "lines", line: { width: 0 }, fill: "tonexty", fillcolor: "rgba(139,148,158,0.24)", hoverinfo: "skip", showlegend: false },
    { x, y: row[50], mode: "lines", line: { color: "#e6edf3", width: 1.5 }, name: "Median", customdata: moneyHover(row[50]), hovertemplate: `Median %{customdata}<extra></extra>`, showlegend: false },
  ];
  const layout = baseLayout("Years");
  layout.xaxis.hoverformat = ".1f";
  layout.yaxis.title = { text: "Buy − Rent" };
  layout.shapes = [
    { type: "line", x0: 0, x1: x.at(-1), y0: 0, y1: 0, line: { color: "#484f58", width: 1, dash: "dash" } },
  ];
  Plotly.react(el, traces, layout, plotConfig(el));
}

// Render a perturbed input the way its own slider would. INPUT_DEFS is
// the single source of truth for both halves of that: the scale (rent
// inflation is STORED as 0.03 but shown as "3.0%") and the formatter (a
// rate, a price and a flat levy do not share one format string). The
// payload ships the config field name precisely so the tornado can look
// the field up rather than infer it from a prose bar label.
function fmtFieldValue(fieldKey, storedValue) {
  const def = INPUT_DEFS.find((d) => d.key === fieldKey);
  if (def === undefined) return "";
  return def.fmt(storedValue * (def.scale ?? 1));
}

// The tested values need four arrays the bars themselves do not. They are
// a strictly additive part of the payload, so a response that predates
// them still has everything needed to draw the chart -- but spreading a
// missing one throws, and the throw happens AFTER the fan chart has
// already rendered, leaving the tornado showing the previous region's
// bars with nothing on screen saying they are stale. Reachable during a
// rolling deploy (new bundle, old container) or from a cached API
// response. Degrade to one ungrouped list under the server's own names
// instead of stranding the chart.
function tornadoRanges(tornado, count) {
  const arrays = [
    tornado.fields,
    tornado.baseInput,
    tornado.lowInput,
    tornado.highInput,
  ];
  if (arrays.some((a) => !Array.isArray(a) || a.length !== count)) return null;
  return arrays;
}

// The tornado's two group headings. A bar's group is the input panel
// section its field lives in: the outlook assumptions are guesses nobody
// can check today, everything else is known (or negotiable) when you sign.
const FUTURE_GROUP = "Guesses about the future";
const YOURS_GROUP = "Your numbers";

// Below this gap between a tested value and the current one, the side was
// clamped at a slider limit and tested nothing. Absolute rather than
// relative, because a clamped side equals the current value exactly and
// every real test moves by a whole step, whatever the field's units.
const SAME_INPUT_TOLERANCE = 1e-9;

// The slider limit a tested value sits on, if any: "min" for a lower side
// at its slider's minimum, "max" for a higher side at its maximum. The
// engine clamps every test to these same bounds (_UI_MINIMUM and
// _UI_MAXIMUM mirror them), so a clamped side lands on the bound exactly.
// Compared in stored units: rent inflation's slider shows 10% for 0.1.
function sliderLimit(def, direction, stored) {
  if (def?.min === undefined) return null;
  const [limit, bound] = direction === "lower" ? ["min", def.min] : ["max", def.max];
  return Math.abs(stored - bound / (def.scale ?? 1)) < SAME_INPUT_TOLERANCE ? limit : null;
}

const LIMIT_WORDS = { min: "minimum", max: "maximum" };

// The value printed at a bar end, marked when its test stopped at a
// slider limit instead of moving a full step.
function endLabel(side) {
  if (side.tested === null) return "";
  return side.limit === null ? side.tested : `${side.tested} (${side.limit})`;
}

// One row per bar, widest first as the payload sends them. Each side
// carries the verdict it produced and, when the payload has them, the
// tested and current values formatted like their slider. A side that is
// already at a slider limit is marked `untested`: there is no bar to draw
// for it. `limit` names the slider limit a side stopped at, if any.
function tornadoRows(tornado) {
  const ranges = tornadoRanges(tornado, tornado.params.length);
  return tornado.params.map((name, i) => {
    if (ranges === null) {
      return {
        label: name,
        future: false,
        current: null,
        sides: [
          { end: tornado.low[i], tested: null, untested: false, direction: "lower", limit: null },
          { end: tornado.high[i], tested: null, untested: false, direction: "higher", limit: null },
        ],
      };
    }
    const [fields, baseIn, lowIn, highIn] = ranges;
    const def = INPUT_DEFS.find((d) => d.key === fields[i]);
    const untested = (v) => Math.abs(v - baseIn[i]) < SAME_INPUT_TOLERANCE;
    return {
      label: def?.label ?? name,
      future: def?.section === "assumptions",
      current: fmtFieldValue(fields[i], baseIn[i]),
      sides: [
        { end: tornado.low[i], tested: fmtFieldValue(fields[i], lowIn[i]), untested: untested(lowIn[i]), direction: "lower", limit: sliderLimit(def, "lower", lowIn[i]) },
        { end: tornado.high[i], tested: fmtFieldValue(fields[i], highIn[i]), untested: untested(highIn[i]), direction: "higher", limit: sliderLimit(def, "higher", highIn[i]) },
      ],
    };
  });
}

// A Buy - Rent gap under half a unit of currency is a tie: it would print
// as "~$0". Mirrors engine.TIE_TOLERANCE.
const TIE_TOLERANCE = 0.5;

// The server's verdict rule (api._winner) for one Buy - Rent gap.
function winnerOf(diff) {
  if (Math.abs(diff) < TIE_TOLERANCE) return "tie";
  return diff > 0 ? "buy" : "rent";
}

function aheadBy(diff) {
  const winner = winnerOf(diff);
  if (winner === "tie") return "Buying and renting level";
  return winner === "buy" ? `Buying ahead by ${fmtMoney(diff)}` : `Renting ahead by ${fmtMoney(-diff)}`;
}

function lowerFirst(text) {
  return text.charAt(0).toLowerCase() + text.slice(1);
}

// A row's name without its bracketed qualifier, for sentences where the
// tested value already carries the unit: "property levy at 1.70%", not
// "property levy (% of value per year) at 1.70%".
function shortLabel(label) {
  return label.replace(/\s*\(.*\)$/, "");
}

// What one side tested, as the start of a sentence: "Equity growth at
// 11.7% instead of 7.0%", or "Higher equity growth" when the payload
// predates the tested values. The hover uses it as is, the summary
// lower-cases its first letter.
function testedPhrase(row, side) {
  if (side.tested === null) {
    return `${side.direction.charAt(0).toUpperCase()}${side.direction.slice(1)} ${lowerFirst(row.label)}`;
  }
  return `${row.label} at ${side.tested} instead of ${row.current}`;
}

const COUNT_WORDS = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"];

// Bars named in the summary when more than this many flip the answer.
const MAX_NAMED_FLIPS = 3;

// "a, b, or c" / "a, b, and c".
function listPhrase(items, conjunction) {
  return items.length === 1 ? items[0] : `${items.slice(0, -1).join(", ")}, ${conjunction} ${items.at(-1)}`;
}

// The sentence above the tornado: which single changes would flip the
// answer. A side flips it when its verdict names the other strategy. The
// winner follows the server's own rule (winnerOf), so an exact tie gets
// its own line, and a toss-up gets one too, decided by the same flag as
// the headline, so the two never disagree.
export function tornadoSummary(tornado, tossUp) {
  const winner = winnerOf(tornado.base);
  if (winner === "tie") return "Buying and renting are level, so any change here would put one of them ahead.";
  if (tossUp) return "The answer is too close to call, so small changes can tip it either way.";
  const buyAhead = winner === "buy";
  const other = buyAhead ? "rent" : "buy";
  const flips = tornadoRows(tornado).flatMap((row) => {
    const side = row.sides.find((s) => !s.untested && winnerOf(s.end) === other);
    const named = { ...row, label: shortLabel(row.label) };
    return side === undefined ? [] : [lowerFirst(testedPhrase(named, side))];
  });
  if (flips.length === 0) {
    return `No single change here flips the answer. ${buyAhead ? "Buying" : "Renting"} stays ahead in every test.`;
  }
  const count = COUNT_WORDS[flips.length - 1] ?? String(flips.length);
  const lead = `${count} of these could flip the answer to ${buyAhead ? "renting" : "buying"} on ${flips.length === 1 ? "its" : "their"} own`;
  if (flips.length > MAX_NAMED_FLIPS) {
    return `${lead}. The biggest are ${listPhrase(flips.slice(0, MAX_NAMED_FLIPS), "and")}.`;
  }
  return `${lead}: ${listPhrase(flips, "or")}.`;
}

// An empty side of the axis is extended by this fraction of the data
// span, which keeps the tie line at least a quarter of the way in from
// either edge. Each tinted half then has room for its label even when
// every bar lies on one side.
const MIN_HALF_FRACTION = 1 / 3;

// Room past the outermost bar ends for the tested values printed there.
const END_LABEL_PAD = 0.14;

// The width of an 11 px label beside a line, estimated before Plotly lays
// it out: pixels per character (about 6 when measured), plus its gap from
// the line. Both err wide, so a label is never given too little room.
const SIDE_LABEL_CHAR_PX = 7;
const SIDE_LABEL_GAP_PX = 8;

// The same estimate for the 12 px row names that set the left margin on a
// wide chart. Erring wide here only reserves a little more room.
const ROW_NAME_CHAR_PX = 7;

// No label claims more than this share of the plot width, so two labels
// that run towards each other's edges always fit together.
const MAX_LABEL_SHARE = 0.45;

// Rounds of growing the axis edges in turn. Each round shrinks what is
// still missing to a fraction of what it was, so a few rounds settle it.
const ROOM_ROUNDS = 10;

// The tornado's side margins on a phone, where the row names sit above
// their bars instead of in the left margin.
const NARROW_MARGIN = { l: 16, r: 24 };

// Behind the tornado, each half of the axis is tinted with the colour of
// the strategy that is ahead there.
const HALF_TINT_ALPHA = 0.1;

function tint(hex, alpha) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${alpha})`;
}

// One side of one row as Plotly needs it. Headings and untested sides
// draw no bar; an untested side at a slider limit gets a label of its own
// from limitAnnotations instead.
function sideCell(slot, k, base) {
  const side = slot.heading ? null : slot.sides[k];
  if (side === null || side.untested) return { x: null, text: "", hover: "" };
  const atLimit = side.limit === null ? "" : ` (the slider ${LIMIT_WORDS[side.limit]})`;
  return {
    x: side.end - base,
    text: endLabel(side),
    hover: `${testedPhrase({ ...slot, label: shortLabel(slot.label) }, side)}${atLimit}<br>${aheadBy(side.end)}`,
  };
}

// A side already at its slider limit tests nothing, so it has no bar. A
// label at your verdict says why that side is empty. It sits where the
// bar would have gone: away from the other side's bar.
function limitAnnotations(slots, base) {
  return slots.flatMap((slot) => {
    if (slot.heading) return [];
    return slot.sides.flatMap((side, k) => {
      if (!side.untested || side.limit === null) return [];
      const otherGoesRight = slot.sides[1 - k].end > base;
      return [
        {
          name: "limit-label",
          x: base,
          y: slot.label,
          xanchor: otherGoesRight ? "right" : "left",
          xshift: otherGoesRight ? -4 : 4,
          text: endLabel(side),
          hovertext: `${shortLabel(slot.label)} is already at its slider ${LIMIT_WORDS[side.limit]}, so it can't be tested ${side.direction}.`,
          showarrow: false,
          font: { color: MUTED, size: 11 },
          hoverlabel: { bgcolor: BAR }, // the bars' own hover style
        },
      ];
    });
  });
}

// The plot's width before Plotly lays it out. On a phone the margins are
// fixed; on a wider chart the left margin grows to fit the longest row name.
function plotWidthEstimate(el, slots) {
  if (el.clientWidth < NARROW_CHART_PX) return el.clientWidth - NARROW_MARGIN.l - NARROW_MARGIN.r;
  const longest = Math.max(...slots.map((s) => s.label.length));
  return el.clientWidth - baseLayout("").margin.r - longest * ROW_NAME_CHAR_PX;
}

// The empty margin beside the plot that a label may run into. On a phone
// both side margins are empty; on a wider chart the left one holds the row
// names.
function spareMargins(el) {
  return el.clientWidth < NARROW_CHART_PX ? NARROW_MARGIN : { l: 0, r: baseLayout("").margin.r };
}

// The share of the plot width a label beside a line needs, after it uses
// the empty margin on the side it runs to. A label anchored by its right
// end runs left of its line.
function sideLabelShare(label, plotPx, spare) {
  const px = label.text.length * SIDE_LABEL_CHAR_PX + SIDE_LABEL_GAP_PX - (label.xanchor === "right" ? spare.l : spare.r);
  return Math.min(MAX_LABEL_SHARE, Math.max(0, px) / plotPx);
}

// The share of the axis between a label's line and the edge it runs to.
// A label anchored by its right end runs left of its line.
function roomBeside(label, [x0, x1]) {
  return (label.xanchor === "right" ? label.x - x0 : x1 - label.x) / (x1 - x0);
}

// Each request asks for at least `share` of the axis between a label's
// line and the edge the label runs to. The axis grows on that side until
// it has it. Growing one edge narrows the room beside every other line,
// so the two edges are grown in turn.
function roomForLabels(range, requests) {
  let [x0, x1] = range;
  for (let round = 0; round < ROOM_ROUNDS; round++) {
    for (const { x, xanchor, share } of requests) {
      if (xanchor === "right" && x - x0 < share * (x1 - x0)) x0 = x - (share * (x1 - x)) / (1 - share);
      if (xanchor === "left" && x1 - x < share * (x1 - x0)) x1 = x + (share * (x - x0)) / (1 - share);
    }
  }
  return [x0, x1];
}

export function renderTornadoChart(el, tornado) {
  const base = tornado.base;
  const rows = tornadoRows(tornado);
  // Top to bottom: guesses about the future, then your numbers, each
  // still widest first. Headings only when the payload says which is
  // which; an older payload gets one ungrouped list.
  const future = rows.filter((r) => r.future);
  const yours = rows.filter((r) => !r.future);
  const heading = (label) => ({ label, heading: true });
  const order =
    future.length > 0
      ? [heading(FUTURE_GROUP), ...future, ...(yours.length > 0 ? [heading(YOURS_GROUP), ...yours] : [])]
      : rows;
  // Plotly draws the first category at the bottom.
  const slots = [...order].reverse();
  const categories = slots.map((s) => s.label);

  // The axis is the verdict itself, Buy - Rent, the same quantity as the
  // fan chart above, so $0 is the tie in both. Each bar runs from your
  // verdict to the verdict under one tested value; a bar that crosses $0
  // flips the answer on its own.
  const sideTrace = (k) => {
    const cells = slots.map((s) => sideCell(s, k, base));
    return {
      type: "bar",
      orientation: "h",
      y: categories,
      base,
      x: cells.map((c) => c.x),
      marker: { color: BAR },
      text: cells.map((c) => c.text),
      textposition: "outside",
      cliponaxis: false,
      textfont: { color: MUTED, size: 11 },
      customdata: cells.map((c) => c.hover),
      hovertemplate: "%{customdata}<extra></extra>",
    };
  };
  const traces = [sideTrace(0), sideTrace(1)];

  const ends = [0, base, ...rows.flatMap((r) => r.sides.map((s) => s.end))];
  let lo = Math.min(...ends);
  let hi = Math.max(...ends);
  const span = hi - lo || 1;
  lo = Math.min(lo, -span * MIN_HALF_FRACTION);
  hi = Math.max(hi, span * MIN_HALF_FRACTION);
  const pad = (hi - lo) * END_LABEL_PAD;
  // The direction of each half, pinned to the tie line.
  const directionLabels = [
    { x: 0, xanchor: "right", xshift: -6, yref: "paper", y: 1, yanchor: "bottom", text: "← Renting ahead", showarrow: false, font: { color: RENT, size: 11 } },
    { x: 0, xanchor: "left", xshift: 6, yref: "paper", y: 1, yanchor: "bottom", text: "Buying ahead →", showarrow: false, font: { color: BUY, size: 11 } },
  ];
  // A limit label starts at your verdict, and each tested value starts at
  // its bar's end and runs outward, so each needs room of its own when it
  // starts near an edge. Making that room squeezes the other side, so each
  // direction label keeps the room it had, or what it needs if that is
  // less. When every label already fits, the axis stays as it was.
  const limitLabels = limitAnnotations(slots, base);
  const endLabels = slots.flatMap((slot) =>
    slot.heading
      ? []
      : slot.sides
          .filter((side) => !side.untested && side.tested !== null)
          .map((side) => ({ x: side.end, xanchor: side.end > base ? "left" : "right", text: endLabel(side) })),
  );
  const plotPx = plotWidthEstimate(el, slots);
  const spare = spareMargins(el);
  const start = [lo - pad, hi + pad];
  const range = roomForLabels(start, [
    ...[...limitLabels, ...endLabels].map((a) => ({ ...a, share: sideLabelShare(a, plotPx, spare) })),
    ...directionLabels.map((a) => ({ ...a, share: Math.min(sideLabelShare(a, plotPx, spare), roomBeside(a, start)) })),
  ]);

  const layout = baseLayout("Buy − Rent");
  moveCurrencyToXAxis(layout);
  layout.hovermode = "closest";
  layout.barmode = "overlay";
  layout.margin = { ...layout.margin, t: 44 };
  layout.xaxis.range = range;
  layout.xaxis.zeroline = false; // the tie line below replaces it
  layout.yaxis.categoryorder = "array";
  layout.yaxis.categoryarray = categories;
  layout.yaxis.automargin = true; // grow the left margin to fit row labels
  // Headings in the text colour, bars' names in the muted one.
  layout.yaxis.tickmode = "array";
  layout.yaxis.tickvals = categories;
  layout.yaxis.ticktext = slots.map((s) => (s.heading ? `<b style="color:${TEXT}">${s.label}</b>` : s.label));
  layout.shapes = [
    { type: "rect", layer: "below", x0: range[0], x1: 0, yref: "paper", y0: 0, y1: 1, fillcolor: tint(RENT, HALF_TINT_ALPHA), line: { width: 0 } },
    { type: "rect", layer: "below", x0: 0, x1: range[1], yref: "paper", y0: 0, y1: 1, fillcolor: tint(BUY, HALF_TINT_ALPHA), line: { width: 0 } },
    { type: "line", x0: 0, x1: 0, yref: "paper", y0: 0, y1: 1, line: { color: "#484f58", width: 1 } },
    { type: "line", name: "you-are-here", x0: base, x1: base, yref: "paper", y0: 0, y1: 1, line: { color: TEXT, width: 1.5 } },
  ];
  // Two rows above the plot: your verdict's label on top, the direction
  // of each half underneath, both pinned to the line they describe.
  layout.annotations = [
    { x: base, yref: "paper", y: 1, yanchor: "bottom", yshift: 18, text: "You are here", showarrow: false, font: { color: TEXT, size: 11 } },
    ...directionLabels,
  ];
  layout.annotations.push(...limitLabels);
  if (el.clientWidth < NARROW_CHART_PX) {
    layout.yaxis.showticklabels = false;
    layout.yaxis.automargin = false;
    layout.xaxis.automargin = true;
    layout.margin = { ...layout.margin, ...NARROW_MARGIN };
    layout.bargap = 0.5;
    // Each label's bottom edge sits on its bar's top edge: a bar fills
    // (1 - bargap) of its category slot, centred on the category. A
    // heading has no bar, so it sits centred in its slot.
    const slotPx = plotHeight(el, layout) / slots.length;
    layout.annotations.push(
      ...slots.map((s) => ({
        name: "row-label",
        xref: "paper",
        x: 0,
        xanchor: "left",
        y: s.label,
        yanchor: s.heading ? "middle" : "bottom",
        yshift: s.heading ? 0 : (slotPx * (1 - layout.bargap)) / 2,
        text: s.heading ? `<b>${s.label}</b>` : s.label,
        showarrow: false,
        font: { color: s.heading ? TEXT : MUTED, size: 11 },
      })),
    );
  }
  Plotly.react(el, traces, layout, plotConfig(el));
  showTornadoDetail(el);
}

// On touch, a tapped bar's hover label shows only briefly, so the line
// under the chart repeats it. A mouse keeps the hover alone.
function showTornadoDetail(el) {
  const detail = document.getElementById("tornado-detail");
  if (!detail) return;
  const touch = window.matchMedia("(hover: none)").matches;
  detail.hidden = !touch;
  detail.textContent = touch ? "Tap a bar to see what it tested." : "";
  // Plotly keeps its event handlers across Plotly.react, so bind once.
  if (el._tapDetailWired) return;
  el._tapDetailWired = true;
  const show = (e) => {
    const text = e?.points?.[0]?.customdata;
    if (text && !detail.hidden) detail.textContent = `${text.replace("<br>", ". ")}.`;
  };
  el.on("plotly_click", show);
  el.on("plotly_hover", show);
}

export function renderOutflowChart(el, series) {
  const x = series.year;
  const layout = baseLayout("Years");
  layout.xaxis.range = [x[0], x.at(-1)];
  layout.xaxis.hoverformat = ".1f";
  const fwd = maybeSymlog(layout, series.outflowBuy, series.outflowRent);
  layout.annotations = endLabelAnnotations(x, series.outflowBuy, series.outflowRent, fwd, plotHeight(el, layout));
  Plotly.react(el, strategyTraces(x, series.outflowBuy, series.outflowRent, fwd), layout, plotConfig(el));
}

export function renderBreakdownChart(el, payload, cfg) {
  const t = payload.totals;
  const items = [
    ["Mortgage interest", t.interestPaid],
    ["Property levy", t.propertyTaxPaid],
    ["Maintenance", t.maintenancePaid],
    ["Insurance", t.insurancePaid],
    // Zero at 20% down or more; a response from before the field had none.
    ["Mortgage insurance", t.mortgageInsurancePaid ?? 0],
    ["Buyer closing", t.closingCostsBuyer],
    ["Seller closing", t.closingCostsSeller],
  ].sort((a, b) => b[1] - a[1]);
  const labels = [...items.map((i) => i[0]), "Tax savings (offset)"];
  const values = [...items.map((i) => i[1]), -t.taxSavings];
  // Reverse once into locals so the negative "Tax savings" bar keeps its
  // green highlight (in-place .reverse() would desync colors from bars).
  const revLabels = [...labels].reverse();
  const revValues = [...values].reverse();
  const traces = [
    {
      type: "bar", orientation: "h",
      y: revLabels, x: revValues,
      marker: { color: revValues.map((v) => (v < 0 ? "#7ee787" : MUTED)) },
      customdata: moneyHover(revValues),
      hovertemplate: `%{y}: %{customdata}<extra></extra>`,
    },
  ];
  const layout = baseLayout(`Total over ${cfg.horizonYears} years`);
  moveCurrencyToXAxis(layout);
  layout.yaxis.automargin = true; // grow the left margin to fit category labels
  Plotly.react(el, traces, layout, plotConfig(el));
}
