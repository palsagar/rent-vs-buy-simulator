// Input rendering: left panel (core + assumptions), advanced drawer,
// region and outlook preset pills. Slider `scale` converts between the
// stored value and the displayed one (decimal rates display ×100).

import { fmtCompact, fmtMoney, fmtPct } from "./format.js";
import { applyPreset, getConfig, setParam } from "./state.js";

const INPUT_DEFS = [
  { key: "propertyPrice", label: "Home price", min: 50000, max: 2000000, step: 5000, fmt: fmtCompact, section: "core", hint: "Purchase price of the property" },
  { key: "downPaymentPct", label: "Down payment", min: 5, max: 50, step: 1, fmt: (v) => fmtPct(v, 0), section: "core" },
  { key: "mortgageRateAnnual", label: "Mortgage rate", min: 1, max: 10, step: 0.05, fmt: (v) => fmtPct(v, 2), section: "core" },
  { key: "mortgageTermYears", label: "Mortgage term", type: "segmented", options: [15, 20, 30], section: "core", hint: "Amortization period — independent of the horizon" },
  { key: "monthlyRent", label: "Monthly rent", min: 500, max: 10000, step: 50, fmt: fmtMoney, section: "core" },
  { key: "horizonYears", label: "Horizon", min: 2, max: 40, step: 1, fmt: (v) => `${v} yrs`, section: "core", hint: "Years until you'd sell — the chart x-axis ends here" },
  { key: "propertyAppreciationAnnual", label: "Property appreciation", min: 0, max: 10, step: 0.1, fmt: (v) => fmtPct(v), section: "assumptions" },
  { key: "equityGrowthAnnual", label: "Equity growth (CAGR)", min: 0, max: 15, step: 0.1, fmt: (v) => fmtPct(v), section: "assumptions" },
  { key: "rentInflationRate", label: "Rent inflation", min: 0, max: 10, step: 0.1, scale: 100, fmt: (v) => fmtPct(v), section: "assumptions" },
  { key: "closingCostBuyerPct", label: "Buyer closing costs", min: 0, max: 10, step: 0.1, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "closingCostSellerPct", label: "Seller closing costs", min: 0, max: 10, step: 0.1, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "propertyTaxRate", label: "Property levy", min: 0, max: 5, step: 0.05, fmt: (v) => fmtPct(v, 2), section: "advanced" },
  { key: "annualHomeInsurance", label: "Home insurance /yr", min: 0, max: 5000, step: 50, fmt: fmtMoney, section: "advanced" },
  { key: "annualMaintenancePct", label: "Maintenance", min: 0, max: 5, step: 0.1, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "costInflationRate", label: "Cost inflation", min: 0, max: 10, step: 0.1, scale: 100, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "interestDeductionEnabled", label: "Interest deductible", type: "checkbox", section: "advanced", hint: "Deduct mortgage interest (and capped levy) from taxable income" },
  { key: "marginalTaxRatePct", label: "Marginal tax rate", min: 0, max: 60, step: 1, fmt: (v) => fmtPct(v, 0), section: "advanced" },
  { key: "levyDeductionCap", label: "Levy deduction cap", min: 0, max: 50000, step: 1000, fmt: (v) => (v === 0 ? "uncapped" : fmtMoney(v)), section: "advanced", hint: "0 = uncapped (US SALT cap is $10k)" },
  { key: "saleCgRegime", label: "Home-sale CG rule", type: "select", options: [["exempt_amount", "Exempt up to a fixed amount"], ["exempt_after_years", "Exempt after N years"], ["fully_exempt", "Always exempt"]], section: "advanced" },
  { key: "saleCgExemptAmount", label: "Exempt gain amount", min: 0, max: 1000000, step: 10000, fmt: fmtCompact, section: "advanced" },
  { key: "saleCgExemptAfterYears", label: "Exempt after (years)", min: 0, max: 30, step: 1, fmt: (v) => `${v} yrs`, section: "advanced" },
  { key: "saleCgRatePct", label: "Home-sale CG rate", min: 0, max: 40, step: 0.5, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "portfolioCgRatePct", label: "Investment CG rate", min: 0, max: 40, step: 0.5, fmt: (v) => fmtPct(v), section: "advanced" },
];

const OUTLOOK_PRESETS = {
  conservative: { propertyAppreciationAnnual: 2.0, equityGrowthAnnual: 5.0, rentInflationRate: 0.02 },
  historical: { propertyAppreciationAnnual: 3.0, equityGrowthAnnual: 7.0, rentInflationRate: 0.03 },
  optimistic: { propertyAppreciationAnnual: 5.0, equityGrowthAnnual: 10.0, rentInflationRate: 0.025 },
};

const SECTION_CONTAINERS = {
  core: "core-inputs",
  assumptions: "assumption-inputs",
  advanced: "advanced-inputs",
};

const widgets = []; // { def, refresh() } — refresh re-reads state into the widget

