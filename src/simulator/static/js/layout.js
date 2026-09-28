// Phone layout. Below the drawer breakpoint the preset controls move into
// the inputs panel, next to the numbers they change, and the Guide button
// moves to the title bar; above it everything returns to the preset bar.
// Nodes are MOVED, never cloned, so listeners and ids survive: the tour
// targets #region-pills, #ftb-pill, #outlook-pills, #advanced-btn and
// #guide-btn by id, and opens the inputs panel when a target is inside it.

// Must match the max-width of the phone blocks in style.css.
const PHONE_QUERY = "(max-width: 900px)";

// [id of the node to move, id of its container on a phone]
const PHONE_MOVES = [
  ["region-group", "sheet-region"],
  ["outlook-group", "sheet-outlook"],
  ["advanced-btn", "sheet-advanced"],
  ["guide-btn", "title-bar"],
];

export function initPhoneLayout() {
  const moves = PHONE_MOVES.map(([id, phoneParentId]) => {
    const node = document.getElementById(id);
    return {
      node,
      phoneParent: document.getElementById(phoneParentId),
      // The desktop slot, captured before anything moves.
      desktopParent: node.parentNode,
      desktopNext: node.nextSibling,
    };
  });
  const media = window.matchMedia(PHONE_QUERY);
  const apply = () => {
    if (media.matches) {
      for (const m of moves) m.phoneParent.appendChild(m.node);
    } else {
      // Reverse order, so a saved neighbour that was itself moved is
      // already back in place when a node is re-inserted before it.
      for (const m of [...moves].reverse()) m.desktopParent.insertBefore(m.node, m.desktopNext);
    }
  };
  apply();
  media.addEventListener("change", apply);
}
