// Fetch wrappers for the simulation API. A NEGATIVE `levyDeductionCap` on
// the client means "uncapped"; the engine represents that as null. Zero
// means "the levy is not deductible at all" (NL), which is a real value.

export function serializeForWire(cfg) {
  return {
    ...cfg,
    levyDeductionCap: cfg.levyDeductionCap >= 0 ? cfg.levyDeductionCap : null,
  };
}

async function postJson(path, body, signal) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data.detail) {
        detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // keep default message
    }
    throw new Error(detail);
  }
  return res.json();
}

export function postSimulate(cfg, signal) {
  return postJson("/api/simulate", serializeForWire(cfg), signal);
}

export function postMonteCarlo(cfg, signal) {
  return postJson("/api/monte-carlo", serializeForWire(cfg), signal);
}

export async function getRegions() {
  const res = await fetch("/api/regions");
  if (!res.ok) throw new Error(`Regions request failed (${res.status})`);
  return res.json();
}