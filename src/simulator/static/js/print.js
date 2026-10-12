// Printing (Ctrl/Cmd+P): fills the print-only "Your numbers" summary, opens
// the region caveats, and lays the charts out at paper width so their text
// prints at a readable size. Everything goes back after printing. The light
// colours come from the @media print block in style.css.

import { changedFromRegion } from "./advanced.js";
import { trackEvent } from "./analytics.js";
import { INPUT_DEFS } from "./fields.js";
import { regionDefaults } from "./inputs.js";
import { redrawCharts, shownScenario, verdictIsCurrent } from "./results.js";
import { getConfig, getFtb, getRegionId, shareUrl } from "./state.js";

// About the width of an A4 or Letter page inside the default margins, less
// the card's padding.
const PRINT_CHART_PX = 640;

/** A stored value as the summary prints it. */
function formatValue(def, stored) {
  if (def.type === "segmented") return `${stored} yrs`;
  if (def.type === "select") return def.options.find(([value]) => value === stored)?.[1] ?? String(stored);
  if (def.type === "checkbox") return stored ? "Yes" : "No";
  return def.fmt(stored * (def.scale ?? 1));
}

// The printed numbers are the ones the printed results were computed for,
// which differ from the live ones while a change is updating or after it
// failed (the page then also says so).
function fillSummary(regions) {
  const shown = shownScenario() ?? { cfg: getConfig(), regionId: getRegionId(), ftb: getFtb() };
  const { cfg } = shown;
  document.getElementById("print-stale").hidden = verdictIsCurrent();
  const list = document.getElementById("print-summary-list");
  list.replaceChildren();
  const row = (label, value) => {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value;
    list.append(dt, dd);
  };
  const region = regions.find((r) => r.id === shown.regionId);
  if (region) row("Region", region.label);
  for (const def of INPUT_DEFS) {
    if (def.section !== "advanced") row(def.label, formatValue(def, cfg[def.key]));
  }
  // Only what differs from the region; with no region, every Advanced value.
  // A field another field switches off is hidden on screen and does not
  // count, so it is not printed either. The live region's defaults only
  // describe results computed in that region with that relief setting.
  const sameRegion = shown.regionId === getRegionId() && shown.ftb === getFtb();
  const defaults = sameRegion ? regionDefaults() : null;
  const changed = INPUT_DEFS.filter(
    (def) =>
      def.section === "advanced" &&
      (!def.visibleWhen || def.visibleWhen(cfg)) &&
      (defaults === null || changedFromRegion(def, cfg, defaults)),
  );
  if (changed.length > 0) {
    const heading = document.createElement("dt");
    heading.className = "print-summary-heading";
    heading.textContent = "Changed in Advanced";
    list.append(heading);
    for (const def of changed) row(def.label, formatValue(def, cfg[def.key]));
  }
  document.getElementById("print-summary-link").textContent = `Open this scenario online: ${shareUrl(shown)}`;
}

// Each chart at the given width ("" for its screen width), drawn again for
// that size. Plotly only sizes a chart to its box on the first draw or on an
// autosize relayout, so the relayout comes first; the redraw then lays out
// the tornado's labels for the new width.
function sizeCharts(width) {
  for (const chart of document.querySelectorAll(".chart")) {
    chart.style.width = width;
    if (chart._fullLayout) Plotly.relayout(chart, { autosize: true });
  }
  redrawCharts();
}

/** `regions` is the list the inputs were built from. */
export function initPrint(regions) {
  const caveats = document.getElementById("region-caveats");
  let caveatsWereOpen = false;
  // A second beforeprint before the afterprint (Chromium's print-to-PDF
  // inside a print preview) must not save the print-time state as the
  // screen's.
  let printing = false;
  window.addEventListener("beforeprint", () => {
    fillSummary(regions);
    if (!printing) {
      caveatsWereOpen = caveats.open;
      trackEvent("page-printed");
    }
    printing = true;
    caveats.open = true;
    sizeCharts(`${PRINT_CHART_PX}px`);
    // Black, so the print stylesheet's colour inversion turns it pure white.
    for (const chart of document.querySelectorAll(".chart")) {
      if (chart._fullLayout) Plotly.relayout(chart, { paper_bgcolor: "#000", plot_bgcolor: "#000" });
    }
  });
  window.addEventListener("afterprint", () => {
    printing = false;
    caveats.open = caveatsWereOpen;
    sizeCharts("");
  });
}
