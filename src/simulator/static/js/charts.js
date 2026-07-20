// Plotly.js builders — one shared GitHub-dark theme. Buy #f0883e,
// Rent #58a6ff; bands/neutrals muted; direct line labels, no legends.

import { INPUT_DEFS } from "./fields.js";
import { getCurrencySymbol } from "./format.js";

const BUY = "#f0883e";
const RENT = "#58a6ff";
const MUTED = "#8b949e";
const GRID = "rgba(48,54,61,0.6)";

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
    format: { currency: [getCurrencySymbol(), ""] },
  });
  return "$~s";
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
      ? { ...base, y: yRaw.map(fwd), customdata: yRaw, hovertemplate: `${name} ${getCurrencySymbol()}%{customdata:,.0f}<extra></extra>` }
      : { ...base, y: yRaw, hovertemplate: `${name} ${getCurrencySymbol()}%{y:,.0f}<extra></extra>` };
  };
  return [mk(buyY, BUY, "Buy"), mk(rentY, RENT, "Rent")];
}

function endLabelAnnotations(x, buyY, rentY, fwd) {
  const y = (v) => (fwd ? fwd(v) : v);
  return [
    { x: x.at(-1), y: y(buyY.at(-1)), text: "Buy", font: { color: BUY, size: 12 }, showarrow: false, xanchor: "left", xshift: 6 },
    { x: x.at(-1), y: y(rentY.at(-1)), text: "Rent", font: { color: RENT, size: 12 }, showarrow: false, xanchor: "left", xshift: 6 },
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
// The sign is U+2212 MINUS, not an ASCII hyphen, because these labels
// share a page with linear axes that Plotly formats itself -- and Plotly
// emits U+2212. A hyphen here renders visibly shorter and higher than
// the minus one chart across.
const MINUS = "−";
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

export function renderDecisionChart(el, series, breakevenYear) {
  const x = series.year;
  const layout = baseLayout("Years");
  const fwd = maybeSymlog(layout, series.netBuy, series.netRent);
  layout.annotations = endLabelAnnotations(x, series.netBuy, series.netRent, fwd);
  if (breakevenYear != null) {
    layout.shapes = [
      { type: "line", x0: breakevenYear, x1: breakevenYear, yref: "paper", y0: 0, y1: 1, line: { color: "#484f58", width: 1, dash: "dash" } },
    ];
    layout.annotations.push({
      x: breakevenYear, yref: "paper", y: 1, yanchor: "bottom", xanchor: "left", xshift: 4,
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
    { x, y: row[50], mode: "lines", line: { color: "#e6edf3", width: 1.5 }, name: "Median", hovertemplate: `Median ${getCurrencySymbol()}%{y:,.0f}<extra></extra>`, showlegend: false },
  ];
  const layout = baseLayout("Years");
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

export function renderTornadoChart(el, tornado) {
  const params = [...tornado.params].reverse();
  const base = tornado.base;
  const low = [...tornado.low].reverse().map((v) => v - base);
  const high = [...tornado.high].reverse().map((v) => v - base);
  // A bar's width says how much the outcome moves but never what was
  // changed, and the width of the three stochastic bars additionally
  // varies with the horizon (the delta is a standard error). Both are
  // invisible without stating the assumption's own before/after.
  const fields = [...tornado.fields].reverse();
  const baseIn = [...tornado.baseInput].reverse();
  const lowIn = [...tornado.lowInput].reverse();
  const highIn = [...tornado.highInput].reverse();
  const rangeTo = (values) =>
    fields.map((f, i) => `${fmtFieldValue(f, baseIn[i])} → ${fmtFieldValue(f, values[i])}`);
  const cur = getCurrencySymbol();
  const traces = [
    { type: "bar", orientation: "h", y: params, x: low, base, marker: { color: MUTED }, customdata: rangeTo(lowIn), hovertemplate: `%{y} lower<br>%{customdata}<br>${cur}%{x:,.0f}<extra></extra>` },
    { type: "bar", orientation: "h", y: params, x: high, base, marker: { color: RENT }, customdata: rangeTo(highIn), hovertemplate: `%{y} higher<br>%{customdata}<br>${cur}%{x:,.0f}<extra></extra>` },
  ];
  const layout = baseLayout("Impact on Buy − Rent difference");
  moveCurrencyToXAxis(layout);
  layout.barmode = "overlay";
  layout.yaxis.automargin = true; // grow the left margin to fit parameter labels
  layout.shapes = [
    { type: "line", x0: base, x1: base, yref: "paper", y0: 0, y1: 1, line: { color: "#e6edf3", width: 1 } },
  ];
  Plotly.react(el, traces, layout, PLOT_CONFIG);
}

export function renderOutflowChart(el, series) {
  const x = series.year;
  const layout = baseLayout("Years");
  const fwd = maybeSymlog(layout, series.outflowBuy, series.outflowRent);
  layout.annotations = endLabelAnnotations(x, series.outflowBuy, series.outflowRent, fwd);
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
      hovertemplate: `%{y}: ${getCurrencySymbol()}%{x:,.0f}<extra></extra>`,
    },
  ];
  const layout = baseLayout(`Total over ${cfg.horizonYears} years`);
  moveCurrencyToXAxis(layout);
  layout.yaxis.automargin = true; // grow the left margin to fit category labels
  Plotly.react(el, traces, layout, PLOT_CONFIG);
}