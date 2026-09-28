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

/**
 * Parse a number typed into a slider's exact-value field.
 *
 * Ignores currency symbols, spaces and "%" and accepts U+2212 as a minus.
 * Separators: when both "," and "." appear, the later one is the decimal
 * point ("1.234,5", "1,234.5"). When only one kind appears, more than one
 * of it is digit grouping ("1.234.567"). A single one is the decimal point
 * ("6,5", "7.5") -- the iOS decimal keypad shows "," in most European
 * locales -- except in a whole-number field when exactly three digits
 * follow it, where it is digit grouping ("437,000", "437.000"). A
 * whole-number field rounds the result ("7.5" gives 8). A trailing "k"
 * or "M" (either case) multiplies by a thousand or a million, before that
 * rounding ("450k", "1.5M", "2,5k"). Returns NaN when any other letter
 * is left ("12abc", "1e5") or when nothing numeric is left.
 */
export function parseTypedNumber(text, integerField) {
  let s = String(text)
    .replaceAll(MINUS, "-")
    .replace(/[^\d.,\p{L}-]/gu, "");
  let multiplier = 1;
  const suffix = s.slice(-1).toLowerCase();
  if (suffix === "k" || suffix === "m") {
    multiplier = suffix === "k" ? 1_000 : 1_000_000;
    s = s.slice(0, -1);
  }
  if (/\p{L}/u.test(s)) return NaN;
  const lastDot = s.lastIndexOf(".");
  const lastComma = s.lastIndexOf(",");
  if (lastDot >= 0 && lastComma >= 0) {
    const decimal = lastComma > lastDot ? "," : ".";
    s = s.split(decimal === "," ? "." : ",").join("").replace(decimal, ".");
  } else if (lastDot >= 0 || lastComma >= 0) {
    const at = Math.max(lastDot, lastComma);
    const sep = s[at];
    const count = s.split(sep).length - 1;
    const grouping =
      count > 1 || (integerField && /^\d{3}$/.test(s.slice(at + 1)));
    s = grouping ? s.split(sep).join("") : s.replace(sep, ".");
  }
  if (s === "" || s === "-") return NaN;
  const n = Number(s) * multiplier;
  return integerField ? Math.round(n) : n;
}