function buildSlider(def, container) {
  const scale = def.scale ?? 1;
  const row = document.createElement("div");
  row.className = "slider-row";
  row.innerHTML = `
    <div class="slider-header">
      <span class="slider-name">${def.label}</span>
      <span class="slider-value"></span>
  </div>
    <input type="range" min="${def.min}" max="${def.max}" step="${def.step}">
    ${def.hint ? `<div class="slider-hint">${def.hint}</div>` : ""}
  `;
  const input = row.querySelector("input");
  const value = row.querySelector(".slider-value");
  const refresh = () => {
    const stored = getConfig()[def.key];
    input.value = stored * scale;
    value.textContent = def.fmt(stored * scale);
  };
  input.addEventListener("input", () => {
    const displayed = Number(input.value);
    value.textContent = def.fmt(displayed);
    setParam(def.key, displayed / scale);
  });
  container.appendChild(row);
  widgets.push({ refresh });
}

function buildSegmented(def, container) {
  const picker = document.createElement("div");
  picker.className = "seg-picker";
  const buttons = def.options.map((option) => {
    const btn = document.createElement("button");
    btn.className = "seg-btn";
    btn.textContent = option;
    btn.addEventListener("click", () => setParam(def.key, option));
    picker.appendChild(btn);
    return btn;
  });
  const refresh = () => {
    const stored = getConfig()[def.key];
    for (const [i, btn] of buttons.entries()) {
      btn.classList.toggle("active", def.options[i] === stored);
    }
  };
  container.appendChild(labeledRow(def, picker));
  widgets.push({ refresh });
}

function buildCheckbox(def, container) {
  const row = document.createElement("label");
  row.className = "checkbox-row";
  const input = document.createElement("input");
  input.type = "checkbox";
  row.appendChild(input);
  row.appendChild(document.createTextNode(def.label));
  const refresh = () => {
    input.checked = getConfig()[def.key];
  };
  input.addEventListener("change", () => setParam(def.key, input.checked));
  container.appendChild(row);
  if (def.hint) container.appendChild(hintEl(def.hint));
  widgets.push({ refresh });
}

function buildSelect(def, container) {
  const select = document.createElement("select");
  for (const [value, label] of def.options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  }
  const refresh = () => {
    select.value = getConfig()[def.key];
  };
  select.addEventListener("change", () => setParam(def.key, select.value));
  const row = document.createElement("div");
  row.className = "select-row";
  row.appendChild(select);
  container.appendChild(labeledRow(def, row));
  widgets.push({ refresh });
}

function labeledRow(def, el) {
  const wrap = document.createElement("div");
  const header = document.createElement("div");
  header.className = "slider-header";
  header.innerHTML = `<span class="slider-name">${def.label}</span>`;
  wrap.appendChild(header);
  wrap.appendChild(el);
  if (def.hint) wrap.appendChild(hintEl(def.hint));
  return wrap;
}

function hintEl(text) {
  const hint = document.createElement("div");
  hint.className = "slider-hint";
  hint.textContent = text;
  return hint;
}

function buildPresetPills(regions) {
  const regionPills = document.getElementById("region-pills");
  for (const region of regions) {
    const btn = document.createElement("button");
    btn.className = `preset-btn${region.available ? "" : " disabled"}`;
    btn.textContent = region.id.toUpperCase();
    if (!region.available) {
      btn.disabled = true;
      btn.title = "Coming in a follow-up — values pending research";
    } else {
      btn.addEventListener("click", () => {
        for (const el of regionPills.querySelectorAll(".preset-btn")) el.classList.remove("active");
        btn.classList.add("active");
        applyPreset({ ...region.typical, ...region.taxPrimitives });
        syncInputs();
      });
    }
    regionPills.appendChild(btn);
  }
  regionPills.querySelector(".preset-btn:not(.disabled)")?.classList.add("active");

  const outlookPills = document.getElementById("outlook-pills");
  for (const [name, preset] of Object.entries(OUTLOOK_PRESETS)) {
    const btn = document.createElement("button");
    btn.className = "preset-btn";
    btn.textContent = name[0].toUpperCase() + name.slice(1);
    btn.addEventListener("click", () => {
      for (const el of outlookPills.querySelectorAll(".preset-btn")) el.classList.remove("active");
      btn.classList.add("active");
      applyPreset(preset);
      syncInputs();
    });
    outlookPills.appendChild(btn);
  }
}

export function initInputs(regions) {
  for (const def of INPUT_DEFS) {
    const container = document.getElementById(SECTION_CONTAINERS[def.section]);
    if (def.type === "segmented") buildSegmented(def, container);
    else if (def.type === "checkbox") buildCheckbox(def, container);
    else if (def.type === "select") buildSelect(def, container);
    else buildSlider(def, container);
  }
  buildPresetPills(regions);
  syncInputs();
}

export function syncInputs() {
  for (const widget of widgets) widget.refresh();
}
