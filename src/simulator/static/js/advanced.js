// Advanced inputs: the fields that tailor the model to one situation, in
// five collapsible groups at the end of the inputs panel. Every group
// starts closed and summarises its values. A field that another field has
// switched off in the engine is hidden, and a field that differs from the
// selected region's default gets a dot and a "Region default" line; each
// group can be reset to those defaults. All of it is derived from the
// config and the region, so nothing here is stored or put in the share
// link. Field metadata (label, help line, group, visibleWhen) lives in
// fields.js.

import { trackEvent } from "./analytics.js";
import { INPUT_DEFS } from "./fields.js";
import { fmtCompact, fmtMoney, MINUS } from "./format.js";
import { buildField, regionDefaults, registerWidget, syncInputs } from "./inputs.js";
import { applyPreset, getConfig, onConfigChange } from "./state.js";

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
// maintenance, every fixed amount, and mortgage insurance, a % of the
// loan charged only below 20% down (engine.py).
function summarizeYearly(c) {
  const loan = c.propertyPrice * (1 - c.downPaymentPct / 100);
  const mortgageInsurance = c.downPaymentPct < 20 ? (loan * c.mortgageInsuranceRatePct) / 100 : 0;
  const total =
    (c.propertyPrice * (c.propertyTaxRate + c.annualMaintenancePct)) / 100 +
    c.annualPropertyLevy +
    c.annualHomeInsurance +
    c.annualMaintenanceAmount +
    mortgageInsurance;
  return `≈ ${fmtMoney(total)} in year 1`;
}

function summarizeMortgageRelief(c) {
  return c.interestDeductionEnabled ? `On · ${pct(c.marginalTaxRatePct)} tax rate` : "Off";
}

function summarizeHomeSale(c) {
  if (c.saleCgRegime === "exempt_amount") return `Tax-free up to ${fmtCompact(c.saleCgExemptAmount)}`;
  if (c.saleCgRegime === "exempt_after_years") return `Tax-free after ${c.saleCgExemptAfterYears} ${c.saleCgExemptAfterYears === 1 ? "yr" : "yrs"}`;
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

// Every negative levy cap means "no cap", and a share link may carry any
// of them, so two negative caps are the same setting.
const levyCapSetting = (v) => (v < 0 ? -1 : v);

function differs(value, fallback) {
  if (typeof value === "number" && typeof fallback === "number") {
    return Math.abs(value - fallback) > FLOAT_TOLERANCE;
  }
  return value !== fallback;
}

/**
 * Whether a field differs from its region default. False when there is
 * nothing to compare against: no region, or a key missing from the
 * defaults (the offline fallback region has no bundle). print.js uses it.
 */
export function changedFromRegion(def, cfg, defaults) {
  const asSetting = def.type === "levyCap" ? levyCapSetting : (v) => v;
  return (
    defaults !== null &&
    def.key in defaults &&
    differs(asSetting(cfg[def.key]), asSetting(defaults[def.key]))
  );
}

/** A stored value as its own widget would show it. */
function formatStored(def, stored) {
  if (def.type === "checkbox") return stored ? "on" : "off";
  if (def.type === "select") {
    return def.options.find(([value]) => value === stored)?.[1] ?? String(stored);
  }
  return def.fmt(stored * (def.scale ?? 1));
}

/**
 * The default for the "Region default" line. A field can show less than the
 * region's value: a rate has more decimals than its field (NL top tax rate
 * 37.56% in a 0-decimal field), and a compact amount drops digits ($250,400
 * reads "$250k"). Where the field's text would read the same as the current
 * value, the line shows the exact default instead: a rate to 4 decimals, an
 * amount in full.
 */
function formatDefault(def, regionValue, current) {
  const text = formatStored(def, regionValue);
  if (typeof regionValue !== "number" || text !== formatStored(def, current)) return text;
  const exact = regionValue * (def.scale ?? 1);
  return text.endsWith("%") ? `${Number(exact.toFixed(4))}%` : fmtMoney(exact);
}

// One entry per group: { group, values, changed, reset, fields: [{ def, el, dot, note }] }.
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
    // The field's own label comes first in its markup; the levy cap's
    // amount slider has a second one further down.
    const dot = document.createElement("span");
    dot.className = "adv-changed-dot";
    dot.setAttribute("aria-hidden", "true");
    el.querySelector(".slider-name, .checkbox-row").appendChild(dot);
    const note = document.createElement("div");
    note.className = "adv-changed-note";
    el.appendChild(note);
    body.appendChild(el);
    if (PAIR_NOTES[def.key]) {
      const pair = document.createElement("div");
      pair.className = "slider-hint adv-pair-note";
      pair.textContent = PAIR_NOTES[def.key];
      body.appendChild(pair);
    }
    fields.push({ def, el, dot, note });
  }

  const reset = document.createElement("button");
  reset.type = "button";
  reset.className = "adv-reset";
  reset.textContent = "Reset to region defaults";
  reset.addEventListener("click", (e) => {
    const defaults = regionDefaults();
    if (!defaults) return;
    // Every field in the group, hidden ones included.
    const keys = fields.map(({ def }) => def.key).filter((key) => key in defaults);
    applyPreset(Object.fromEntries(keys.map((key) => [key, defaults[key]])));
    syncInputs();
    // The reset hides itself once nothing differs; keep keyboard focus in
    // the group rather than dropping it to the page.
    summary.focus();
    if (e.isTrusted) trackEvent("advanced-reset", { group: group.id });
  });
  body.appendChild(reset);

  details.append(summary, body);
  host.appendChild(details);
  return { group, values, changed, reset, fields };
}

function refresh() {
  const cfg = getConfig();
  const defaults = regionDefaults();
  for (const { group, values, changed, reset, fields } of rendered) {
    values.textContent = group.summarize(cfg);
    let shown = 0;
    let any = false;
    for (const { def, el, dot, note } of fields) {
      const visible = def.visibleWhen ? def.visibleWhen(cfg) : true;
      const isChanged = changedFromRegion(def, cfg, defaults);
      el.hidden = !visible;
      dot.hidden = !isChanged;
      note.hidden = !isChanged;
      note.textContent = isChanged
        ? `Region default: ${formatDefault(def, defaults[def.key], cfg[def.key])}`
        : "";
      if (isChanged) {
        any = true;
        if (visible) shown += 1;
      }
    }
    // A hidden field has no effect, so only visible ones count; reset
    // still restores the hidden ones.
    changed.textContent = shown > 0 ? ` · ${shown} changed` : "";
    reset.hidden = !any;
  }
}

export function initAdvanced() {
  const host = document.getElementById("advanced-inputs");
  for (const group of GROUPS) rendered.push(buildGroup(group, host));
  refresh();
  onConfigChange(refresh);
  // syncInputs also runs after changes that move the region or the relief
  // without a config change of their own (the tour's restore).
  registerWidget({ refresh });
}
