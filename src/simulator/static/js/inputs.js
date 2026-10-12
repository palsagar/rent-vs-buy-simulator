// Input rendering: left panel (core + assumptions; advanced.js adds the
// Advanced groups through buildField),
// region and outlook preset pills. Slider `scale` converts between the
// stored value and the displayed one (decimal rates display ×100).

import { INPUT_DEFS } from "./fields.js";
import { trackEvent } from "./analytics.js";
import { fmtMoney, parseTypedNumber, setCurrency } from "./format.js";
import {
  DEFAULT_CONFIG,
  KEYS_ADDED_IN_V3,
  applyPreset,
  debounce,
  getConfig,
  getFtb,
  getRegionId,
  setFtb,
  setParam,
  setRegionId,
  linkCarried,
  urlOmitted,
} from "./state.js";

const OUTLOOK_PRESETS = {
  conservative: { propertyAppreciationAnnual: 2.0, equityGrowthAnnual: 5.0, rentInflationRate: 0.02 },
  historical: { propertyAppreciationAnnual: 3.0, equityGrowthAnnual: 7.0, rentInflationRate: 0.03 },
  optimistic: { propertyAppreciationAnnual: 5.0, equityGrowthAnnual: 10.0, rentInflationRate: 0.025 },
};

const SECTION_CONTAINERS = {
  core: "core-inputs",
  assumptions: "assumption-inputs",
};

const widgets = []; // { def, refresh() } — refresh re-reads state into the widget
let regionsList = [];

// Ids that tie a field's name and hint to its control for screen readers.
// The levy cap's amount slider reuses its field's key, hence the counter.
let fieldUid = 0;
const uid = (key) => `f-${key}-${++fieldUid}`;

function buildSlider(def, container) {
  const scale = def.scale ?? 1;
  const id = uid(def.key);
  const row = document.createElement("div");
  row.className = "slider-row";
  row.innerHTML = `
    <div class="slider-header">
      <span class="slider-name" id="${id}-name">${def.label}</span>
      <button type="button" class="slider-value"></button>
  </div>
    <input type="range" min="${def.min}" max="${def.max}" step="${def.step}" aria-labelledby="${id}-name"${def.hint ? ` aria-describedby="${id}-hint"` : ""}>
    ${def.hint ? `<div class="slider-hint" id="${id}-hint">${def.hint}</div>` : ""}
  `;
  const input = row.querySelector("input");
  const value = row.querySelector(".slider-value");
  // The button's name carries the value it shows, so a screen reader
  // announces both the field and its current value.
  const show = (displayed) => {
    const text = def.fmt(displayed);
    value.textContent = text;
    value.setAttribute("aria-label", `${def.label} ${text}, type an exact value`);
    // The slider reads "$500k", as shown, rather than "500000".
    input.setAttribute("aria-valuetext", text);
  };
  const refresh = () => {
    const stored = getConfig()[def.key];
    input.value = stored * scale;
    show(stored * scale);
  };
  // Dragging and typing both store a value in displayed units here. Only
  // a drag passes `drag`, which keeps a toss-up headline (state.js).
  const apply = (displayed, drag = false) => {
    show(displayed);
    setParam(def.key, displayed / scale, { drag });
    // Moving the price across a relief ceiling must withdraw the
    // relief, so the buyer-cost keys cannot stay latched at their FTB
    // values while the price says they no longer apply.
    if (def.key === "propertyPrice") syncFtbToPrice();
  };
  input.addEventListener("input", () => apply(Number(input.value), true));
  // Sent when the slider is released, or 500 ms after the last keyboard
  // step (each arrow-key press is its own change). The typed path's
  // synthetic change is not trusted, so openTypedField counts that one itself.
  const sendSliderChange = () =>
    trackEvent("value-changed", { field: def.key, via: "slider" });
  const sendKeyboardChange = debounce(sendSliderChange, 500);
  let keyboard = false;
  input.addEventListener("keydown", () => { keyboard = true; });
  input.addEventListener("pointerdown", () => { keyboard = false; });
  input.addEventListener("change", (e) => {
    if (!e.isTrusted) return;
    if (keyboard) sendKeyboardChange();
    else sendSliderChange();
  });
  value.addEventListener("click", () =>
    openTypedField(def, value, input, getConfig()[def.key] * scale, apply),
  );
  container.appendChild(row);
  widgets.push({ refresh });
}

