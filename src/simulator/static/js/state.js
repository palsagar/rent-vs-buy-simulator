// Central config state, share-URL codec, debounce, and result cache.

import { INPUT_DEFS } from "./fields.js";

export const DEFAULT_CONFIG = {
  horizonYears: 10,
  propertyPrice: 500000,
  downPaymentPct: 20,
  mortgageRateAnnual: 6.5,
  propertyAppreciationAnnual: 3.0,
  equityGrowthAnnual: 7.0,
  monthlyRent: 2400,
  mortgageTermYears: 30,
  rentInflationRate: 0.03,
  closingCostBuyerPct: 3.0,
  closingCostSellerPct: 6.0,
  propertyTaxRate: 1.2,
  annualHomeInsurance: 1200,
  annualMaintenancePct: 1.0,
  costInflationRate: 0.025,
  annualPropertyLevy: 0,
  levyPaidByOccupier: false,
  annualMaintenanceAmount: 0,
  closingCostBuyerAmount: 0,
  portfolioDeemedReturnPct: 0,
  portfolioDragRatePct: 0,
  interestDeductionEnabled: true,
  marginalTaxRatePct: 24.0,
  levyDeductionCap: 10000,
  saleCgRegime: "exempt_amount",
  saleCgExemptAmount: 250000,
  saleCgExemptAfterYears: 10,
  saleCgRatePct: 15.0,
  portfolioCgRatePct: 15.0,
  mortgageInsuranceRatePct: 0.5,
};

let config = { ...DEFAULT_CONFIG };
const listeners = [];

export function getConfig() {
  return { ...config };
}

export function onConfigChange(fn) {
  listeners.push(fn);
}

// Debounced like the simulate run, so the link and the charts settle
// together. Writing on every slider tick broke Safari, which throws once a
// page makes 100 history updates in 10 s -- and the throw also skipped the
// listeners below, so the results froze mid-drag.
const scheduleUrlWrite = debounce(writeUrl, 300);

function emit(drag) {
  scheduleUrlWrite();
  for (const fn of listeners) fn(getConfig(), { drag });
}

// `drag` marks a change made by dragging a slider (its input events).
// Listeners get it beside the config: main.js keeps the toss-up wording
// through a drag but drops it on any other change (ADR-0010).
export function setParam(key, value, { drag = false } = {}) {
  config[key] = value;
  emit(drag);
}

export function applyPreset(partial) {
  Object.assign(config, partial);
  emit(false);
}

// --- share URL codec: only non-default values are written ---

// Bumped when a value's ENCODING changes meaning, so readUrl can tell a
// link written before the change from one written after. v2 moved the
// levyDeductionCap "uncapped" sentinel from 0 to negative, which made 0 a
// real value (the levy is not deductible) that four region bundles ship.
// v3 added mortgageInsuranceRatePct. A link carries only the values that
// differ from DEFAULT_CONFIG, so a v3 link without the key means the US
// default, but an older link without it says nothing about it: the value
// must come from the link's region instead, or, if the link matches no
// region, be the value that changes nothing (inputs.js).
const URL_SCHEMA_VERSION = "3";

// Keys a link older than v3 cannot carry, each with the value that leaves
// the model as it was before the key existed (inputs.js uses it when the
// link matches no region).
export const KEYS_ADDED_IN_V3 = { mortgageInsuranceRatePct: 0 };

// The KEYS_ADDED_IN_V3 that the link the page opened with was too old to
// carry. Set by readUrl.
let omittedKeys = new Set();

/** Whether the link the page opened with was too old to carry `key`. */
export function urlOmitted(key) {
  return omittedKeys.has(key);
}

// Which region the user picked is state in its own right, NOT something
// recoverable from the numbers. Reverse-matching a config against every
// bundle's taxPrimitives fails the moment any one of them is edited --
// and the Advanced inputs exist to be edited, with the bundle notes
// actively telling users to do it. When the match failed, the currency
// silently fell back to "$" and every modelling note vanished, so a
// GBP simulation rendered in dollars with none of its caveats.
//
// Kept OUT of `config`: the config object is posted to the API verbatim
// and api.py rejects unknown fields.
let regionId = null;

export function getRegionId() {
  return regionId;
}

export function setRegionId(id) {
  regionId = id;
  // Through the same delay as config changes: a region click applies the
  // bundle's numbers right after this, so an immediate write would put the
  // new region's id beside the old region's numbers for 300 ms.
  scheduleUrlWrite();
}

// Whether the first-time-buyer relief is on, while the selected region
// enacts one; null otherwise. Like `regionId` it is state the numbers
// cannot carry: once a relief value is edited, no config says whether
// the relief was on (#51). Kept out of `config` for the same reason.
// Adding it needed no new URL_SCHEMA_VERSION: no existing value changed
// meaning, and a link without it is still read by inference (inputs.js).
let ftb = null;

