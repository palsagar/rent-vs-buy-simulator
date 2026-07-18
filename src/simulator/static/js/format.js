// Number formatting shared by inputs and results.

export function fmtMoney(v) {
  const sign = v < 0 ? "-" : "";
  return `${sign}$${Math.round(Math.abs(v)).toLocaleString("en-US")}`;
}

export function fmtCompact(v) {
  const sign = v < 0 ? "-" : "";
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 10_000) return `${sign}$${Math.round(abs / 1000)}k`;
  return fmtMoney(v);
}

export function fmtPct(v, digits = 1) {
  return `${v.toFixed(digits)}%`;
}