// Exact values: tapping a slider's value swaps it for a text field. Enter
// or leaving the field applies the number, clamped to the slider's range
// but NOT snapped to its step (a $437,000 price is allowed); Escape
// cancels. The field exists only while typing, so `#core-inputs input`
// still finds the slider everywhere else (the tour, the tests). `shown`
// is the current value and `apply` stores a new one, both in displayed
// units; `apply` is the slider's own drag handler.
function openTypedField(def, value, slider, shown, apply) {
  const typed = document.createElement("input");
  typed.type = "text";
  typed.className = "slider-typed";
  // The iOS decimal keypad has no minus key, so fields that go below zero
  // get the full keyboard.
  typed.inputMode = def.min < 0 ? "text" : "decimal";
  typed.enterKeyHint = "done";
  typed.setAttribute("aria-label", def.label);
  // Without float noise (0.03 * 100).
  const prefill = String(Number(shown.toFixed(6)));
  typed.value = prefill;
  let cancelled = false;
  let closed = false;
  // Runs once: removing the focused field can fire blur a second time.
  const close = () => {
    if (closed) return;
    closed = true;
    const n = parseTypedNumber(typed.value, def.step >= 1);
    // An unedited field changes nothing: no re-run, and no re-reading of
    // a hand-edited link value such as "1234.567" as digit grouping.
    if (!cancelled && typed.value !== prefill && Number.isFinite(n)) {
      // A typed value is not snapped to the slider's grid, so a field may
      // allow typed values below the slider's floor (the levy cap).
      const clamped = Math.min(def.max, Math.max(def.typedMin ?? def.min, n));
      slider.value = clamped;
      apply(clamped);
      trackEvent("value-changed", { field: def.key, via: "typed" });
      // A typed value counts as a slider change (the tour's do-it step).
      slider.dispatchEvent(new Event("change", { bubbles: true }));
    }
    typed.remove();
    value.hidden = false;
  };
  // Browsers fire the field's own change events inconsistently (Chromium
  // even on removal after Escape, WebKit not on Enter), so they stay in
  // the field; the slider's change above is the one that counts.
  typed.addEventListener("change", (e) => e.stopPropagation());
  typed.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== "Escape") return;
    // Escape here must not also close the inputs sheet or the tour, and
    // Enter must not go on to press the value button focused below,
    // which would reopen the field.
    e.stopPropagation();
    e.preventDefault();
    cancelled = e.key === "Escape";
    close();
    // Only when removing the field dropped focus to the page: a typed value
    // can advance the tour, which moves focus to its next step.
    if (!document.activeElement || document.activeElement === document.body) value.focus();
  });
  typed.addEventListener("blur", close);
  value.hidden = true;
  value.after(typed);
  typed.focus();
  typed.select();
}

function buildSegmented(def, container) {
  const picker = document.createElement("div");
  picker.className = "seg-picker";
  picker.setAttribute("role", "group");
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
  // The wrapping label names the box; the hint describes it.
  if (def.hint) {
    const hint = hintEl(def.hint);
    hint.id = `${uid(def.key)}-hint`;
    input.setAttribute("aria-describedby", hint.id);
    container.appendChild(hint);
  }
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
  container.appendChild(labeledRow(def, row, select));
  widgets.push({ refresh });
}

// The levy cap is one stored number with three meanings, so it shows as a
// three-way choice plus an amount slider used only by "Capped at…".
// Negative is "no cap" (the def's min, -1000, is the value state.js
// restores legacy links to), 0 is "not deductible", positive is the cap.
const LEVY_CAP_CHOICES = [
  ["none", "No cap"],
  ["capped", "Capped at…"],
  ["zero", "Not deductible"],
];
// Where "Capped at…" starts: the cap the US bundle ships.
const LEVY_CAP_START = 10000;
// The amount slider's floor. The def itself keeps min -1000, because
// state.js validates share links against it.
const LEVY_CAP_MIN_AMOUNT = 1000;
// The smallest cap a typed amount can set. Share links accept caps below
// the slider's floor, so typing must reach them too.
const LEVY_CAP_MIN_TYPED = 1;

function levyCapChoice(stored) {
  if (stored < 0) return "none";
  return stored > 0 ? "capped" : "zero";
}

