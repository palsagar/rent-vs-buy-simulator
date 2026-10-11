// Advanced inputs: the fields that tailor the model to one situation, in
// five collapsible groups at the end of the inputs panel. Every group
// starts closed. Field metadata (label, help line, group) lives in
// fields.js; this module arranges it.

import { trackEvent } from "./analytics.js";
import { INPUT_DEFS } from "./fields.js";
import { buildField } from "./inputs.js";

// `id` is also the group name sent with the analytics events.
const GROUPS = [
  { id: "transaction", title: "Buying and selling costs" },
  { id: "yearly", title: "Yearly costs of owning" },
  { id: "mortgage-relief", title: "Tax relief on the mortgage" },
  { id: "home-sale", title: "Tax when you sell the home" },
  { id: "investments", title: "Tax on investments" },
];

function buildGroup(group, host) {
  const details = document.createElement("details");
  details.className = "adv-group";
  details.dataset.group = group.id;

  const summary = document.createElement("summary");
  const title = document.createElement("span");
  title.className = "adv-group-title";
  title.textContent = group.title;
  const line = document.createElement("span");
  line.className = "adv-group-summary";
  const values = document.createElement("span");
  values.className = "adv-group-values";
  const changed = document.createElement("span");
  changed.className = "adv-group-changed";
  line.append(values, changed);
  summary.append(title, line);
  summary.addEventListener("click", (e) => {
    // The click lands before the toggle, so a closed group is opening.
    // Only real clicks count: the tour and the tests click programmatically.
    if (e.isTrusted && !details.open) trackEvent("advanced-group-opened", { group: group.id });
  });

  const body = document.createElement("div");
  body.className = "adv-group-body";
  for (const def of INPUT_DEFS.filter((d) => d.group === group.id)) {
    const el = document.createElement("div");
    el.className = "adv-field";
    el.dataset.key = def.key;
    buildField(def, el);
    body.appendChild(el);
  }

  details.append(summary, body);
  host.appendChild(details);
}

export function initAdvanced() {
  const host = document.getElementById("advanced-inputs");
  for (const group of GROUPS) buildGroup(group, host);
}
