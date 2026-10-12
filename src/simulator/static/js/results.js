// Verdict hero, stat cards, numbers table, CSV export. The verdict,
// breakeven, and confidence all read from the same API payloads —
// never computed client-side (CONTEXT.md: "Verdict").

import {
  renderBreakdownChart,
  renderDecisionChart,
  renderFanChart,
  renderOutflowChart,
  renderTornadoChart,
  tornadoSummary,
} from "./charts.js";
import { trackEvent } from "./analytics.js";
import { fmtMoney, getCurrencySymbol } from "./format.js";
import { configHash, debounce, getConfig, getFtb, getRegionId } from "./state.js";

// A winner that wins in 40-60% of simulated futures (the confidence, as
// displayed) is a toss-up, so the headline stops naming it (ADR-0010).
const TOSS_UP_MIN_PCT = 40;
const TOSS_UP_MAX_PCT = 60;

// The last simulate verdict, and whether the last Monte Carlo run called
// it a toss-up. The flag carries over to the next simulate result only
// while a slider is dragged, so a drag inside a toss-up does not flash the
// winner headline on every step. Any other change drops it (forgetTossUp),
// as does a failed Monte Carlo run for the verdict on screen (clearTossUp);
// the next Monte Carlo result sets it again.
let lastVerdict = null;
let tossUp = false;
// The config the verdict on screen was computed for. Until the next
// simulate result lands (or when it fails), it differs from the live config.
let verdictHash = null;
// The payloads on screen, so the charts can be drawn again at a new size.
// The tornado's is `tornado`, below. `lastSim` also keeps the scenario the
// result was computed for (config, region, currency, relief setting), so
// the CSV and the printout describe the numbers on screen even when a
// later change failed to update them.
let lastSim = null;
let lastFan = null;

// The tornado's layout depends on its width: the phone layout below
// NARROW_CHART_PX, its margins, and the axis room that keeps its labels
// inside the chart (charts.js). A width change after it is drawn (a
// resized window, a turned phone) draws it again from the payload on
// screen (#57).
let tornado = null; // the payload on screen
let tornadoHash = null; // the config it was computed for
let tornadoWidth = null; // the width it was laid out for; null until drawn
let watchingTornado = false;
const TORNADO_RESIZE_MS = 100;

// Until the next Monte Carlo result lands, the payload on screen can belong
// to an older config. Drawing it again then would show its numbers in the
// new region's currency; the pending result draws at the new width anyway.
const tornadoIsCurrent = () => tornadoHash === configHash(getConfig());

function drawTornado() {
  const el = document.getElementById("tornado-chart");
  // A hidden chart has no width to lay out for; it is drawn once it shows.
  if (el.clientWidth === 0) {
    tornadoWidth = null;
    return;
  }
  tornadoWidth = el.clientWidth;
  renderTornadoChart(el, tornado);
}

// Any whole-pixel change counts. Drawing never changes the chart's width
// (the card sets it; the height is fixed), so a draw cannot set off another.
const redrawTornado = debounce(() => {
  const el = document.getElementById("tornado-chart");
  if (!tornado || el.clientWidth === 0 || el.clientWidth === tornadoWidth) return;
  if (!tornadoIsCurrent()) return;
  tornadoWidth = el.clientWidth;
  // A redraw keeps the width Plotly drew at, and Plotly fits it to the
  // chart only on a window resize, which a chart shown again after being
  // hidden never gets. So fit the width first, then draw: the chart's own
  // layout is the last draw.
  Plotly.Plots.resize(el).then(() => {
    if (tornadoIsCurrent()) drawTornado();
  });
}, TORNADO_RESIZE_MS);

function watchTornadoWidth() {
  if (watchingTornado || typeof ResizeObserver === "undefined") return;
  watchingTornado = true;
  new ResizeObserver(redrawTornado).observe(document.getElementById("tornado-chart"));
}

function headlineHtml({ winner, difference, horizonYears }) {
  // A tie names no winner and no amount: the gap is under half a unit of
  // currency and would print as "~$0" (ADR-0010 amendment).
  if (winner === "tie") return `Buying and renting leave you equally well off after ${horizonYears} years`;
  const amount = `~${fmtMoney(Math.abs(difference))}`;
  if (tossUp) {
    // No Buy/Rent colour on the amount: either colour would imply a winner.
    return `Too close to call: buying and renting end within ${amount} of each other after ${horizonYears} years`;
  }
  const name = winner === "buy" ? "Buying" : "Renting";
  return `${name} leaves you <span class="amount-${winner}">${amount}</span> wealthier if you sell after ${horizonYears} years`;
}