function buildLevyCap(def, container) {
  const picker = document.createElement("div");
  picker.className = "seg-picker seg-picker--text";
  // Screen readers announce the field with each choice.
  picker.setAttribute("role", "group");
  picker.setAttribute("aria-label", def.label);
  const next = { none: def.min, zero: 0, capped: LEVY_CAP_START };
  const buttons = LEVY_CAP_CHOICES.map(([choice, text]) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "seg-btn";
    btn.textContent = text;
    btn.addEventListener("click", () => {
      if (levyCapChoice(getConfig()[def.key]) === choice) return;
      setParam(def.key, next[choice]);
      syncInputs();
    });
    picker.appendChild(btn);
    return btn;
  });
  const controls = document.createElement("div");
  controls.appendChild(picker);
  const amount = document.createElement("div");
  buildSlider(
    {
      ...def,
      label: "Capped at",
      min: LEVY_CAP_MIN_AMOUNT,
      typedMin: LEVY_CAP_MIN_TYPED,
      fmt: fmtMoney,
      hint: undefined,
    },
    amount,
  );
  controls.appendChild(amount);
  const refresh = () => {
    const choice = levyCapChoice(getConfig()[def.key]);
    for (const [i, btn] of buttons.entries()) {
      const on = LEVY_CAP_CHOICES[i][0] === choice;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", String(on));
    }
    amount.hidden = choice !== "capped";
  };
  container.appendChild(labeledRow(def, controls, picker));
  widgets.push({ refresh });
}

