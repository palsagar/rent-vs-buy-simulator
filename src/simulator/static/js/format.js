// Number formatting shared by inputs, results and charts.

// U+2212 MINUS, not an ASCII hyphen. Plotly emits U+2212 on axis ticks
// and offers no way to change it, so every other money label in the app
// is built from the same glyph rather than leaving a hyphen sitting
// beside a minus in the same hover. Exported because charts.js pre-
// formats Plotly hover values -- d3-format hardcodes an ASCII hyphen
// and the locale's `minus` key reaches ticks only (verified on 2.35.2).
export const MINUS = "\u2212";

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
  const sign = v < 0 ? MINUS : "";
  return `${sign}${currencySymbol}${Math.round(Math.abs(v)).toLocaleString(currencyLocale)}`;
}

export function fmtCompact(v) {
  const sign = v < 0 ? MINUS : "";
  const abs = Math.abs(v);
  if (abs >= 1_000_000)
    return `${sign}${currencySymbol}${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 10_000)
    return `${sign}${currencySymbol}${Math.round(abs / 1000)}k`;
  return fmtMoney(v);
}

export function fmtPct(v, digits = 1) {
  // toFixed emits an ASCII hyphen. Rates share hovers and slider rows
  // with money, so they take the same sign glyph.
  const sign = v < 0 ? MINUS : "";
  return `${sign}${Math.abs(v).toFixed(digits)}%`;
}