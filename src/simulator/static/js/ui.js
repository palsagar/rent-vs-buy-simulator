// Chrome behavior: drawer, overlays, error banner, busy state.
// Also owns the accessibility wiring for the overlays and drawer: focus
// management, dialog semantics, keyboard accordion, and scrim dismissal.

import { Tour, currentActiveTour } from "./tour.js";
import { trackEvent } from "./analytics.js";
import { moveFocusIn, restoreFocus, trapFocus } from "./focus.js";
import { INPUT_DEFS } from "./fields.js";
import { verdictIsCurrent } from "./results.js";
import { shareUrl } from "./state.js";

// A first visit through a link someone sent opens on their scenario:
// viewing it is the main action and the tour the second. The buttons keep
// their ids and handlers, so View still marks the welcome as skipped.
function applySharedWelcome(welcome) {
  welcome.querySelector("h1").textContent = "Someone shared a scenario with you";
  welcome.querySelector(".welcome-hero-sub").textContent = "Their numbers are already filled in";
  welcome.querySelector(".welcome-intro").textContent =
    "This calculator compares buying a home with renting and investing the difference. " +
    "The answer for their numbers is ready below. " +
    "Change any number to try your own.";
  const view = document.getElementById("start-sim-btn");
  const tourBtn = document.getElementById("start-tour-btn");
  view.textContent = "View this shared scenario";
  view.className = "btn-primary";
  tourBtn.textContent = "Take the tour first";
  tourBtn.className = "btn";
  tourBtn.before(view);
}

