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

function renderVerdict(data) {
  const { winner, difference, horizonYears } = data.verdict;
  const name = winner === "buy" ? "Buying" : "Renting";
  document.getElementById("verdict-line").innerHTML =
    `${name} leaves you <span class="amount-${winner}">~${fmtMoney(Math.abs(difference))}</span> wealthier if you sell after ${horizonYears} years`;

  const breakevenEl = document.getElementById("verdict-breakeven");
  const b = data.breakevenYear;
  breakevenEl.textContent =
    b != null
      ? `${name} pulls ahead if you stay ≥ ${Math.ceil(b)} years`
      : `No breakeven within ${horizonYears} years`;
  document.getElementById("verdict-confidence").textContent = "";
}

function renderStats(data) {
  document.getElementById("stat-buy").textContent = fmtMoney(data.series.netBuy.at(-1));
  document.getElementById("stat-rent").textContent = fmtMoney(data.series.netRent.at(-1));
  document.getElementById("stat-cost-buy").textContent = `${fmtMoney(data.monthlyCostBuyYear1)}/mo`;
  document.getElementById("stat-cost-rent").textContent = `${fmtMoney(data.monthlyCostRentYear1)}/mo`;
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
  document.getElementById("verdict-confidence").textContent =
    ` · ${name} wins in ${pct.toFixed(0)}% of simulated futures`;
  renderFanChart(document.getElementById("fan-chart"), mc);
  renderTornadoChart(document.getElementById("tornado-chart"), mc.tornado);
}