// Bootstrap and orchestration: config changes schedule a fast
// deterministic run and a slower Monte Carlo run, each debounced,
// aborted when superseded, and cached by config hash.

import { getRegions, postMonteCarlo, postSimulate } from "./api.js";
import { initInputs, syncInputs } from "./inputs.js";
import { initPhoneLayout } from "./layout.js";
import {
  clearTossUp,
  forgetTossUp,
  renderMonteCarlo,
  renderSimulate,
} from "./results.js";
import {
  configHash,
  debounce,
  getCached,
  getConfig,
  onConfigChange,
  readUrl,
  setCached,
} from "./state.js";
import { Tour, STEPS } from "./tour.js";
import { hideError, initUi, setLoading, showError } from "./ui.js";

let simAbort = null;
let mcAbort = null;
let lastWinner = "rent";
let lastWinnerHash = null;
let simRun = null;
// Counts config changes that are not slider drags. A Monte Carlo run
// started before one judged a config the page has jumped away from, so it
// must not render: its toss-up call would carry over to the new result.
let jumps = 0;
const errors = { simulate: null, monteCarlo: null };

function syncBanner() {
  const message = errors.simulate ?? errors.monteCarlo;
  if (message) showError(message);
  else hideError();
}

async function runSimulate() {
  simAbort?.abort();
  const cfg = getConfig();
  const hash = configHash(cfg);
  const cached = getCached("simulate", hash);
  if (cached) {
    lastWinner = cached.verdict.winner;
    lastWinnerHash = hash;
    renderSimulate(cached, cfg);
    errors.simulate = null;
    syncBanner();
    return;
  }
  const controller = new AbortController();
  simAbort = controller;
  setLoading(true);
  simRun = (async () => {
    try {
      const data = await postSimulate(cfg, controller.signal);
      setCached("simulate", hash, data);
      if (simAbort !== controller) return;
      lastWinner = data.verdict.winner;
      lastWinnerHash = hash;
      renderSimulate(data, cfg);
      errors.simulate = null;
      syncBanner();
    } catch (err) {
      // A superseded/aborted request must never surface as the error banner:
      // the abort can reject as AbortError, but under a connection teardown
      // the same abort can surface as a generic TypeErrors, so gate on the
      // controller's own signal rather than the error's name. A genuinely
      // failed (non-aborted) request still shows the banner.
      if (!controller.signal.aborted && simAbort === controller) {
        errors.simulate = `Simulation failed: ${err.message}`;
        syncBanner();
      }
    } finally {
      if (simAbort === controller) setLoading(false);
    }
  })();
  await simRun;
}

async function runMonteCarlo() {
  const cfg = getConfig();
  const hash = configHash(cfg);
  const jumpsAtStart = jumps;
  mcAbort?.abort();
  const controller = new AbortController();
  mcAbort = controller;
  const cached = getCached("monteCarlo", hash);
  // Ordering contract: Monte Carlo only renders when its config hash matches
  // the last simulate winner (lastWinnerHash === hash). lastWinnerHash and
  // lastWinner are set as a side effect of the simulate path, and simRun is
  // awaited to ensure that path has settled first. Changing the hashing or
  // the simulate cache logic can therefore silently suppress MC rendering.
  // A change that is not a drag (see `jumps`) also suppresses it.
  try {
    if (cached) {
      await simRun;
      if (mcAbort === controller) {
        errors.monteCarlo = null;
        syncBanner();
        if (lastWinnerHash === hash && jumps === jumpsAtStart) renderMonteCarlo(cached, lastWinner);
      }
      return;
    }
    const data = await postMonteCarlo(cfg, controller.signal);
    setCached("monteCarlo", hash, data);
    await simRun;
    if (mcAbort === controller) {
      errors.monteCarlo = null;
      syncBanner();
      if (lastWinnerHash === hash && jumps === jumpsAtStart) renderMonteCarlo(data, lastWinner);
    }
  } catch (err) {
    if (!controller.signal.aborted && mcAbort === controller) {
      errors.monteCarlo = `Monte Carlo failed: ${err.message}`;
      syncBanner();
      clearTossUp();
    }
  }
}

const scheduleSimulate = debounce(runSimulate, 300);
const scheduleMonteCarlo = debounce(runMonteCarlo, 600);

async function init() {
  readUrl();
  const tour = new Tour({ steps: STEPS });
  window.__rvb = { tour }; // test handle for browser-driven verification
  // Before the regions request: the move needs only static markup, so phones
  // never show the controls in the preset bar and then see them jump.
  initPhoneLayout();
  let regions;
  try {
    regions = await getRegions();
  } catch (err) {
    showError(`Could not load regions: ${err.message}`);
    // currencySymbol is not optional: it reaches setCurrency, and from
    // there every money label in the app -- including the Plotly locale
    // the charts register. Omitting it rendered axis ticks as
    // "undefined500k". It must match regions.py's US symbol, since this
    // stands in for that region.
    regions = [
      {
        id: "us",
        label: "United States",
        available: true,
        currencySymbol: "$",
        typical: {},
        taxPrimitives: {},
      },
    ];
  }
  initInputs(regions);
  initUi(tour);
  syncInputs();
  onConfigChange((_cfg, { drag }) => {
    // Only a slider drag keeps the toss-up wording until Monte Carlo
    // reports (ADR-0010).
    if (!drag) {
      jumps += 1;
      forgetTossUp();
    }
    scheduleSimulate();
    scheduleMonteCarlo();
  });
  await runSimulate();
  runMonteCarlo();
}

init();
