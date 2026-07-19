// Input rendering: left panel (core + assumptions), advanced drawer,
// region and outlook preset pills. Slider `scale` converts between the
// stored value and the displayed one (decimal rates display ×100).

import { INPUT_DEFS } from "./fields.js";
import { fmtMoney, setCurrency } from "./format.js";
import {
  applyPreset,
  getConfig,
  getRegionId,
  setParam,
  setRegionId,
} from "./state.js";

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
    // Dragging the price across a relief ceiling must withdraw the
    // relief, so the buyer-cost keys cannot stay latched at their FTB
    // values while the price says they no longer apply.
    if (def.key === "propertyPrice") syncFtbToPrice();
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
    btn.addEventListener("click", () => {
      setParam(def.key, option);
      refresh();
    });
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

// The first-time-buyer relief is a modifier OF the region, not an engine
// field: which buyer-cost numbers apply is region-specific statute the
// engine must never know (ADR-0007). It defaults ON because the relief
// is the common case, and it is visible rather than buried in Advanced
// because a default-on relief with no visible cause is a trap.
let selectedRegion = null;
let ftbOn = true;
let ftbBtn = null;

/** Whether this region enacts any first-time-buyer relief (US, DE: no). */
function hasRelief(region) {
  return Object.keys(region?.firstTimeBuyerOverrides ?? {}).length > 0;
}

// Reliefs are withdrawn above a statutory price (UK GBP500,000 outright;
// NL the EUR555,000 startersvrijstelling ceiling). Applying one above its
// ceiling models a discount that does not exist, and because the tool
// outputs a single signed number that is enough to invert it -- the UK
// verdict flips across roughly GBP610k-GBP710k. Relief must therefore be
// a function of price, not a latched flag.
/** Whether relief exists for this region AT this price. */
function reliefApplies(region) {
  if (!hasRelief(region)) return false;
  const cap = region.firstTimeBuyerMaxPrice;
  return cap == null || getConfig().propertyPrice <= cap;
}

/** True when every override key currently holds its FTB value. */
function ftbMatchesConfig(region) {
  const overrides = region?.firstTimeBuyerOverrides ?? {};
  const keys = Object.keys(overrides);
  if (keys.length === 0) return false;
  const cfg = getConfig();
  return keys.every((k) => cfg[k] === overrides[k]);
}

/**
 * The selected region: its stored id when the link carries one, else
 * reverse-matched from the numbers for links written before `r` existed.
 */
function deriveSelectedRegion(regions) {
  const stored = getRegionId();
  if (stored) {
    const named = regions.find((r) => r.available && r.id === stored);
    if (named) return named;
  }
  const cfg = getConfig();
  return (
    regions.find(
      (region) =>
        region.available &&
        Object.entries(region.taxPrimitives).every(([k, v]) => cfg[k] === v),
    ) ??
    // A config matching no bundle is legitimate -- a hand-edited or
    // FTB-modified share URL. Fall back to matching on the keys the FTB
    // overrides do NOT touch, so a UK+FTB link still resolves to UK.
    regions.find(
      (region) =>
        region.available &&
        Object.entries(region.taxPrimitives)
          .filter(([k]) => !(k in region.firstTimeBuyerOverrides))
          .every(([k, v]) => cfg[k] === v),
    ) ??
    null
  );
}

/** Move ONLY the override keys. Never re-applies the whole bundle. */
function applyFtb(region, on) {
  const keys = Object.keys(region?.firstTimeBuyerOverrides ?? {});
  if (keys.length === 0) return; // DE, US: inert by data
  applyPreset(
    Object.fromEntries(
      keys.map((k) => [
        k,
        on ? region.firstTimeBuyerOverrides[k] : region.taxPrimitives[k],
      ]),
    ),
  );
  syncInputs();
}

function refreshFtbPill() {
  if (!ftbBtn) return;
  const enacted = hasRelief(selectedRegion);
  const applies = reliefApplies(selectedRegion);
  // Priced out reads as disabled, like a region with no relief at all:
  // in both cases there is nothing the user could switch on.
  ftbBtn.disabled = !applies;
  ftbBtn.classList.toggle("disabled", !applies);
  ftbBtn.classList.toggle("active", applies && ftbOn);
  if (!enacted) {
    ftbBtn.title = "This region has no first-time-buyer relief";
  } else if (!applies) {
    const cap = selectedRegion.firstTimeBuyerMaxPrice;
    ftbBtn.title =
      `Relief is withdrawn above ${fmtMoney(cap)} — ` +
      "it does not apply at this price";
  } else {
    ftbBtn.title = "Apply this region's first-time-buyer relief";
  }
}

