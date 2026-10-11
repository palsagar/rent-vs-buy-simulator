// Advanced inputs: the fields that tailor the model to one situation, in
// five collapsible groups at the end of the inputs panel. Every group
// starts closed and summarises its values, and a field that another field
// has switched off in the engine is hidden. Both are derived from the
// config on every change, so nothing here is stored. Field metadata
// (label, help line, group, visibleWhen) lives in fields.js.

import { trackEvent } from "./analytics.js";
import { INPUT_DEFS } from "./fields.js";
import { fmtCompact, fmtMoney, MINUS } from "./format.js";
import { buildField } from "./inputs.js";
import { getConfig, onConfigChange } from "./state.js";

const FLOAT_TOLERANCE = 1e-9;

// A rate without trailing zeros: 3 -> "3%", 1.75 -> "1.75%", 7.468 -> "7.47%".
const pct = (v) => `${Number(v.toFixed(2))}%`;
const nonZero = (v) => Math.abs(v) > FLOAT_TOLERANCE;

function summarizeTransaction(c) {
  const fixed = c.closingCostBuyerAmount;
  const fixedPart = nonZero(fixed) ? ` ${fixed < 0 ? MINUS : "+"} ${fmtMoney(Math.abs(fixed))}` : "";
  return `Buy ${pct(c.closingCostBuyerPct)}${fixedPart} · Sell ${pct(c.closingCostSellerPct)}`;
}

// Year-1 owning costs at today's price: the % parts of the levy and of
// maintenance, plus every fixed amount.
function summarizeYearly(c) {
  const total =
    (c.propertyPrice * (c.propertyTaxRate + c.annualMaintenancePct)) / 100 +
    c.annualPropertyLevy +
    c.annualHomeInsurance +
    c.annualMaintenanceAmount;
  return `≈ ${fmtMoney(total)} in year 1`;
}

function summarizeMortgageRelief(c) {
  return c.interestDeductionEnabled ? `On · ${pct(c.marginalTaxRatePct)} tax rate` : "Off";
}

function summarizeHomeSale(c) {
  if (c.saleCgRegime === "exempt_amount") return `Tax-free up to ${fmtCompact(c.saleCgExemptAmount)}`;
  if (c.saleCgRegime === "exempt_after_years") return `Tax-free after ${c.saleCgExemptAfterYears} yrs`;
  return "Always tax-free";
}

function summarizeInvestments(c) {
  const wealth = (c.portfolioDeemedReturnPct * c.portfolioDragRatePct) / 100;
  const wealthPart = nonZero(wealth) ? ` · wealth tax ${pct(wealth)}/yr` : "";
  return `${pct(c.portfolioCgRatePct)} on gains${wealthPart}`;
}

// `id` is also the group name sent with the analytics events.
const GROUPS = [
  { id: "transaction", title: "Buying and selling costs", summarize: summarizeTransaction },
  { id: "yearly", title: "Yearly costs of owning", summarize: summarizeYearly },
  { id: "mortgage-relief", title: "Tax relief on the mortgage", summarize: summarizeMortgageRelief },
  { id: "home-sale", title: "Tax when you sell the home", summarize: summarizeHomeSale },
  { id: "investments", title: "Tax on investments", summarize: summarizeInvestments },
];

// One line under each %-plus-fixed pair, after its fixed half.
const PAIR_NOTES = {
  closingCostBuyerAmount: "Both apply. The total is the % of the price plus the fixed amount.",
  annualPropertyLevy: "Both apply. The total is the % of the home's value plus the fixed amount.",
  annualMaintenanceAmount: "Both apply. The total is the % of the home's value plus the fixed amount.",
};

// One entry per group: { group, values, changed, fields: [{ def, el }] }.
const rendered = [];

function buildGroup(group, host) {
  const details = document.createElement("details");
  details.className = "adv-group";
  details.dataset.group = group.id;

  const summary = document.createElement("summary");
  const title = document.createElement("span");
  title.className = "adv-group-title";
  title.textContent = group.title;
  const line = document.createElement("span");
  line.className = "adv-group-summary";
  const values = document.createElement("span");
  values.className = "adv-group-values";
  const changed = document.createElement("span");
  changed.className = "adv-group-changed";
  line.append(values, changed);
  summary.append(title, line);
  summary.addEventListener("click", (e) => {
    // The click lands before the toggle, so a closed group is opening.
    // Only real clicks count: the tour and the tests click programmatically.
    if (e.isTrusted && !details.open) trackEvent("advanced-group-opened", { group: group.id });
  });

  const body = document.createElement("div");
  body.className = "adv-group-body";
  const fields = [];
  for (const def of INPUT_DEFS.filter((d) => d.group === group.id)) {
    const el = document.createElement("div");
    el.className = "adv-field";
    el.dataset.key = def.key;
    buildField(def, el);
    body.appendChild(el);
    if (PAIR_NOTES[def.key]) {
      const note = document.createElement("div");
      note.className = "slider-hint adv-pair-note";
      note.textContent = PAIR_NOTES[def.key];
      body.appendChild(note);
    }
    fields.push({ def, el });
  }

  details.append(summary, body);
  host.appendChild(details);
  return { group, values, changed, fields };
}

function refresh() {
  const cfg = getConfig();
  for (const { group, values, fields } of rendered) {
    values.textContent = group.summarize(cfg);
    for (const { def, el } of fields) {
      el.hidden = def.visibleWhen ? !def.visibleWhen(cfg) : false;
    }
  }
}

export function initAdvanced() {
  const host = document.getElementById("advanced-inputs");
  for (const group of GROUPS) rendered.push(buildGroup(group, host));
  refresh();
  onConfigChange(refresh);
}
