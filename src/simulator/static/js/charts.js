// Plotly.js builders — one shared GitHub-dark theme. Buy #f0883e,
// Rent #58a6ff; bands/neutrals muted; direct line labels, no legends.

import { getCurrencySymbol } from "./format.js";

const BUY = "#f0883e";
const RENT = "#58a6ff";
const MUTED = "#8b949e";
const GRID = "rgba(48,54,61,0.6)";

const PLOT_CONFIG = { displayModeBar: false, responsive: true };

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
      tickprefix: getCurrencySymbol(),
      tickformat: "~s",
    },
  };
}

// Horizontal-bar charts put money on X and categories on Y, so the base
// layout's money formatting has to MOVE axes, not just come off Y.
// Deleting it alone left the money axis with no currency and no SI
// compaction at all -- the tornado read "-0.5M" where every other chart
// reads "-EUR500k".
//
// It cannot simply be set on both: Plotly ignores a tickformat on a
// category axis but honours a tickprefix, so a prefix left on Y labels
// every category "<symbol>Rent Inflation".
function moveCurrencyToXAxis(layout) {
  layout.xaxis.tickprefix = layout.yaxis.tickprefix;
  layout.xaxis.tickformat = layout.yaxis.tickformat;
  delete layout.yaxis.tickprefix;
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
function fmtTick(v) {
  const sign = v < 0 ? "-" : "";
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

export function renderTornadoChart(el, tornado) {
  const params = [...tornado.params].reverse();
  const base = tornado.base;
  const low = [...tornado.low].reverse().map((v) => v - base);
  const high = [...tornado.high].reverse().map((v) => v - base);
  const traces = [
    { type: "bar", orientation: "h", y: params, x: low, base, marker: { color: MUTED }, hovertemplate: `%{y} lower: ${getCurrencySymbol()}%{x:,.0f}<extra></extra>` },
    { type: "bar", orientation: "h", y: params, x: high, base, marker: { color: RENT }, hovertemplate: `%{y} higher: ${getCurrencySymbol()}%{x:,.0f}<extra></extra>` },
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
    ["Property tax", t.propertyTaxPaid],
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