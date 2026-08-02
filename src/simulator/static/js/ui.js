// Chrome behavior: drawer, overlays, error banner, loading indicator.

import { Tour } from "./tour.js";

export function initUi(tour) {
  const panel = document.getElementById("advanced-panel");
  document.getElementById("advanced-btn").addEventListener("click", () => panel.classList.toggle("visible"));
  document.getElementById("advanced-close").addEventListener("click", () => panel.classList.remove("visible"));

  const guide = document.getElementById("guide-overlay");
  document.getElementById("guide-btn").addEventListener("click", () => guide.classList.remove("hidden"));
  guide.querySelector(".modal-close").addEventListener("click", () => guide.classList.add("hidden"));
  guide.addEventListener("click", (e) => {
    if (e.target === guide) guide.classList.add("hidden");
  });
  for (const header of guide.querySelectorAll(".guide-section-header")) {
    header.addEventListener("click", () => header.parentElement.classList.toggle("open"));
  }
  document.getElementById("btn-replay-tour").addEventListener("click", () => tour.start());

  const welcome = document.getElementById("welcome-overlay");
  const dismissWelcome = () => welcome.classList.add("hidden");
  // First visit only: returning visitors hold the tour flag. Markup starts
  // hidden and JS reveals it, so no inline script is needed (CSP-safe).
  if (!Tour.readFlag()) welcome.classList.remove("hidden");
  document.getElementById("start-tour-btn").addEventListener("click", () => {
    dismissWelcome();
    tour.start();
  });
  const skipWelcome = () => {
    Tour.writeFlag("skipped");
    dismissWelcome();
  };
  document.getElementById("start-sim-btn").addEventListener("click", skipWelcome);
  document.getElementById("welcome-close").addEventListener("click", skipWelcome);
  document.getElementById("open-guide-from-welcome").addEventListener("click", (e) => {
    e.preventDefault();
    skipWelcome();
    // Let the welcome fade finish before the guide fades in.
    setTimeout(() => guide.classList.remove("hidden"), 350);
  });

  document.getElementById("inputs-btn").addEventListener("click", () => {
    document.getElementById("input-panel").classList.toggle("visible");
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
