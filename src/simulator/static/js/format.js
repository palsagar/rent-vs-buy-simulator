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
 * Ignores currency symbols, spaces and "%" and accepts U+2212 (minus),
 * U+2012 (figure dash) and U+2013 (en dash) as a minus.
 * Separators: when both "," and "." appear, the later one is the decimal
 * point ("1.234,5", "1,234.5"). When only one kind appears, more than one
 * of it is digit grouping ("1.234.567"). A single one is the decimal point
 * ("6,5", "7.5") -- the iOS decimal keypad shows "," in most European
 * locales -- except in a whole-number field when exactly three digits
 * follow it and no "k" or "M" does, where it is digit grouping ("437,000",
 * "437.000"; "1.250M" is 1.25 million). Digit grouping must split the
 * whole part into threes after a first group of one to three digits, so
 * "1.23.4", "1234,000", ".500" and "1,000," are unreadable. A lone
 * separator at either end that is the decimal point still reads (".5",
 * "5.", "1,000."). A whole-number field rounds the result ("7.5" gives
 * 8). A trailing "k" or "M" (either case) multiplies by a thousand or a
 * million, before that rounding ("450k", "1.5M", "2,5k"). Returns NaN when any other letter is left ("12abc", "1e5"),
 * when two separators touch ("5..0", "1,,000"), when the grouping is
 * malformed, or when nothing numeric is left.
 */
export function parseTypedNumber(text, integerField) {
  let s = String(text)
    .replace(/[\u2012\u2013\u2212]/g, "-")
    .replace(/[^\d.,\p{L}-]/gu, "");
  let multiplier = 1;
  const suffix = s.slice(-1).toLowerCase();
  if (suffix === "k" || suffix === "m") {
    multiplier = suffix === "k" ? 1_000 : 1_000_000;
    s = s.slice(0, -1);
  }
  if (/\p{L}/u.test(s) || /[.,]{2}/.test(s)) return NaN;
  const lastDot = s.lastIndexOf(".");
  const lastComma = s.lastIndexOf(",");
  let decimal = null;
  let group = null;
  if (lastDot >= 0 && lastComma >= 0) {
    decimal = lastComma > lastDot ? "," : ".";
    group = decimal === "," ? "." : ",";
  } else if (lastDot >= 0 || lastComma >= 0) {
    const at = Math.max(lastDot, lastComma);
    const sep = s[at];
    const count = s.split(sep).length - 1;
    const grouping =
      count > 1 ||
      (integerField && multiplier === 1 && /^\d{3}$/.test(s.slice(at + 1)));
    if (grouping) group = sep;
    else decimal = sep;
  }
  if (group) {
    // Grouping splits the whole part into threes: "1.234.567", not "1.23.4".
    const whole = decimal ? s.slice(0, s.lastIndexOf(decimal)) : s;
    const [first, ...rest] = whole.replace(/^-/, "").split(group);
    if (!/^\d{1,3}$/.test(first) || !rest.every((g) => /^\d{3}$/.test(g))) return NaN;
    s = s.split(group).join("");
  }
  if (decimal) s = s.replace(decimal, ".");
  if (s === "" || s === "-") return NaN;
  const n = Number(s) * multiplier;
  return integerField ? Math.round(n) : n;
}