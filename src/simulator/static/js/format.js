// Number formatting shared by inputs and results.

// Currency is formatting only -- no FX, no conversion (ADR-0007). The
// engine is currency-agnostic; this is the single place the symbol lives.
let currencySymbol = "$";
let currencyLocale = "en-US";

export function setCurrency(symbol, locale = "en-US") {
  currencySymbol = symbol;
  currencyLocale = locale;
}

export function getCurrencySymbol() {
  return currencySymbol;
}

export function fmtMoney(v) {
  const sign = v < 0 ? "-" : "";
  return `${sign}${currencySymbol}${Math.round(Math.abs(v)).toLocaleString(currencyLocale)}`;
}

export function fmtCompact(v) {
  const sign = v < 0 ? "-" : "";
  const abs = Math.abs(v);
  if (abs >= 1_000_000)
    return `${sign}${currencySymbol}${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 10_000)
    return `${sign}${currencySymbol}${Math.round(abs / 1000)}k`;
  return fmtMoney(v);
}

export function fmtPct(v, digits = 1) {
  return `${v.toFixed(digits)}%`;
}