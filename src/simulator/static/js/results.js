// Verdict hero, stat cards, numbers table, CSV export. The verdict,
// breakeven, and confidence all read from the same API payloads —
// never computed client-side (CONTEXT.md: "Verdict").

import {
  renderBreakdownChart,
  renderDecisionChart,
  renderFanChart,
  renderOutflowChart,
  renderTornadoChart,
} from "./charts.js";
import { fmtMoney } from "./format.js";

// A winner that wins in 40-60% of simulated futures (the confidence, as
// displayed) is a toss-up, so the headline stops naming it (ADR-0010).
const TOSS_UP_MIN_PCT = 40;
const TOSS_UP_MAX_PCT = 60;

// The last simulate verdict, and whether the last Monte Carlo run called
// it a toss-up. The flag survives a simulate re-render until the matching
// Monte Carlo result replaces it, so dragging a slider inside a toss-up
// does not flash the winner headline on every step.
let lastVerdict = null;
let tossUp = false;

function headlineHtml({ winner, difference, horizonYears }) {
  const amount = `~${fmtMoney(Math.abs(difference))}`;
  if (tossUp) {
    // No Buy/Rent colour on the amount: either colour would imply a winner.
    return `Too close to call: buying and renting end within ${amount} of each other after ${horizonYears} years`;
  }
  const name = winner === "buy" ? "Buying" : "Renting";
  return `${name} leaves you <span class="amount-${winner}">${amount}</span> wealthier if you sell after ${horizonYears} years`;
}

function renderVerdict(data) {
  lastVerdict = data.verdict;
  const { winner, horizonYears } = data.verdict;
  const name = winner === "buy" ? "Buying" : "Renting";
  document.getElementById("verdict-line").innerHTML = headlineHtml(data.verdict);

  const breakevenEl = document.getElementById("verdict-breakeven");
  const b = data.breakevenYear;
  breakevenEl.textContent =
    b != null
      ? `${name} pulls ahead if you stay ≥ ${Math.ceil(b)} years`
      : `No breakeven within ${horizonYears} years`;
  document.getElementById("verdict-confidence").textContent = "";
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

const TABLE_COLUMNS = [
  ["Year", "year", (v) => v.toFixed(0)],
  ["Home value", "homeValue", fmtMoney],
  ["Portfolio (rent)", "equityValue", fmtMoney],
  ["Portfolio (buy)", "buyPortfolioValue", fmtMoney],
  ["Mortgage balance", "mortgageBalance", fmtMoney],
  ["Outflow (buy)", "outflowBuy", fmtMoney],
  ["Outflow (rent)", "outflowRent", fmtMoney],
  ["Net (buy)", "netBuy", fmtMoney],
  ["Net (rent)", "netRent", fmtMoney],
];

function renderTable(series) {
  // Yearly rows for readability; CSV export (below) keeps every month.
  const rows = series.year
    .map((year, i) => ({ year, i }))
    .filter(({ i }) => i % 12 === 0)
    .map(({ i }) => `<tr>${TABLE_COLUMNS.map(([, key, fmt]) => `<td>${fmt(series[key][i])}</td>`).join("")}</tr>`)
    .join("");
  document.getElementById("data-table").innerHTML =
    `<table><thead><tr>${TABLE_COLUMNS.map(([label]) => `<th>${label}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table>`;
}

export function downloadCsv(series) {
  const cols = [
    ["Year", series.year],
    ["Home_Value", series.homeValue],
    ["Equity_Value", series.equityValue],
    ["Buy_Portfolio_Value", series.buyPortfolioValue],
    ["Mortgage_Balance", series.mortgageBalance],
    ["Outflow_Buy", series.outflowBuy],
    ["Outflow_Rent", series.outflowRent],
    ["Cash_Committed", series.cashCommitted],
    ["Net_Buy", series.netBuy],
    ["Net_Rent", series.netRent],
  ];
  const lines = [
    cols.map(([name]) => name).join(","),
    ...series.year.map((_, i) => cols.map(([, arr]) => arr[i]).join(",")),
  ];
  const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" }));
  const link = Object.assign(document.createElement("a"), { href: url, download: "simulation_results.csv" });
  link.click();
  URL.revokeObjectURL(url);
}

export function renderSimulate(data, cfg) {
  renderVerdict(data);
  renderStats(data);
  renderDecisionChart(document.getElementById("decision-chart"), data.series, data.breakevenYear);
  renderOutflowChart(document.getElementById("outflow-chart"), data.series);
  renderBreakdownChart(document.getElementById("breakdown-chart"), data, cfg);
  renderTable(data.series);
  document.getElementById("csv-btn").onclick = () => downloadCsv(data.series);
}

export function renderMonteCarlo(mc, winner) {
  const pct = winner === "buy" ? mc.buyWinsPct : 100 - mc.buyWinsPct;
  const name = winner === "buy" ? "Buying" : "Renting";
  // Decide on the rounded share, so the headline agrees with the number
  // printed beside it (60.4% prints as 60% and is a toss-up).
  const shownPct = Math.round(pct);
  tossUp = shownPct >= TOSS_UP_MIN_PCT && shownPct <= TOSS_UP_MAX_PCT;
  if (lastVerdict) document.getElementById("verdict-line").innerHTML = headlineHtml(lastVerdict);
  document.getElementById("verdict-confidence").textContent =
    ` · ${name} wins in ${shownPct}% of simulated futures`;
  renderFanChart(document.getElementById("fan-chart"), mc);
  renderTornadoChart(document.getElementById("tornado-chart"), mc.tornado);
}
