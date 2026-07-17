// Plotly.js builders — one shared GitHub-dark theme. Buy #f0883e,
// Rent #58a6ff; bands/neutrals muted; direct line labels, no legends.

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
    yaxis: { gridcolor: GRID, zerolinecolor: "#30363d", tickformat: "$~s" },
  };
}

function strategyTraces(x, buyY, rentY) {
  return [
    { x, y: buyY, mode: "lines", line: { color: BUY, width: 2 }, name: "Buy", hovertemplate: "Buy %{y:$,.0f}<extra></extra>" },
    { x, y: rentY, mode: "lines", line: { color: RENT, width: 2 }, name: "Rent", hovertemplate: "Rent %{y:$,.0f}<extra></extra>" },
  ];
}

function endLabelAnnotations(x, buyY, rentY) {
  return [
    { x: x.at(-1), y: buyY.at(-1), text: "Buy", font: { color: BUY, size: 12 }, showarrow: false, xanchor: "left", xshift: 6 },
    { x: x.at(-1), y: rentY.at(-1), text: "Rent", font: { color: RENT, size: 12 }, showarrow: false, xanchor: "left", xshift: 6 },
  ];
}

export function renderDecisionChart(el, series, breakevenYear) {
  const x = series.year;
  const layout = baseLayout("Years");
  layout.annotations = endLabelAnnotations(x, series.netBuy, series.netRent);
  if (breakevenYear != null) {
    layout.shapes = [
      { type: "line", x0: breakevenYear, x1: breakevenYear, yref: "paper", y0: 0, y1: 1, line: { color: "#484f58", width: 1, dash: "dash" } },
    ];
    layout.annotations.push({
      x: breakevenYear, yref: "paper", y: 1, yanchor: "bottom", xanchor: "left", xshift: 4,
      text: `breakeven ${breakevenYear.toFixed(1)}y`, font: { color: MUTED, size: 11 }, showarrow: false,
    });
  }
  Plotly.react(el, strategyTraces(x, series.netBuy, series.netRent), layout, PLOT_CONFIG);
}

export function renderFanChart(el, mc) {
  const x = mc.yearAxis;
  const row = Object.fromEntries(mc.percentileLevels.map((level, i) => [level, mc.differencePercentiles[i]]));
  const traces = [
    { x, y: row[95], mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
    { x, y: row[5], mode: "lines", line: { width: 0 }, fill: "tonexty", fillcolor: "rgba(139,148,158,0.14)", hoverinfo: "skip", showlegend: false },
    { x, y: row[75], mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
    { x, y: row[25], mode: "lines", line: { width: 0 }, fill: "tonexty", fillcolor: "rgba(139,148,158,0.24)", hoverinfo: "skip", showlegend: false },
    { x, y: row[50], mode: "lines", line: { color: "#e6edf3", width: 1.5 }, name: "Median", hovertemplate: "Median %{y:$,.0f}<extra></extra>", showlegend: false },
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
    { type: "bar", orientation: "h", y: params, x: low, base, marker: { color: MUTED }, hovertemplate: "%{y} lower: %{x:$,.0f}<extra></extra>" },
    { type: "bar", orientation: "h", y: params, x: high, base, marker: { color: RENT }, hovertemplate: "%{y} higher: %{x:$,.0f}<extra></extra>" },
  ];
  const layout = baseLayout("Impact on Buy − Rent difference");
  layout.barmode = "overlay";
  layout.shapes = [
    { type: "line", x0: base, x1: base, yref: "paper", y0: 0, y1: 1, line: { color: "#e6edf3", width: 1 } },
  ];
  Plotly.react(el, traces, layout, PLOT_CONFIG);
}

export function renderOutflowChart(el, series) {
  const x = series.year;
  const layout = baseLayout("Years");
  layout.annotations = endLabelAnnotations(x, series.outflowBuy, series.outflowRent);
  Plotly.react(el, strategyTraces(x, series.outflowBuy, series.outflowRent), layout, PLOT_CONFIG);
}

export function renderBreakdownChart(el, payload, cfg) {
  const nMonths = Math.min(cfg.horizonYears, cfg.mortgageTermYears) * 12;
  const loan = cfg.propertyPrice * (1 - cfg.downPaymentPct / 100);
  const finalBalance = payload.series.mortgageBalance.at(-1);
  const interestPaid = payload.monthlyMortgagePayment * nMonths - (loan - finalBalance);
  const t = payload.totals;
  const items = [
    ["Mortgage interest", interestPaid],
    ["Property tax", t.propertyTaxPaid],
    ["Maintenance", t.maintenancePaid],
    ["Insurance", t.insurancePaid],
    ["Buyer closing", t.closingCostsBuyer],
    ["Seller closing", t.closingCostsSeller],
  ].sort((a, b) => b[1] - a[1]);
  const labels = [...items.map((i) => i[0]), "Tax savings (offset)"];
  const values = [...items.map((i) => i[1]), -t.taxSavings];
  const traces = [
    {
      type: "bar", orientation: "h",
      y: labels.reverse(), x: values.reverse(),
      marker: { color: values.map((v) => (v < 0 ? "#7ee787" : MUTED)).reverse() },
      hovertemplate: "%{y}: %{x:$,.0f}<extra></extra>",
    },
  ];
  const layout = baseLayout(`Total over ${cfg.horizonYears} years`);
  Plotly.react(el, traces, layout, PLOT_CONFIG);
}