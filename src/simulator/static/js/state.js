// Central config state, share-URL codec, debounce, and result cache.

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

function writeUrl() {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(config)) {
    if (value !== DEFAULT_CONFIG[key]) params.set(key, value);
  }
  const qs = params.toString();
  history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
}

export function readUrl() {
  const params = new URLSearchParams(location.search);
  const restored = {};
  for (const [key, def] of Object.entries(DEFAULT_CONFIG)) {
    if (!params.has(key)) continue;
    const raw = params.get(key);
    if (typeof def === "boolean") {
      restored[key] = raw === "true";
    } else if (typeof def === "number") {
      const n = Number(raw);
      if (!Number.isNaN(n)) restored[key] = n;
    } else {
      restored[key] = raw;
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