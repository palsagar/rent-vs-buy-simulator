// Chrome behavior: drawer, overlays, error banner, loading indicator.

export function initUi() {
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

  const welcome = document.getElementById("welcome-overlay");
  if (localStorage.getItem("rvb-welcomed")) welcome.classList.add("hidden");
  const dismiss = () => {
    localStorage.setItem("rvb-welcomed", "1");
    welcome.classList.add("hidden");
  };
  document.getElementById("welcome-start").addEventListener("click", dismiss);
  document.getElementById("welcome-close").addEventListener("click", dismiss);

  document.getElementById("inputs-btn").addEventListener("click", () => {
    document.getElementById("input-panel").classList.toggle("visible");
  });
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
