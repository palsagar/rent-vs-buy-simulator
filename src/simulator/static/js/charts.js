// Plotly.js builders — one shared GitHub-dark theme. Buy #f0883e,
// Rent #58a6ff; bands/neutrals muted; direct line labels, no legends.

import { INPUT_DEFS } from "./fields.js";
import { MINUS, fmtMoney, getCurrencySymbol } from "./format.js";

const BUY = "#f0883e";
const RENT = "#58a6ff";
const MUTED = "#8b949e";
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

const PLOT_CONFIG = { displayModeBar: false, responsive: true, locale: CURRENCY_LOCALE };

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
  Plotly.react(el, strategyTraces(x, series.netBuy, series.netRent, fwd), layout, PLOT_CONFIG);
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
  Plotly.react(el, traces, layout, PLOT_CONFIG);
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
// response. Degrade to unnamed, ungrouped bars instead of stranding the
// chart.
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
// clamped at a slider limit and tested nothing.
const SAME_INPUT_TOLERANCE = 1e-9;

// One row per bar, widest first as the payload sends them. Each side
// carries the Buy - Rent result it produced and, when the payload has
// them, the tested and current values formatted like their slider.
function tornadoRows(tornado) {
  const ranges = tornadoRanges(tornado, tornado.params.length);
  return tornado.params.map((name, i) => {
    if (ranges === null) {
      return {
        label: name,
        future: false,
        current: null,
        sides: [
          { end: tornado.low[i], tested: null, direction: "lower" },
          { end: tornado.high[i], tested: null, direction: "higher" },
        ],
      };
    }
    const [fields, baseIn, lowIn, highIn] = ranges;
    const def = INPUT_DEFS.find((d) => d.key === fields[i]);
    const tested = (v) =>
      Math.abs(v - baseIn[i]) < SAME_INPUT_TOLERANCE ? null : fmtFieldValue(fields[i], v);
    return {
      label: def?.label ?? name,
      future: def?.section === "assumptions",
      current: fmtFieldValue(fields[i], baseIn[i]),
      sides: [
        { end: tornado.low[i], tested: tested(lowIn[i]), direction: "lower" },
        { end: tornado.high[i], tested: tested(highIn[i]), direction: "higher" },
      ],
    };
  });
}

function aheadBy(diff) {
  return diff >= 0 ? `Buying ahead by ${fmtMoney(diff)}` : `Renting ahead by ${fmtMoney(-diff)}`;
}

function lowerFirst(text) {
  return text.charAt(0).toLowerCase() + text.slice(1);
}

// "equity growth (CAGR) at 11.7% instead of 7.0%", or "higher equity
// growth" when the payload predates the tested values.
function testedPhrase(row, side) {
  return side.tested === null
    ? `${side.direction} ${lowerFirst(row.label)}`
    : `${lowerFirst(row.label)} at ${side.tested} instead of ${row.current}`;
}

const COUNT_WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"];

// Bars named in the summary when more than this many flip the answer.
const MAX_NAMED_FLIPS = 3;

// The sentence above the tornado: which single changes would flip the
// answer. A side flips it when its Buy - Rent result lands on the other
// side of the tie from yours. A toss-up gets its own line, decided by
// the same rule as the headline, so the two never disagree.
export function tornadoSummary(tornado, tossUp) {
  if (tossUp) return "Your result is too close to call, so small changes can tip it either way.";
  const buyAhead = tornado.base >= 0;
  const flips = tornadoRows(tornado).flatMap((row) => {
    const side = row.sides.find((s) => s.end >= 0 !== buyAhead);
    return side === undefined ? [] : [testedPhrase(row, side)];
  });
  if (flips.length === 0) {
    return `No single change here flips the answer. ${buyAhead ? "Buying" : "Renting"} stays ahead in every test.`;
  }
  const count = COUNT_WORDS[flips.length] ?? String(flips.length);
  const lead = `${count} of these could flip the answer to ${buyAhead ? "renting" : "buying"} on ${flips.length === 1 ? "its" : "their"} own`;
  if (flips.length > MAX_NAMED_FLIPS) {
    const [a, b, c] = flips;
    return `${lead}. The biggest are ${a}, ${b}, and ${c}.`;
  }
  const list = flips.length === 1 ? flips[0] : `${flips.slice(0, -1).join(", ")}, or ${flips.at(-1)}`;
  return `${lead}: ${list}.`;
}

// An empty side of the axis is extended by this fraction of the data
// span, which keeps the tie line at least a quarter of the way in from
// either edge. Each tinted half then has room for its label even when
// every bar lies on one side.
const MIN_HALF_FRACTION = 1 / 3;

// Room past the outermost bar ends for the tested values printed there.
const END_LABEL_PAD = 0.14;