// The price slider can cross a relief ceiling, so the override keys must
// be re-derived whenever the price moves -- not just when the pill is
// clicked. ftbOn is preserved as the user's INTENT; whether it takes
// effect is decided here.
function syncFtbToPrice() {
  if (!selectedRegion || !hasRelief(selectedRegion)) return;
  const shouldApply = ftbOn && reliefApplies(selectedRegion);
  if (shouldApply !== ftbMatchesConfig(selectedRegion)) {
    applyFtb(selectedRegion, shouldApply);
  }
  refreshFtbPill();
}

function selectRegionPill(regionPills, regions, region) {
  for (const el of regionPills.querySelectorAll(".preset-btn")) {
    el.classList.remove("active");
  }
  if (!region) return;
  const index = regions.filter((r) => r.available).indexOf(region);
  const buttons = regionPills.querySelectorAll(".preset-btn:not(.disabled)");
  buttons[index]?.classList.add("active");
}

// Every region's known simplifications are disclosed here rather than in
// a doc nobody opens. Notes are authored in regions.py, so they travel
// with the values they qualify.
function renderRegionNotes(region) {
  const host = document.getElementById("region-notes");
  if (!host) return;
  // replaceChildren, not innerHTML: notes are authored data, but the
  // habit matters. Note text below goes in via textContent for the
  // same reason.
  host.replaceChildren();
  if (!region?.notes?.length) return;
  const heading = document.createElement("strong");
  heading.textContent = `${region.label} — modelling notes:`;
  const list = document.createElement("ul");
  for (const note of region.notes) {
    const item = document.createElement("li");
    item.textContent = note;
    list.appendChild(item);
  }
  host.appendChild(heading);
  host.appendChild(list);
}

function applySelectedRegion() {
  if (!selectedRegion) return;
  // Before applyPreset, so the re-render it triggers already has the
  // right symbol -- the chart hovertemplates are built at call time.
  setCurrency(selectedRegion.currencySymbol);
  applyPreset({
    ...selectedRegion.typical,
    ...selectedRegion.taxPrimitives,
    // The bundle's own typical price applies here, so eligibility is
    // judged against it rather than against the outgoing region's.
    ...(ftbOn &&
    (selectedRegion.firstTimeBuyerMaxPrice == null ||
      selectedRegion.typical.propertyPrice <=
        selectedRegion.firstTimeBuyerMaxPrice)
      ? selectedRegion.firstTimeBuyerOverrides
      : {}),
  });
  syncInputs();
  renderRegionNotes(selectedRegion);
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
        selectedRegion = region;
        setRegionId(region.id);
        selectRegionPill(regionPills, regions, region);
        applySelectedRegion();
        refreshFtbPill();
      });
    }
    regionPills.appendChild(btn);
  }

  ftbBtn = document.createElement("button");
  ftbBtn.className = "preset-btn";
  ftbBtn.textContent = "First-time buyer";
  ftbBtn.addEventListener("click", () => {
    ftbOn = !ftbOn;
    applyFtb(selectedRegion, ftbOn);
    refreshFtbPill();
  });
  document.getElementById("ftb-pill").appendChild(ftbBtn);

  // Derive rather than assume: readUrl() has already run, so the config
  // may be any region's. Marking the first pill active regardless would
  // make the first FTB click apply the US delta to a UK config.
  selectedRegion = deriveSelectedRegion(regions);
  // Persist whatever was derived, so a legacy link upgrades to a stored
  // id on first load and stops depending on the numbers matching.
  if (selectedRegion) setRegionId(selectedRegion.id);
  // Only derive the flag from a region that actually enacts relief.
  // ftbMatchesConfig is false for an empty override set, so deriving it
  // from US or DE would latch the flag OFF and the next region WITH
  // relief would then load without it -- FTB must default ON.
  ftbOn = hasRelief(selectedRegion) ? ftbMatchesConfig(selectedRegion) : true;
  if (selectedRegion) setCurrency(selectedRegion.currencySymbol);
  selectRegionPill(regionPills, regions, selectedRegion);
  // A link shared before relief was priced can carry the FTB buyer costs
  // above the ceiling. Correct the config rather than only the pill,
  // otherwise the stale link keeps its inverted verdict.
  syncFtbToPrice();
  refreshFtbPill();
  renderRegionNotes(selectedRegion);

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