// `sharedLink`: the page opened on a link that sets its own numbers.
export function initUi(tour, { sharedLink = false } = {}) {
  // Desktop only: on a phone the preset bar is hidden, and the groups sit
  // in the inputs sheet right below the outlook section.
  document.getElementById("advanced-btn").addEventListener("click", () => {
    const section = document.getElementById("advanced-section");
    section.scrollIntoView({ block: "start" });
    section.querySelector("summary")?.focus({ preventScroll: true });
  });

  // ── Guide overlay ────────────────────────────────────────────────────────
  const guide = document.getElementById("guide-overlay");
  const guideCloseBtn = guide.querySelector(".modal-close");
  const guideTitle = guide.querySelector("h1");
  if (guideTitle && !guideTitle.id) guideTitle.id = "guide-title";
  guide.setAttribute("role", "dialog");
  guide.setAttribute("aria-modal", "true");
  guide.setAttribute("aria-labelledby", "guide-title");
  let guideActive = false;
  let releaseGuideTrap = null;
  let guideLauncher = null;

  function closeGuide() {
    if (!guideActive) return;
    guideActive = false;
    releaseGuideTrap?.();
    releaseGuideTrap = null;
    guide.classList.add("hidden");
    restoreFocus(guideLauncher);
  }
  function openGuide() {
    // Single-active-modal rule: never stack a second document-level focus trap
    // on a live one. End WHATEVER tour is running (the canonical one wired by
    // main.js, or a programmatic instance) first — that releases its trap and
    // tears its overlay down — so the guide never renders beneath the tour's
    // dims with two traps live.
    const running = currentActiveTour();
    if (running) running.skip();
    guideActive = true;
    guideLauncher = document.activeElement;
    guide.classList.remove("hidden");
    // Focus the close button and keep Tab cycling inside the dialog.
    if (releaseGuideTrap) releaseGuideTrap();
    releaseGuideTrap = trapFocus(guide);
    moveFocusIn(guide, guideCloseBtn);
  }

  document.getElementById("guide-btn").addEventListener("click", openGuide);
  guideCloseBtn.addEventListener("click", closeGuide);
  guide.addEventListener("click", (e) => {
    if (e.target === guide) closeGuide();
  });

  // Accordion: mouse + keyboard toggle, kept in the tab order, with the
  // accessible state mirrored on aria-expanded. A11Y-05 keeps the
  // toggle-per-section (multiple-open) model — this just makes it operable.
  const guideSections = guide.querySelectorAll(".guide-section");
  const toggleGuideSection = (header) => {
    const section = header.parentElement;
    const body = section.querySelector(".guide-section-body");
    if (body && !body.id) body.id = `guide-section-${Array.from(guideSections).indexOf(section)}`;
    header.setAttribute("aria-controls", body.id);
    const open = section.classList.toggle("open");
    header.setAttribute("aria-expanded", String(open));
  };
  guideSections.forEach((section) => {
    const header = section.querySelector(".guide-section-header");
    if (!header) return;
    // Keyboard-operable regardless of markup: nothing to do if F-A already
    // made it focusable, ensure it is if not.
    if (typeof header.tabIndex !== "number" || header.tabIndex < 0) header.tabIndex = 0;
    if (!header.hasAttribute("role")) header.setAttribute("role", "button");
    header.setAttribute("aria-expanded", section.classList.contains("open") ? "true" : "false");
    header.addEventListener("click", () => toggleGuideSection(header));
    header.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleGuideSection(header);
      }
    });
  });

  document.getElementById("btn-replay-tour").addEventListener("click", () => {
    // Tour owns focus from here: release the guide trap without restoring,
    // so start() captures #btn-replay-tour as its launcher.
    if (guideActive) {
      guideActive = false;
      releaseGuideTrap?.();
      releaseGuideTrap = null;
      guide.classList.add("hidden");
    }
    tour.start();
  });

  // ── Welcome overlay ──────────────────────────────────────────────────────
  const welcome = document.getElementById("welcome-overlay");
  const welcomeTitleEl = welcome.querySelector("h1");
  if (welcomeTitleEl && !welcomeTitleEl.id) welcomeTitleEl.id = "welcome-title";
  welcome.setAttribute("role", "dialog");
  welcome.setAttribute("aria-modal", "true");
  welcome.setAttribute("aria-labelledby", "welcome-title");
  let welcomeActive = false;
  let releaseWelcomeTrap = null;

  const dismissWelcome = () => {
    if (!welcomeActive) return;
    welcomeActive = false;
    releaseWelcomeTrap?.();
    releaseWelcomeTrap = null;
    welcome.classList.add("hidden");
  };
  if (sharedLink) applySharedWelcome(welcome);
  // First visit only: returning visitors hold the tour flag. Markup starts
  // hidden and JS reveals it, so no inline script is needed (CSP-safe).
  if (!Tour.readFlag()) {
    welcomeActive = true;
    welcome.classList.remove("hidden");
    releaseWelcomeTrap = trapFocus(welcome);
    moveFocusIn(welcome, document.getElementById(sharedLink ? "start-sim-btn" : "start-tour-btn"));
  }
  document.getElementById("start-tour-btn").addEventListener("click", () => {
    dismissWelcome();
    tour.start();
  });
  const skipWelcome = () => {
    Tour.writeFlag("skipped");
    dismissWelcome();
  };
  document.getElementById("start-sim-btn").addEventListener("click", skipWelcome);
  document.getElementById("welcome-close").addEventListener("click", () => {
    skipWelcome();
    restoreFocus(document.getElementById("start-sim-btn"));
  });
  document.getElementById("open-guide-from-welcome").addEventListener("click", (e) => {
    e.preventDefault();
    skipWelcome();
    // Let the welcome fade finish before the guide fades in.
    setTimeout(openGuide, 350);
  });

  // ── Inputs drawer + scrim ────────────────────────────────────────────────
  const inputPanel = document.getElementById("input-panel");
  // Resolved lazily so the scrim (added by F-A in index.html/style.css) is
  // picked up whenever it appears, and its absence never breaks the drawer.
  const scrim = () => document.getElementById("drawer-scrim");
  const setDrawer = (open) => {
    inputPanel.classList.toggle("visible", open);
    const s = scrim();
    if (s) s.classList.toggle("hidden", !open);
  };
  // While the sheet is open its own live verdict line speaks, so the hero's
  // would say the same thing twice. Watched, not set in setDrawer: the tour
  // and the phone layout also open and close the sheet.
  const syncHeroLive = () => {
    const live = inputPanel.classList.contains("visible") ? "off" : "polite";
    for (const id of ["verdict-line", "verdict-confidence"]) {
      document.getElementById(id).setAttribute("aria-live", live);
    }
  };
  new MutationObserver(syncHeroLive).observe(inputPanel, { attributes: true, attributeFilter: ["class"] });
  // Done, Esc and a tap outside close the phone inputs sheet. After Esc,
  // focus that was in the sheet goes to the button that reopens it, not
  // off-screen.
  const closeSheets = (returnFocus) => {
    const focusInSheet = inputPanel.contains(document.activeElement);
    setDrawer(false);
    if (returnFocus && focusInSheet) document.getElementById("inputs-btn").focus();
  };
  document.getElementById("inputs-btn").addEventListener("click", (e) => {
    const open = !inputPanel.classList.contains("visible");
    setDrawer(open);
    if (open && e.isTrusted) trackEvent("inputs-opened");
  });
  // Done always sits in the sheet it closes, so focus always goes back to the
  // Edit button, even where a tap does not focus Done (WebKit, iOS Safari).
  document.getElementById("sheet-done").addEventListener("click", () => {
    closeSheets(false);
    document.getElementById("inputs-btn").focus();
  });
  // The scrim only shows on phones.
  document.addEventListener("click", (e) => {
    if (e.target && e.target.id === "drawer-scrim") closeSheets(false);
  });
  // Esc closes both phone sheets and the scrim, and returns focus that was in
  // a sheet to the Edit your numbers button. Only fires when the inputs sheet
  // is actually the open mobile surface, so it can't clobber the tour's own
  // Escape handling.
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && inputPanel.classList.contains("visible")) {
      const mobile = window.getComputedStyle(document.getElementById("inputs-btn")).display !== "none";
      if (mobile) closeSheets(true);
    }
  });

  // ── Share ────────────────────────────────────────────────────────────────
  // The native share sheet wherever the browser has one (phones, but also
  // desktop Safari and Edge or Chrome on Windows), else copy the link.
  const shareBtn = document.getElementById("share-btn");
  const shareLabel = shareBtn.textContent;
  // One timer: a second copy restarts the two seconds instead of letting
  // the first copy's timer put the label back early.
  let shareLabelTimer = null;
  shareBtn.addEventListener("click", async (e) => {
    if (e.isTrusted) trackEvent("link-shared");
    const url = shareUrl();
    if (navigator.share) {
      // The link is always the live config; the verdict on screen can still
      // be the previous one (loading, or its request failed). Send it only
      // when it matches the link.
      const data = { title: "Rent or buy?", url };
      if (verdictIsCurrent()) data.text = document.getElementById("verdict-line").textContent;
      try {
        await navigator.share(data);
        return;
      } catch (err) {
        // AbortError means the person closed the share sheet. Any other
        // failure falls through to copying the link.
        if (err.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      shareBtn.textContent = "Link copied";
    } catch {
      shareBtn.textContent = "Copy the link from the address bar";
    }
    clearTimeout(shareLabelTimer);
    shareLabelTimer = setTimeout(() => {
      shareBtn.textContent = shareLabel;
    }, 2000);
  });
}

// A link value the calculator cannot use falls back to its starting value;
// this says which ones did. `keys` are config keys, or `ftb`.
export function showLinkNotice(keys) {
  // `ftb` is not a field: it is the first-time-buyer pill.
  const label = (key) => (key === "ftb" ? "First-time buyer" : INPUT_DEFS.find((d) => d.key === key)?.label ?? key);
  const labels = [...new Set(keys.map(label))];
  document.getElementById("link-notice-text").textContent =
    labels.length === 1
      ? `One value in this link was outside what the calculator allows, so ${labels[0]} uses the starting value instead.`
      : `Some values in this link were outside what the calculator allows, so these use the starting values instead: ${labels.join(", ")}.`;
  const notice = document.getElementById("link-notice");
  notice.hidden = false;
  document.getElementById("link-notice-dismiss").addEventListener("click", () => {
    notice.hidden = true;
  });
}

// The source of the failure the banner shows: what Try again re-runs.
let bannerSource = null;

// Wired here (not inline onclick) so the CSP script-src can omit 'unsafe-inline'.
export function initErrorBanner({ onRetry, onDismiss }) {
  const banner = document.getElementById("error-banner");
  // Focus on a button the banner just hid would be lost, so it moves to
  // the results the banner was about.
  const leaveBanner = () => {
    if (!banner.classList.contains("visible") && banner.contains(document.activeElement)) {
      document.getElementById("verdict-hero").focus({ preventScroll: true });
    }
  };
  document.getElementById("error-retry").addEventListener("click", (e) => {
    if (e.isTrusted) {
      trackEvent("error-retried", { source: bannerSource === "monteCarlo" ? "monte-carlo" : "simulate" });
    }
    onRetry(bannerSource);
    leaveBanner();
  });
  document.getElementById("error-reload").addEventListener("click", () => location.reload());
  document.getElementById("error-dismiss").addEventListener("click", () => {
    onDismiss();
    leaveBanner();
  });
}

// `action` is "retry" or "reload": the one fix the banner offers.
export function showError(message, action, source) {
  bannerSource = source;
  // Shown first, then filled: an alert is announced when its text changes.
  document.getElementById("error-banner").classList.add("visible");
  document.getElementById("error-message").textContent = message;
  document.getElementById("error-retry").hidden = action !== "retry";
  document.getElementById("error-reload").hidden = action !== "reload";
}

export function hideError() {
  document.getElementById("error-banner").classList.remove("visible");
  // Emptied, so the same message is announced again next time.
  document.getElementById("error-message").textContent = "";
}

// Fades the out-of-date result sections, marks the ones still updating as
// busy, and shows the Updating chip while any update can still land.
export function paintBusy({ simulate, monteCarlo, checkingConfidence }) {
  for (const el of document.querySelectorAll("[data-result]")) {
    const s = el.dataset.result === "simulate" ? simulate : monteCarlo;
    el.classList.toggle("stale", s.stale);
    el.setAttribute("aria-busy", String(s.working));
  }
  document
    .getElementById("results-spinner")
    .classList.toggle("visible", simulate.working || monteCarlo.working);
  document.getElementById("verdict-pending").hidden = !checkingConfidence;
}