export function getFtb() {
  return ftb;
}

export function setFtb(on) {
  ftb = on;
  // Through the same delay as config changes, like setRegionId.
  scheduleUrlWrite();
}

function currentQuery() {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(config)) {
    if (value !== DEFAULT_CONFIG[key]) params.set(key, value);
  }
  if (regionId) params.set("r", regionId);
  if (ftb !== null) params.set("ftb", ftb ? "1" : "0");
  const qs = params.toString();
  return qs ? `?${qs}&v=${URL_SCHEMA_VERSION}` : "";
}

function writeUrl() {
  try {
    history.replaceState(null, "", currentQuery() || location.pathname);
  } catch {
    // Safari refuses history updates past 100 in 10 s. The link then lags
    // until the next write succeeds; nothing else depends on it.
  }
}

/**
 * An absolute link to the current scenario. Built from the live config,
 * so it is current even while the debounced address-bar write is pending.
 */
export function shareUrl() {
  return `${location.origin}${location.pathname}${currentQuery()}`;
}

// Per-field validation metadata derived from INPUT_DEFS (the single source
// of truth). Numeric ranges are expressed in stored units: INPUT_DEFS
// min/max are in displayed units, so divide by any `scale`.
const NUMERIC_RANGES = new Map();
const ALLOWED_VALUES = new Map();
for (const def of INPUT_DEFS) {
  if (def.type === "segmented") {
    ALLOWED_VALUES.set(def.key, new Set(def.options));
  } else if (def.type === "select") {
    ALLOWED_VALUES.set(def.key, new Set(def.options.map((opt) => opt[0])));
  } else if (def.min !== undefined) {
    const scale = def.scale ?? 1;
    NUMERIC_RANGES.set(def.key, { min: def.min / scale, max: def.max / scale });
  }
}

function isValidNumber(key, n) {
  const allowed = ALLOWED_VALUES.get(key);
  if (allowed) return allowed.has(n);
  const range = NUMERIC_RANGES.get(key);
  return !range || (n >= range.min && n <= range.max);
}

export function readUrl() {
  const params = new URLSearchParams(location.search);
  // A link with no version marker predates the sentinel move, so its
  // levyDeductionCap=0 still means "uncapped". A v2 link means what it
  // says: 0 is a real cap of zero, which FR/DE/NL/UK all ship. Without
  // this gate the migration would rewrite every European region link and
  // silently make that region's levy deductible.
  const isLegacy = !params.has("v");
  // A missing or unreadable version (v=abc) proves nothing, so the link
  // counts as older than v3: !(NaN >= 3) is true.
  const predatesV3 = !(Number(params.get("v")) >= 3);
  omittedKeys = new Set(
    predatesV3 ? Object.keys(KEYS_ADDED_IN_V3).filter((k) => !params.has(k)) : [],
  );
  // Validated against the real bundle list by inputs.js, which owns the
  // region data; an unknown id is dropped there.
  regionId = params.get("r");
  // Only 1 or 0 counts; anything else is read as a link without the
  // setting, so inputs.js infers it from the numbers.
  const ftbRaw = params.get("ftb");
  ftb = ftbRaw === "1" ? true : ftbRaw === "0" ? false : null;
  const restored = {};
  for (const [key, def] of Object.entries(DEFAULT_CONFIG)) {
    if (!params.has(key)) continue;
    const raw = params.get(key);
    if (isLegacy && key === "levyDeductionCap" && Number(raw) === 0) {
      // -1000 is the field's min and the canonical "no cap" value that
      // the levy choice stores, so the restored link matches a click.
      restored[key] = -1000; // uncapped, new encoding
      continue;
    }
    // Drop values outside the field's known range or allowed set so a
    // hand-edited share URL can't push an invalid config into the API.
    if (typeof def === "boolean") {
      restored[key] = raw === "true";
    } else if (typeof def === "number") {
      const n = Number(raw);
      if (!Number.isNaN(n) && isValidNumber(key, n)) restored[key] = n;
    } else {
      const allowed = ALLOWED_VALUES.get(key);
      if (!allowed || allowed.has(raw)) restored[key] = raw;
    }
  }
  if (Object.keys(restored).length > 0) {
    config = { ...DEFAULT_CONFIG, ...restored };
  }
}

// --- result cache, keyed by the serialized config ---

const cache = new Map();

export function configHash(cfg) {
  return JSON.stringify(cfg);
}

export function getCached(kind, hash) {
  return cache.get(hash)?.[kind];
}

export function setCached(kind, hash, value) {
  cache.set(hash, { ...cache.get(hash), [kind]: value });
}

export function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
