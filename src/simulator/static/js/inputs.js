// Input rendering: left panel (core + assumptions), advanced drawer,
// region and outlook preset pills. Slider `scale` converts between the
// stored value and the displayed one (decimal rates display ×100).

import { INPUT_DEFS } from "./fields.js";
import { applyPreset, getConfig, setParam } from "./state.js";

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