export function renderTornadoChart(el, tornado) {
  const base = tornado.base;
  const rows = tornadoRows(tornado);
  // Top to bottom: guesses about the future, then your numbers, each
  // still widest first. Headings only when the payload says which is
  // which; an older payload gets one ungrouped list.
  const future = rows.filter((r) => r.future);
  const yours = rows.filter((r) => !r.future);
  const grouped = future.length > 0;
  const order = grouped
    ? [FUTURE_GROUP, ...future, ...(yours.length > 0 ? [YOURS_GROUP, ...yours] : [])]
    : rows;
  // Plotly draws the first category at the bottom.
  const slots = [...order].reverse();
  const category = (slot) => (typeof slot === "string" ? slot : slot.label);
  const categories = slots.map(category);

  // The axis is the Buy - Rent result itself, the same quantity as the fan
  // chart above, so $0 is the tie in both. Each bar runs from your result
  // to the result of one tested value; a bar that crosses $0 flips the
  // answer on its own.
  const sideTrace = (k) => ({
    type: "bar",
    orientation: "h",
    y: categories,
    base,
    x: slots.map((s) => (typeof s === "string" ? null : s.sides[k].end - base)),
    marker: { color: BAR },
    text: slots.map((s) => (typeof s === "string" ? "" : (s.sides[k].tested ?? ""))),
    textposition: "outside",
    cliponaxis: false,
    textfont: { color: MUTED, size: 11 },
    customdata: slots.map((s) => {
      if (typeof s === "string") return "";
      const side = s.sides[k];
      const what = side.tested === null ? `${s.label}, ${side.direction}` : `${s.label} at ${side.tested} instead of ${s.current}`;
      return `${what}<br>${aheadBy(side.end)}`;
    }),
    hovertemplate: "%{customdata}<extra></extra>",
  });
  const traces = [sideTrace(0), sideTrace(1)];

  const ends = [0, base, ...rows.flatMap((r) => r.sides.map((s) => s.end))];
  let lo = Math.min(...ends);
  let hi = Math.max(...ends);
  const span = hi - lo || 1;
  lo = Math.min(lo, -span * MIN_HALF_FRACTION);
  hi = Math.max(hi, span * MIN_HALF_FRACTION);
  const pad = (hi - lo) * END_LABEL_PAD;
  const range = [lo - pad, hi + pad];

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
  layout.yaxis.ticktext = slots.map((s) => (typeof s === "string" ? `<b style="color:#e6edf3">${s}</b>` : s.label));
  layout.shapes = [
    { type: "rect", layer: "below", x0: range[0], x1: 0, yref: "paper", y0: 0, y1: 1, fillcolor: "rgba(88,166,255,0.1)", line: { width: 0 } },
    { type: "rect", layer: "below", x0: 0, x1: range[1], yref: "paper", y0: 0, y1: 1, fillcolor: "rgba(240,136,62,0.1)", line: { width: 0 } },
    { type: "line", name: "tie", x0: 0, x1: 0, yref: "paper", y0: 0, y1: 1, line: { color: "#484f58", width: 1 } },
    { type: "line", name: "your-result", x0: base, x1: base, yref: "paper", y0: 0, y1: 1, line: { color: "#e6edf3", width: 1.5 } },
  ];
  // Two rows above the plot: your result's label on top, the direction of
  // each half underneath, both pinned to the line they describe.
  layout.annotations = [
    { x: base, yref: "paper", y: 1, yanchor: "bottom", yshift: 18, text: "Your result", showarrow: false, font: { color: "#e6edf3", size: 11 } },
    { x: 0, xanchor: "right", xshift: -6, yref: "paper", y: 1, yanchor: "bottom", text: "← Renting ahead", showarrow: false, font: { color: RENT, size: 11 } },
    { x: 0, xanchor: "left", xshift: 6, yref: "paper", y: 1, yanchor: "bottom", text: "Buying ahead →", showarrow: false, font: { color: BUY, size: 11 } },
  ];
  if (el.clientWidth < NARROW_CHART_PX) {
    layout.yaxis.showticklabels = false;
    layout.yaxis.automargin = false;
    layout.xaxis.automargin = true;
    layout.margin = { ...layout.margin, l: 16, r: 24 };
    layout.bargap = 0.5;
    // Each label's bottom edge sits on its bar's top edge: a bar fills
    // (1 - bargap) of its category slot, centred on the category. A
    // heading has no bar, so it sits centred in its slot.
    const slotPx = plotHeight(el, layout) / slots.length;
    layout.annotations.push(
      ...slots.map((s) => {
        const heading = typeof s === "string";
        return {
          name: "row-label",
          xref: "paper",
          x: 0,
          xanchor: "left",
          y: category(s),
          yanchor: heading ? "middle" : "bottom",
          yshift: heading ? 0 : (slotPx * (1 - layout.bargap)) / 2,
          text: heading ? `<b>${s}</b>` : s.label,
          showarrow: false,
          font: { color: heading ? "#e6edf3" : MUTED, size: 11 },
        };
      }),
    );
  }
  Plotly.react(el, traces, layout, PLOT_CONFIG);
}

export function renderOutflowChart(el, series) {
  const x = series.year;
  const layout = baseLayout("Years");
  layout.xaxis.range = [x[0], x.at(-1)];
  layout.xaxis.hoverformat = ".1f";
  const fwd = maybeSymlog(layout, series.outflowBuy, series.outflowRent);
  layout.annotations = endLabelAnnotations(x, series.outflowBuy, series.outflowRent, fwd, plotHeight(el, layout));
  Plotly.react(el, strategyTraces(x, series.outflowBuy, series.outflowRent, fwd), layout, PLOT_CONFIG);
}

export function renderBreakdownChart(el, payload, cfg) {
  const t = payload.totals;
  const items = [
    ["Mortgage interest", t.interestPaid],
    ["Property levy", t.propertyTaxPaid],
    ["Maintenance", t.maintenancePaid],
    ["Insurance", t.insurancePaid],
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
  Plotly.react(el, traces, layout, PLOT_CONFIG);
}