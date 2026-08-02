/**
 * Shared focus-management helpers for dialogs and overlays.
 *
 * The app is vanilla ES modules — this module is the single place overlays
 * (ui.js) and the tour (tour.js) pull focus plumbing from, so nobody
 * re-implements it. Three small primitives:
 *
 *   moveFocusIn(container, initial?)  — focus the `initial` element, else the
 *                                       first focusable inside `container`.
 *   trapFocus(container)              — keep Tab / Shift+Tab cycling inside
 *                                       `container` via a document keydown
 *                                       listener; returns a cleanup fn.
 *   restoreFocus(target)              — hand focus back to a launcher button.
 */

/** Interactive, non-disabled, visible elements inside `root`. */
export function getFocusable(root) {
  if (!root) return [];
  return Array.from(root.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), ' +
    'select:not([disabled]), textarea:not([disabled]), ' +
    '[tabindex]:not([tabindex="-1"])'
  )).filter((el) => el.offsetParent !== null || el === document.activeElement);
}

/**
 * Move focus into `container` — to `initial` if provided and contained,
 * otherwise to the first focusable element (falling back to the container).
 * Returns the list of focusable elements.
 */
export function moveFocusIn(container, initial) {
  if (!container) return [];
  const focusables = getFocusable(container);
  const target =
    initial && container.contains(initial) && typeof initial.focus === 'function'
      ? initial
      : focusables[0] || container;
  target.focus();
  return focusables;
}

/**
 * Keep Tab / Shift+Tab cycling inside `container`. Uses the live DOM each
 * keystroke, so it tolerates content being re-rendered underneath it. Returns
 * a cleanup function that removes the listener.
 *
 * `extra` is an optional list of elements (typically the focusable children of
 * a spotlighted tour target) spliced into the cycle alongside `container`'s own
 * focusables, so keyboard users can reach a target that lives outside the trap.
 * The caller is responsible for re-creating the trap whenever `extra` changes.
 */
export function trapFocus(container, extra = []) {
  if (!container) return () => {};
  const extras = extra.filter((el) => el && typeof el.focus === 'function');
  const onKeydown = (e) => {
    if (e.key !== 'Tab') return;
    const focusables = [...getFocusable(container), ...extras];
    if (focusables.length === 0) {
      e.preventDefault();
      return;
    }
    e.preventDefault();
    const active = document.activeElement;
    const idx = focusables.indexOf(active);
    // Explicitly step to the next/previous element in the combined set and
    // wrap at the edges. We do NOT rely on native tab order here: the extras
    // (spotlight targets) can live anywhere in the DOM, so only an explicit
    // walk over the set keeps every Tab inside the trap and reaches them.
    const step = e.shiftKey ? -1 : 1;
    const nextIdx = (idx + step + focusables.length) % focusables.length;
    focusables[nextIdx].focus();
  };
  document.addEventListener('keydown', onKeydown);
  return () => document.removeEventListener('keydown', onKeydown);
}

/** Hand focus back to a launcher button (no-op when there's nothing to do). */
export function restoreFocus(target) {
  if (target && typeof target.focus === 'function') target.focus();
}
