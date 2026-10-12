// Bootstrap and orchestration: config changes schedule a fast
// deterministic run and a slower Monte Carlo run, each debounced,
// aborted when superseded, and cached by config hash.

import { initAdvanced } from "./advanced.js";
import { getRegions, postMonteCarlo, postSimulate } from "./api.js";
import { initInputs, syncInputs } from "./inputs.js";
import { initPhoneLayout, initPresetBarFade } from "./layout.js";
import { initPrint } from "./print.js";
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
import {
  hideError,
  initErrorBanner,
  initUi,
  paintBusy,
  showError,
  showLinkNotice,
} from "./ui.js";

let simAbort = null;
let mcAbort = null;
let lastWinner = "rent";
let lastWinnerHash = null;
let simRun = null;
// Counts config changes that are not slider drags. A Monte Carlo run
// started before one judged a config the page has jumped away from, so it
// must not render: its toss-up call would carry over to the new result.
let jumps = 0;
// Each failed source holds { message, hash }: the error and the config
// hash it failed for (null for the regions request).
const errors = { simulate: null, monteCarlo: null, regions: null };
// Dismiss hides the banner until the next failure.
let bannerDismissed = false;
// The config hash each source last rendered.
const shown = { simulate: null, monteCarlo: null };

// One failure at a time, the one that matters most first: a simulate
// retry also re-runs Monte Carlo.
function syncBanner() {
  const source = ["simulate", "monteCarlo", "regions"].find((s) => errors[s]);
  if (!source || bannerDismissed) hideError();
  else showError(errors[source].message, source === "regions" ? "reload" : "retry", source);
}

function fail(source, message, hash) {
  errors[source] = { message, hash };
  bannerDismissed = false;
  syncBanner();
  syncBusy();
}

// Why a request failed, in words a visitor can act on.
function reason(err) {
  if (err.status === 503) return "the server is busy. Try again in a moment.";
  if (err instanceof TypeError) return "the connection dropped. Check you're online and try again.";
  return err.message;
}

// Monte Carlo alone is re-run for its own failure: the simulate result for
// the live config is already on screen.
function retry(source) {
  errors[source] = null;
  syncBanner();
  syncBusy();
  if (source === "simulate") runSimulate().then(runMonteCarlo);
  else if (source === "monteCarlo") runMonteCarlo();
}

function dismissError() {
  bannerDismissed = true;
  syncBanner();
}

// Which result sections are out of date for the live config, and whether
// a request that could update them is still possible.
function syncBusy() {
  const live = configHash(getConfig());
  const simFailed = errors.simulate?.hash === live;
  const mcFailed = simFailed || errors.monteCarlo?.hash === live;
  const simStale = shown.simulate !== live;
  const mcStale = shown.monteCarlo !== live;
  paintBusy({
    simulate: { stale: simStale, working: simStale && !simFailed },
    monteCarlo: { stale: mcStale, working: mcStale && !mcFailed },
    // The verdict on screen has no confidence yet, and one is still coming.
    checkingConfidence:
      shown.simulate !== null &&
      shown.monteCarlo !== shown.simulate &&
      !simFailed &&
      errors.monteCarlo?.hash !== shown.simulate,
  });
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
    shown.simulate = hash;
    errors.simulate = null;
    syncBanner();
    syncBusy();
    return;
  }
  const controller = new AbortController();
  simAbort = controller;
  simRun = (async () => {
    try {
      const data = await postSimulate(cfg, controller.signal);
      setCached("simulate", hash, data);
      if (simAbort !== controller) return;
      lastWinner = data.verdict.winner;
      lastWinnerHash = hash;
      renderSimulate(data, cfg);
      shown.simulate = hash;
      errors.simulate = null;
      syncBanner();
      syncBusy();
    } catch (err) {
      // A superseded/aborted request must never surface as the error banner:
      // the abort can reject as AbortError, but under a connection teardown
      // the same abort can surface as a generic TypeErrors, so gate on the
      // controller's own signal rather than the error's name. A genuinely
      // failed (non-aborted) request still shows the banner.
      if (!controller.signal.aborted && simAbort === controller) {
        fail("simulate", `Couldn't update the results: ${reason(err)}`, hash);
      }
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
        if (lastWinnerHash === hash && jumps === jumpsAtStart) {
          renderMonteCarlo(cached, lastWinner);
          shown.monteCarlo = hash;
        }
        syncBusy();
      }
      return;
    }
    const data = await postMonteCarlo(cfg, controller.signal);
    setCached("monteCarlo", hash, data);
    await simRun;
    if (mcAbort === controller) {
      errors.monteCarlo = null;
      syncBanner();
      if (lastWinnerHash === hash && jumps === jumpsAtStart) {
        renderMonteCarlo(data, lastWinner);
        shown.monteCarlo = hash;
      }
      syncBusy();
    }
  } catch (err) {
    if (!controller.signal.aborted && mcAbort === controller) {
      fail("monteCarlo", `Couldn't work out how sure the answer is: ${reason(err)}`, hash);
      // Repaint only the verdict this run was for, once its simulate run
      // has settled. If that run failed too, the verdict on screen is an
      // older one that still sits beside its own confidence, so it stays.
      await simRun;
      if (mcAbort === controller && lastWinnerHash === hash) clearTossUp();
    }
  }
}

const scheduleSimulate = debounce(runSimulate, 300);
const scheduleMonteCarlo = debounce(runMonteCarlo, 600);

async function init() {
  // First: the regions request below can already fail.
  initErrorBanner({ onRetry: retry, onDismiss: dismissError });
  const link = readUrl();
  const tour = new Tour({ steps: STEPS });
  window.__rvb = { tour }; // test handle for browser-driven verification
  // Before the regions request: the move needs only static markup, so phones
  // never show the controls in the preset bar and then see them jump.
  initPhoneLayout();
  let regions;
  try {
    regions = await getRegions();
  } catch {
    fail("regions", "Couldn't load the region settings, so the US defaults are shown.", null);
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
  // After initInputs: the pills set the bar's width.
  initPresetBarFade();
  // After initInputs: the groups reuse its builders and its region state.
  initAdvanced();
  initUi(tour, { sharedLink: link.shared });
  if (link.dropped.length) showLinkNotice(link.dropped);
  initPrint(regions);
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
    syncBusy();
  });
  syncBusy();
  await runSimulate();
  runMonteCarlo();
}

init();
