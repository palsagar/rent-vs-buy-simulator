// Chrome behavior: drawer, overlays, error banner, loading indicator.
// Also owns the accessibility wiring for the overlays and drawer: focus
// management, dialog semantics, keyboard accordion, and scrim dismissal.

import { Tour, currentActiveTour } from "./tour.js";
import { moveFocusIn, restoreFocus, trapFocus } from "./focus.js";

export function initUi(tour) {
  const panel = document.getElementById("advanced-panel");
  document.getElementById("advanced-btn").addEventListener("click", () => panel.classList.toggle("visible"));
  const advancedClose = document.getElementById("advanced-close");
  advancedClose.addEventListener("click", () => {
    panel.classList.remove("visible");
    // On a phone the close button slides off-screen with the sheet; the
    // Advanced button that opened it stays in view in the inputs sheet.
    const mobile = window.getComputedStyle(document.getElementById("inputs-btn")).display !== "none";
    if (mobile && document.activeElement === advancedClose) document.getElementById("advanced-btn").focus();
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
  // First visit only: returning visitors hold the tour flag. Markup starts
  // hidden and JS reveals it, so no inline script is needed (CSP-safe).
  if (!Tour.readFlag()) {
    welcomeActive = true;
    welcome.classList.remove("hidden");
    releaseWelcomeTrap = trapFocus(welcome);
    moveFocusIn(welcome, document.getElementById("start-tour-btn"));
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
  // On a phone the Advanced sheet opens on top of the inputs sheet, so Done,
  // Esc and a tap outside them close both. After Done or Esc, focus that was
  // in a sheet goes to the button that reopens it, not off-screen.
  const closeSheets = (returnFocus) => {
    const active = document.activeElement;
    const focusInSheet = inputPanel.contains(active) || panel.contains(active);
    setDrawer(false);
    panel.classList.remove("visible");
    if (returnFocus && focusInSheet) document.getElementById("inputs-btn").focus();
  };
  document.getElementById("inputs-btn").addEventListener("click", () => setDrawer(!inputPanel.classList.contains("visible")));
  document.getElementById("sheet-done").addEventListener("click", () => closeSheets(true));
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

  // Wired here (not inline onclick) so the CSP script-src can omit 'unsafe-inline'.
  document.getElementById("error-reload").addEventListener("click", () => location.reload());
}

export function showError(message) {
  const banner = document.getElementById("error-banner");
  banner.querySelector("span").textContent = message;
  banner.classList.add("visible");
}

export function hideError() {
  document.getElementById("error-banner").classList.remove("visible");
}

export function setLoading(on) {
  document.getElementById("results-spinner").style.display = on ? "flex" : "none";
}
