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
};

let config = { ...DEFAULT_CONFIG };
const listeners = [];

export function getConfig() {
  return { ...config };
}

export function onConfigChange(fn) {
  listeners.push(fn);
}

function emit() {
  writeUrl();
  for (const fn of listeners) fn(getConfig());
}

export function setParam(key, value) {
  config[key] = value;
  emit();
}

export function applyPreset(partial) {
  Object.assign(config, partial);
  emit();
}

// --- share URL codec: only non-default values are written ---

// Bumped when a value's ENCODING changes meaning, so readUrl can tell a
// link written before the change from one written after. v2 moved the
// levyDeductionCap "uncapped" sentinel from 0 to negative, which made 0 a
// real value (the levy is not deductible) that four region bundles ship.
const URL_SCHEMA_VERSION = "2";

function writeUrl() {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(config)) {
    if (value !== DEFAULT_CONFIG[key]) params.set(key, value);
  }
  const qs = params.toString();
  history.replaceState(
    null,
    "",
    qs ? `?${qs}&v=${URL_SCHEMA_VERSION}` : location.pathname,
  );
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
  const restored = {};
  for (const [key, def] of Object.entries(DEFAULT_CONFIG)) {
    if (!params.has(key)) continue;
    const raw = params.get(key);
    if (isLegacy && key === "levyDeductionCap" && Number(raw) === 0) {
      restored[key] = -1; // uncapped, new encoding
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