// The one-line verdict pinned at the top of the phone inputs sheet, so the
// answer stays in view while the sheet covers the page. Same tie and
// toss-up rules as the headline.
function paintSheetVerdict() {
  if (!lastVerdict) return;
  const { winner, difference, horizonYears } = lastVerdict;
  const amount = `~${fmtMoney(Math.abs(difference))}`;
  let text;
  if (winner === "tie") text = `Buying and renting end level after ${horizonYears} yrs`;
  else if (tossUp) text = `Too close to call · ${amount} apart after ${horizonYears} yrs`;
  else text = `${winner === "buy" ? "Buying" : "Renting"} ahead by ${amount} after ${horizonYears} yrs`;
  // The line is a live region: rewriting the same text would announce it again.
  const line = document.getElementById("sheet-verdict");
  if (line.textContent !== text) line.textContent = text;
}

// The headline is a live region: rewriting the same text would announce it again.
function paintHeadline() {
  const line = document.getElementById("verdict-line");
  const html = headlineHtml(lastVerdict);
  if (line.innerHTML !== html) line.innerHTML = html;
}

function renderVerdict(data) {
  lastVerdict = data.verdict;
  const { winner, horizonYears } = data.verdict;
  const name = winner === "buy" ? "Buying" : "Renting";
  paintHeadline();

  const breakevenEl = document.getElementById("verdict-breakeven");
  const b = data.breakevenYear;
  // A tie ignores the breakeven: a gap that ends at the tie can still
  // cross zero in the last month, which would name a winner.
  if (winner === "tie") breakevenEl.textContent = `Neither pulls ahead within ${horizonYears} years`;
  else if (b != null) {
    const n = Math.ceil(b);
    breakevenEl.textContent = `${name} pulls ahead if you stay ≥ ${n} ${n === 1 ? "year" : "years"}`;
  }
  else breakevenEl.textContent = `No breakeven within ${horizonYears} years`;
  document.getElementById("verdict-confidence").textContent = "";
  paintSheetVerdict();
}

function renderStats(data) {
  const netBuy = data.series.netBuy.at(-1);
  const netRent = data.series.netRent.at(-1);
  document.getElementById("stat-buy").textContent = fmtMoney(netBuy);
  document.getElementById("stat-rent").textContent = fmtMoney(netRent);
  document.getElementById("stat-cost-buy").textContent = `${fmtMoney(data.monthlyCostBuyYear1)}/mo`;
  document.getElementById("stat-cost-rent").textContent = `${fmtMoney(data.monthlyCostRentYear1)}/mo`;
  // Net Value subtracts everything paid in, rent included, so both sides
  // are often negative -- which reads as "I lose money either way" unless
  // something says why.
  document.getElementById("net-note").hidden = netBuy >= 0 && netRent >= 0;
}

// One list for the on-screen table and the CSV. `csv` takes the currency code.
const NUMBER_COLUMNS = [
  { label: "Home value", csv: (c) => `Home value (${c})`, key: "homeValue" },
  { label: "Portfolio (rent)", csv: (c) => `Portfolio rent side (${c})`, key: "equityValue" },
  { label: "Portfolio (buy)", csv: (c) => `Portfolio buy side (${c})`, key: "buyPortfolioValue" },
  { label: "Mortgage balance", csv: (c) => `Mortgage balance (${c})`, key: "mortgageBalance" },
  { label: "Out of pocket (buy)", csv: (c) => `Out of pocket buy side (${c})`, key: "outflowBuy" },
  { label: "Out of pocket (rent)", csv: (c) => `Out of pocket rent side (${c})`, key: "outflowRent" },
  { label: "Everything put in", csv: (c) => `Everything put in (${c})`, key: "cashCommitted" },
  { label: "Net (buy)", csv: (c) => `Net value buy side (${c})`, key: "netBuy" },
  { label: "Net (rent)", csv: (c) => `Net value rent side (${c})`, key: "netRent" },
];

// CSV headers name the currency as an ASCII code, which every spreadsheet
// reads. By region, because two regions can share a symbol.
const REGION_CURRENCY = { us: "USD", fr: "EUR", de: "EUR", nl: "EUR", uk: "GBP" };

function renderTable(series) {
  // Yearly rows for readability; CSV export (below) keeps every month.
  const yearly = series.year.map((_, i) => i).filter((i) => i % 12 === 0);
  const rows = yearly
    .map((i, n) => {
      // The last row is the year you sell, the one the verdict reads.
      const horizon = n === yearly.length - 1 ? ' class="horizon-row"' : "";
      const cells = NUMBER_COLUMNS.map(({ key }) => `<td>${fmtMoney(series[key][i])}</td>`).join("");
      return `<tr${horizon}><td>${series.year[i].toFixed(0)}</td>${cells}</tr>`;
    })
    .join("");
  const head = ["Year", ...NUMBER_COLUMNS.map((c) => c.label)].map((label) => `<th>${label}</th>`).join("");
  document.getElementById("data-table").innerHTML =
    `<table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`;
}

