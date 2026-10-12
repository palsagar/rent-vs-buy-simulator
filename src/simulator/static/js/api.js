// Fetch wrappers for the simulation API. A NEGATIVE `levyDeductionCap` on
// the client means "uncapped"; the engine represents that as null. Zero
// means "the levy is not deductible at all" (NL), which is a real value.
// A failed request rejects with an Error carrying the HTTP `status`.

export function serializeForWire(cfg) {
  return {
    ...cfg,
    levyDeductionCap: cfg.levyDeductionCap >= 0 ? cfg.levyDeductionCap : null,
  };
}

async function postOnce(path, body, signal) {
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
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

// A busy server (HTTP 503, e.g. every Monte Carlo slot taken) is asked
// again after a short wait; the caller's abort ends the wait at once.
const BUSY_RETRY_DELAYS_MS = [1000, 2000, 4000];

function wait(ms, signal) {
  return new Promise((resolve, reject) => {
    const abort = () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", abort);
      resolve();
    }, ms);
    if (signal?.aborted) abort();
    else signal?.addEventListener("abort", abort, { once: true });
  });
}

async function postJson(path, body, signal) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await postOnce(path, body, signal);
    } catch (err) {
      if (err.status !== 503 || signal?.aborted || attempt >= BUSY_RETRY_DELAYS_MS.length) throw err;
      // Up to 25% either way, so clients turned away together do not all
      // come back at the same moment.
      await wait(BUSY_RETRY_DELAYS_MS[attempt] * (0.75 + Math.random() / 2), signal);
    }
  }
}

export function postSimulate(cfg, signal) {
  return postJson("/api/simulate", serializeForWire(cfg), signal);
}

export function postMonteCarlo(cfg, signal) {
  return postJson("/api/monte-carlo", serializeForWire(cfg), signal);
}

export async function getRegions() {
  const res = await fetch("/api/regions");
  if (!res.ok) {
    const err = new Error(`Regions request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}