// `control` is the element a screen reader announces: it takes the name
// shown above it (unless it has its own) and the hint below it.
function labeledRow(def, el, control = el) {
  const id = uid(def.key);
  const wrap = document.createElement("div");
  const header = document.createElement("div");
  header.className = "slider-header";
  header.innerHTML = `<span class="slider-name" id="${id}-name">${def.label}</span>`;
  wrap.appendChild(header);
  wrap.appendChild(el);
  if (!control.hasAttribute("aria-label")) control.setAttribute("aria-labelledby", `${id}-name`);
  if (def.hint) {
    const hint = hintEl(def.hint);
    hint.id = `${id}-hint`;
    control.setAttribute("aria-describedby", hint.id);
    wrap.appendChild(hint);
  }
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
// Whether the override keys hold the relief's values: as applied, or as
// the user then edited them. After every sync it equals
// `ftbOn && reliefApplies(selectedRegion)`, so the keys move only when
// the relief changes state, never because a relief value was edited.
let ftbInEffect = false;
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

/**
 * True when every override key currently holds its FTB value. Used only
 * to infer the relief setting for a link written before `ftb` existed.
 */
function ftbMatchesConfig(region) {
  const overrides = region?.firstTimeBuyerOverrides ?? {};
  const keys = Object.keys(overrides);
  if (keys.length === 0) return false;
  const cfg = getConfig();
  return keys.every((k) => cfg[k] === overrides[k]);
}

/** Put the relief setting in the share link, for a region that has one. */
function rememberFtb() {
  setFtb(
    hasRelief(selectedRegion) ? ftbOn : null,
    Object.keys(selectedRegion?.firstTimeBuyerOverrides ?? {}),
  );
}

/**
 * Set the relief flags for a config just read from a link or a tour
 * snapshot. `stated` is the setting it carried, or null/undefined for a
 * link written before `ftb` existed: the setting is then inferred from
 * the numbers, which fails once a relief value has been edited (#51).
 * `holdsRelief` says whether the config's relief keys hold the relief,
 * edited or not, when the setting is stated.
 */
function adoptFtb(stated, holdsRelief) {
  const matches = ftbMatchesConfig(selectedRegion);
  if (stated == null) {
    // Only derive the flag from a region that actually enacts relief.
    // ftbMatchesConfig is false for an empty override set, so deriving it
    // from US or DE would latch the flag OFF and the next region WITH
    // relief would then load without it -- FTB must default ON.
    ftbOn = hasRelief(selectedRegion) ? matches : true;
    // Lets syncFtbToPrice withdraw relief values that an old link
    // carries above the ceiling.
    ftbInEffect = matches;
  } else {
    // As above: a stated "off" from US or DE must not latch the flag off
    // for the next region with relief.
    ftbOn = hasRelief(selectedRegion) ? stated : true;
    // A stated setting was written after syncFtbToPrice ran, so the keys
    // hold what the relief at this price says, edits included. When they
    // do not (a hand-built link that states the relief without its
    // numbers), syncFtbToPrice applies it, so the pill never shows the
    // relief on beside numbers that are not the relief's.
    ftbInEffect = ftbOn && reliefApplies(selectedRegion) && holdsRelief;
  }
  rememberFtb();
}

/**
 * Whether the opening link set any of the region's relief values. The app
 * writes every value that differs from the default, and every relief
 * value does, so a link it wrote with the relief in effect sets them,
 * edited or not (unless each was edited back to exactly the default). A
 * hand-built link (`?r=uk&ftb=1`) sets none, and gets the relief values.
 */
function linkHoldsRelief(region) {
  return Object.keys(region?.firstTimeBuyerOverrides ?? {}).some(linkCarried);
}

/**
 * The selected region's value for every Advanced field, with the
 * first-time-buyer relief applied while it is in effect, or null when no
 * region is selected (a link whose numbers match no bundle). Cost
 * inflation is in no bundle, so its default is the app-wide one.
 */
export function regionDefaults() {
  if (!selectedRegion) return null;
  return {
    costInflationRate: DEFAULT_CONFIG.costInflationRate,
    ...selectedRegion.taxPrimitives,
    ...(ftbOn && reliefApplies(selectedRegion) ? selectedRegion.firstTimeBuyerOverrides : {}),
  };
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
  // A key the link was too old to carry still holds the US default, so it
  // says nothing about the region and must not rule one out.
  const carried = ([k]) => !urlOmitted(k);
  return (
    regions.find(
      (region) =>
        region.available &&
        Object.entries(region.taxPrimitives)
          .filter(carried)
          .every(([k, v]) => cfg[k] === v),
    ) ??
    // A config matching no bundle is legitimate -- a hand-edited or
    // FTB-modified share URL. Fall back to matching on the keys the FTB
    // overrides do NOT touch, so a UK+FTB link still resolves to UK.
    regions.find(
      (region) =>
        region.available &&
        Object.entries(region.taxPrimitives)
          .filter(([k]) => !(k in region.firstTimeBuyerOverrides))
          .filter(carried)
          .every(([k, v]) => cfg[k] === v),
    ) ??
    null
  );
}

/**
 * Give each key the opening link was too old to carry the selected
 * region's value, rather than the US default the config started from, or,
 * when the link matches no region, the value it had before the key existed.
 */
function fillKeysTheLinkPredates() {
  const cfg = getConfig();
  const fill = {};
  for (const [k, before] of Object.entries(KEYS_ADDED_IN_V3)) {
    if (!urlOmitted(k)) continue;
    // A link that matches no region has no bundle to ask. It was written
    // before the key existed, so it gets the value that changes nothing:
    // the scenario its sender saw. (The offline stand-in region has no
    // values at all and keeps the default.)
    const value = selectedRegion ? selectedRegion.taxPrimitives[k] : before;
    if (value !== undefined && cfg[k] !== value) fill[k] = value;
  }
  if (Object.keys(fill).length > 0) applyPreset(fill);
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
  ftbInEffect = on;
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
// effect is decided here. The keys move only when the relief changes
// state, so an edited relief value stays while the relief stays in
// effect (#51); crossing the ceiling swaps in the whole set, like the pill.
function syncFtbToPrice() {
  if (!selectedRegion || !hasRelief(selectedRegion)) return;
  const shouldApply = ftbOn && reliefApplies(selectedRegion);
  if (shouldApply !== ftbInEffect) {
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
// a doc nobody opens: collapsed under the verdict they qualify. Notes are
// authored in regions.py, so they travel with the values they qualify.
function renderRegionNotes(region) {
  const box = document.getElementById("region-caveats");
  const list = document.getElementById("region-notes");
  // replaceChildren, not innerHTML: notes are authored data, but the
  // habit matters. Note text below goes in via textContent for the
  // same reason.
  list.replaceChildren();
  const notes = region?.notes ?? [];
  box.hidden = notes.length === 0;
  if (notes.length === 0) return;
  box.querySelector("summary").textContent =
    `${notes.length} ${notes.length === 1 ? "thing" : "things"} to know about the ${region.label} numbers`;
  for (const note of notes) {
    const item = document.createElement("li");
    item.textContent = note;
    list.appendChild(item);
  }
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
  // The price is now the bundle's typical one, judged above.
  ftbInEffect = ftbOn && reliefApplies(selectedRegion);
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
      btn.addEventListener("click", (e) => {
        selectedRegion = region;
        setRegionId(region.id);
        selectRegionPill(regionPills, regions, region);
        applySelectedRegion();
        rememberFtb();
        refreshFtbPill();
        if (e.isTrusted) trackEvent("region-changed", { region: region.id });
      });
    }
    regionPills.appendChild(btn);
  }

  ftbBtn = document.createElement("button");
  ftbBtn.className = "preset-btn";
  ftbBtn.textContent = "First-time buyer";
  ftbBtn.addEventListener("click", (e) => {
    ftbOn = !ftbOn;
    applyFtb(selectedRegion, ftbOn);
    rememberFtb();
    refreshFtbPill();
    if (e.isTrusted) trackEvent("ftb-toggled", { on: ftbOn });
  });
  document.getElementById("ftb-pill").appendChild(ftbBtn);

  // Derive rather than assume: readUrl() has already run, so the config
  // may be any region's. Marking the first pill active regardless would
  // make the first FTB click apply the US delta to a UK config.
  selectedRegion = deriveSelectedRegion(regions);
  fillKeysTheLinkPredates();
  // Persist whatever was derived, so a legacy link upgrades to a stored
  // id on first load and stops depending on the numbers matching. An `r`
  // that names no region is dropped, so a shared link never repeats it.
  setRegionId(selectedRegion?.id ?? null);
  adoptFtb(getFtb(), linkHoldsRelief(selectedRegion));
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
    btn.addEventListener("click", (e) => {
      for (const el of outlookPills.querySelectorAll(".preset-btn")) el.classList.remove("active");
      btn.classList.add("active");
      applyPreset(preset);
      syncInputs();
      if (e.isTrusted) trackEvent("outlook-changed", { outlook: name });
    });
    outlookPills.appendChild(btn);
  }
}

/** Render one field's widget into `container`. advanced.js uses it too. */
export function buildField(def, container) {
  if (def.type === "segmented") buildSegmented(def, container);
  else if (def.type === "checkbox") buildCheckbox(def, container);
  else if (def.type === "select") buildSelect(def, container);
  else if (def.type === "levyCap") buildLevyCap(def, container);
  else buildSlider(def, container);
}

export function initInputs(regions) {
  regionsList = regions;
  // advanced.js renders the Advanced fields into their groups.
  for (const def of INPUT_DEFS) {
    if (def.section === "advanced") continue;
    buildField(def, document.getElementById(SECTION_CONTAINERS[def.section]));
  }
  buildPresetPills(regions);
  syncInputs();
}

export function syncInputs() {
  for (const widget of widgets) widget.refresh();
}

/** Add a widget that syncInputs() refreshes (advanced.js's markers). */
export function registerWidget(widget) {
  widgets.push(widget);
}

/**
 * Capture the settings a tour may disturb, for restore on exit.
 * Includes `ftbOn` (user intent), not just the config, so restoring can
 * re-enable a relief that was priced out during the tour, and
 * `ftbInEffect`, so an edited relief value is restored as edited.
 */
export function snapshotSettings() {
  return { config: getConfig(), regionId: getRegionId(), ftbOn, ftbInEffect };
}

/**
 * Restore a snapshotSettings() snapshot: config, region pill, FTB pill,
 * currency, and region notes. A null regionId (legacy custom link) restores
 * to no active pill and the neutral "$" currency.
 */
export function restoreSettings(snapshot) {
  const region =
    regionsList.find((r) => r.available && r.id === snapshot.regionId) ?? null;
  selectedRegion = region;
  setCurrency(region ? region.currencySymbol : "$");
  // Restores every config key, including any FTB override values.
  applyPreset(snapshot.config);
  setRegionId(snapshot.regionId);
  adoptFtb(snapshot.ftbOn, snapshot.ftbInEffect);
  selectRegionPill(document.getElementById("region-pills"), regionsList, region);
  // Outlook pills have no authoritative match after restore; clear the chrome
  // rather than leave a stale highlight (the app already tolerates this
  // drift when sliders are dragged after picking an outlook).
  document
    .querySelectorAll("#outlook-pills .preset-btn")
    .forEach((b) => b.classList.remove("active"));
  syncInputs();
  syncFtbToPrice();
  refreshFtbPill();
  renderRegionNotes(region);
}