// Takes the scenario the table on screen was computed for, so the
// headers and the file name always match the rows in the file.
export function downloadCsv({ data, cfg, regionId, symbol }) {
  const { series } = data;
  // A link that matches no region keeps its symbol.
  const code = REGION_CURRENCY[regionId] ?? symbol;
  const lines = [
    ["Month", "Year", ...NUMBER_COLUMNS.map((c) => c.csv(code))].join(","),
    ...series.year.map((year, i) =>
      [Math.round(year * 12), year.toFixed(4), ...NUMBER_COLUMNS.map(({ key }) => series[key][i].toFixed(2))].join(","),
    ),
  ];
  // The byte-order mark makes Excel read the file as UTF-8.
  const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const name = `rent-or-buy-${regionId ?? "custom"}-${cfg.horizonYears}-years-${cfg.propertyPrice}.csv`;
  const link = Object.assign(document.createElement("a"), { href: url, download: name });
  link.click();
  URL.revokeObjectURL(url);
}

export function renderSimulate(data, cfg) {
  verdictHash = configHash(cfg);
  lastSim = { data, cfg, regionId: getRegionId(), symbol: getCurrencySymbol(), ftb: getFtb() };
  const shown = lastSim;
  renderVerdict(data);
  renderStats(data);
  renderDecisionChart(document.getElementById("decision-chart"), data.series, data.breakevenYear);
  renderOutflowChart(document.getElementById("outflow-chart"), data.series);
  renderBreakdownChart(document.getElementById("breakdown-chart"), data, cfg);
  renderTable(data.series);
  document.getElementById("csv-btn").onclick = (e) => {
    downloadCsv(shown);
    if (e.isTrusted) trackEvent("csv-downloaded");
  };
}

// Whether the verdict on screen belongs to the live config, so Share
// never pairs a link with the verdict of a different scenario.
export function verdictIsCurrent() {
  return verdictHash === configHash(getConfig());
}

// The sentence above the tornado reads the same toss-up flag as the
// headline. Whenever that flag is dropped, the sentence goes too, rather
// than keep calling a toss-up beside a headline that names a winner. The
// next Monte Carlo result writes it again.
function clearTornadoSummary() {
  document.getElementById("tornado-summary").textContent = "";
}

// A change that is not a slider drag (a region, a pill, a typed value) can
// land far from the config the last Monte Carlo run judged, so the next
// simulate result must name its winner until its own run says otherwise.
// Nothing is repainted here: the headline on screen still belongs to the
// judged config, and the next simulate result repaints it.
export function forgetTossUp() {
  tossUp = false;
  clearTornadoSummary();
}

// A failed Monte Carlo run leaves nothing to call the verdict a toss-up,
// so the carried-over flag must not keep the headline from naming the winner.
export function clearTossUp() {
  tossUp = false;
  clearTornadoSummary();
  if (lastVerdict) paintHeadline();
  paintSheetVerdict();
}

export function renderMonteCarlo(mc, winner) {
  lastFan = mc;
  // A tie has no winner whose share to show, so it shows buying's.
  const pct = winner === "rent" ? 100 - mc.buyWinsPct : mc.buyWinsPct;
  const name = winner === "rent" ? "Renting" : "Buying";
  // Decide on the rounded share, so the headline agrees with the number
  // printed beside it (60.4% prints as 60% and is a toss-up).
  const shownPct = Math.round(pct);
  tossUp = shownPct >= TOSS_UP_MIN_PCT && shownPct <= TOSS_UP_MAX_PCT;
  if (lastVerdict) paintHeadline();
  paintSheetVerdict();
  // A live region too, written only when its text changes.
  const confidence = document.getElementById("verdict-confidence");
  const confidenceText = ` · ${name} wins in ${shownPct}% of simulated futures`;
  if (confidence.textContent !== confidenceText) confidence.textContent = confidenceText;
  renderFanChart(document.getElementById("fan-chart"), mc);
  document.getElementById("tornado-summary").textContent = tornadoSummary(mc.tornado, tossUp);
  tornado = mc.tornado;
  // main.js renders a Monte Carlo result only for the config of the
  // verdict on screen.
  tornadoHash = verdictHash;
  drawTornado();
  watchTornadoWidth();
}

// Redraw every chart from the payloads on screen, at the charts' current
// size; print.js uses it to lay them out at paper width and back.
export function redrawCharts() {
  if (lastSim) {
    const { data, cfg } = lastSim;
    renderDecisionChart(document.getElementById("decision-chart"), data.series, data.breakevenYear);
    renderOutflowChart(document.getElementById("outflow-chart"), data.series);
    renderBreakdownChart(document.getElementById("breakdown-chart"), data, cfg);
  }
  if (lastFan) renderFanChart(document.getElementById("fan-chart"), lastFan);
  if (tornado) drawTornado();
}
