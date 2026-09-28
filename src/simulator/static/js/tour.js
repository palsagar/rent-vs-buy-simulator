import { trackEvent } from './analytics.js';
import { snapshotSettings, restoreSettings } from './inputs.js';
import { moveFocusIn, restoreFocus, trapFocus, getFocusable } from './focus.js';

/**
 * Onboarding tour — spotlight walkthrough of Rent or Buy?'s features.
 * Engine ported verbatim from the sibling apps (webgpu-fluid-solver /
 * webgpu-gray-scott/static/js/tour.js).
 *
 * The engine is step-agnostic: steps are injected, so tests can drive tiny
 * custom step arrays. The real script (STEPS below) is what main.js wires up.
 *
 * The overlay is four dim rects framing a GENUINE hole over the target (not a
 * translucent sheet): the spotlighted control is the only clickable element.
 * Do-it steps are detected purely from DOM events — the tour never
 * instruments inputs.js or ui.js internals.
 */

const STORAGE_KEY = 'rvb.tour.v1';
const PAD = 8; // px of breathing room around the spotlight hole

// The Tour instance currently running, if any. Module-wide so any entry point
// (ui.js's openGuide, tests driving custom instances) can end whatever tour is
// live, regardless of which instance started it.
let activeTour = null;

export function currentActiveTour() { return activeTour; }

export class Tour {
    /**
     * @param {Object} ctx
     * @param {Array} ctx.steps - [
     *   { target?: string, title: string, body: string,
     *     action?: { type: 'click' | 'change',
     *                selector?: string, advanceWhen?: (ctx) => boolean },
     *     onLeave?: (ctx) => void }
     * ]
     *
     * `action.selector` narrows which descendant counts as the do-it gesture
     * (e.g. click steps use it to ignore buttons that are not the intended
     * control). `action.advanceWhen` is an optional post-gesture gate that
     * decides whether the step should advance after a qualifying gesture.
     * `onLeave` fires both when navigating between steps and when the tour
     * exits (finish or skip).
     */
    constructor({ steps }) {
        this._ctx = {};
        this._snapshot = null;
        this._steps = steps;
        this._active = false;
        this._index = -1;
        this._els = null;            // { dims: [top,right,bottom,left], ring, tooltip }
        this._teardownAction = null; // removes the current step's action listeners
        this._releaseFocusTrap = null; // cleans up the tooltip Tab-trap
        this._launcher = null;       // element that started the tour (focus restore target)
        this._overrideTarget = null; // retargets the hole mid-step
        this._relayoutTimer = null;  // one deferred layout pass, covers target CSS transitions
        this._targetTransitionListener = null; // { target, fn } removes the relayout transition listener
        this._onKeydown = null;
        this._onResize = null;
        this._onScroll = null;       // debounced layout on scroll (ring tracks its target)
        this._scrollTimer = null;
        this._recheckTimer = null;   // one deferred re-render after a drawer/scroll settles
        this._recheckedStepIndex = -1;
    }

    get active() { return this._active; }
    get stepIndex() { return this._index; }

    static readFlag() {
        try { return localStorage.getItem(STORAGE_KEY); } catch { return null; }
    }

    static writeFlag(value) {
        // Private-mode failure just means the welcome re-appears next visit.
        try { localStorage.setItem(STORAGE_KEY, value); } catch { /* ignore */ }
    }

    /** Start (or restart) the tour from step 0. */
    start() {
        if (this._active) return;
        // Starting a new tour must first retire any other tour that is still
        // live. Otherwise the prior tour's dim overlay and document-level focus
        // trap would stay installed, and overwriting the activeTour registry
        // would orphan the old tour from later discovery (currentActiveTour /
        // ui.js openGuide) even though it is still running — leaving two focus
        // traps that can coexist. skip() runs the full teardown, so the old
        // tour's own guarded unregister clears the registry before we claim it.
        if (activeTour && activeTour !== this && activeTour.active) {
            activeTour.skip();
        }
        // Defensive teardown: sweep any tour surface left behind by an orphaned
        // or crashed instance, so a fresh start never stacks overlays/rings.
        document.querySelectorAll('.tour-dim, .tour-ring, .tour-tooltip').forEach((el) => el.remove());
        // The button that triggered start() is still focused — remember it so
        // we can hand focus back when the tour ends or is escaped.
        this._launcher = document.activeElement;
        document.getElementById('guide-overlay')?.classList.add('hidden');
        document.getElementById('advanced-panel')?.classList.remove('visible');
        document.getElementById('input-panel')?.classList.remove('visible');
        document.getElementById('drawer-scrim')?.classList.add('hidden');
        this._snapshot = snapshotSettings();
        this._buildDom();
        this._active = true;
        activeTour = this;
        // Keep Tab/Shift+Tab cycling inside the tooltip for the tour's whole
        // lifetime. The trap reads the live DOM per keystroke, so it stays
        // correct as step content is re-rendered.
        this._releaseFocusTrap = trapFocus(this._els.tooltip);
        trackEvent('tour-started');
        this._onKeydown = (e) => { if (e.key === 'Escape') this.skip(); };
        document.addEventListener('keydown', this._onKeydown);
        let resizeTimer = null;
        this._onResize = () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => this._layout(), 150);
        };
        window.addEventListener('resize', this._onResize);
        this._onScroll = () => {
            clearTimeout(this._scrollTimer);
            this._scrollTimer = setTimeout(() => this._layout(), 80);
        };
        // Scroll events don't bubble; a capture-phase listener catches any
        // scrollable descendant (results, input/advanced drawers, preset-bar).
        document.addEventListener('scroll', this._onScroll, { capture: true, passive: true });
        this._goTo(0);
    }

    /** Skip the tour — same teardown as finishing, different flag value. */
    skip() { this._end('skipped'); }

    /** Advance a read step. Last read step finishes the tour. */
    next() {
        const step = this._steps[this._index];
        if (!step || step.action) return;
        if (this._index === this._steps.length - 1) this._end('done');
        else this._goTo(this._index + 1);
    }

    /** Back is navigation, not time travel: undo nothing, retrace one step. */
    back() {
        if (this._index > 0) this._goTo(this._index - 1);
    }

    // ── Internals ─────────────────────────────────────────────────────────

    _end(result) {
        if (!this._active) return;
        trackEvent(result === 'skipped' ? 'tour-skipped' : 'tour-completed');
        this._teardownCurrentAction();
        const step = this._steps[this._index];
        if (step?.onLeave) step.onLeave(this._ctx);
        try {
            if (this._snapshot) restoreSettings(this._snapshot);
        } finally {
            this._snapshot = null;
            clearTimeout(this._relayoutTimer);
            clearTimeout(this._scrollTimer);
            clearTimeout(this._recheckTimer);
            this._detachTargetRelayoutListener();
            // Leave any drawer the tour opened (mobile inputs, advanced)
            // closed, matching the state tour start() set up, and drop its
            // scrim if one was shown.
            document.getElementById('input-panel')?.classList.remove('visible');
            document.getElementById('advanced-panel')?.classList.remove('visible');
            document.getElementById('drawer-scrim')?.classList.add('hidden');
            Tour.writeFlag(result);
            this._removeDom();
            // Drop the Tab-trap and hand focus back to the control that
            // launched the tour — or, if that control now lives inside a
            // closing overlay and would be invisible, an always-on-page
            // toolbar control / the body instead.
            this._releaseFocusTrap?.();
            this._releaseFocusTrap = null;
            restoreFocus(this._restoreTarget());
            this._launcher = null;
            document.removeEventListener('keydown', this._onKeydown);
            window.removeEventListener('resize', this._onResize);
            if (this._onScroll) document.removeEventListener('scroll', this._onScroll, { capture: true });
            this._active = false;
            this._index = -1;
            if (activeTour === this) activeTour = null;
        }
    }

    _goTo(i) {
        if (i < 0 || i >= this._steps.length) return;
        const prev = this._steps[this._index];
        this._teardownCurrentAction();
        if (prev?.onLeave) prev.onLeave(this._ctx);
        this._overrideTarget = null;
        this._index = i;
        clearTimeout(this._recheckTimer);
        this._recheckTimer = null;
        this._recheckedStepIndex = -1;
        this._renderStep();
    }

    /** Rebuild the tooltip Tab-trap with the current step's extra focusables. */
    _updateTrap(extras) {
        this._releaseFocusTrap?.();
        this._releaseFocusTrap = trapFocus(this._els.tooltip, extras);
    }

    /**
     * Pick where to hand focus back when the tour ends: the launcher if it is
     * still exposed, else an always-on-page control / the body. Launchers live
     * inside overlays (welcome, guide) that are mid-fade with `.hidden` at
     * teardown, so naive visibility checks see them as alive — test the overlay
     * state instead.
     */
    _restoreTarget() {
        if (this._isExposed(this._launcher)) return this._launcher;
        for (const sel of ['#guide-btn', '#advanced-btn']) {
            const el = document.querySelector(sel);
            if (el && this._isExposed(el)) return el;
        }
        return document.body;
    }

    _isExposed(el) {
        if (!el || !el.isConnected) return false;
        const hiddenOverlay = el.closest('.overlay.hidden');
        if (hiddenOverlay) return false;
        let node = el;
        while (node && node !== document.documentElement) {
            const cs = window.getComputedStyle(node);
            if (cs.display === 'none' || cs.visibility === 'hidden') return false;
            node = node.parentElement;
        }
        return true;
    }

    _renderStep() {
        const step = this._steps[this._index];
        const { tooltip } = this._els;
        const isLast = this._index === this._steps.length - 1;

        // Re-entrant (post-drawer/scroll recheck): shed any prior action
        // listeners so a do-it gesture is never double-wired.
        this._teardownCurrentAction();

        tooltip.innerHTML = '';
        const title = document.createElement('div');
        title.className = 'tour-title';
        title.id = 'tour-tooltip-title';
        title.textContent = step.title;
        const body = document.createElement('div');
        body.className = 'tour-body';
        body.textContent = step.body;
        const footer = document.createElement('div');
        footer.className = 'tour-footer';

        const counter = document.createElement('span');
        counter.className = 'tour-counter';
        counter.textContent = `${this._index + 1} / ${this._steps.length}`;

        const skipBtn = document.createElement('button');
        skipBtn.className = 'tour-skip';
        skipBtn.textContent = 'Skip tour';
        skipBtn.addEventListener('click', () => this.skip());

        const nav = document.createElement('span');
        nav.className = 'tour-nav';
        if (this._index > 0) {
            const backBtn = document.createElement('button');
            backBtn.className = 'tour-btn tour-btn-secondary';
            backBtn.textContent = 'Back';
            backBtn.addEventListener('click', () => this.back());
            nav.appendChild(backBtn);
        }
        // Try to make an off-viewport target frameable (open a collapsed
        // drawer that contains it; scroll the scrollable ancestor) before
        // deciding reachability.
        const needsRecheck = this._makeTargetReachable(step);

        // Reachability, not just DOM presence, decides whether an action
        // step can actually be performed. A target that exists but is
        // off-screen (closed drawer, zero rect, outside viewport) must fall
        // back to the primary button so the tour never deadlocks.
        let reachable = false;
        if (step.action && step.target) {
            const el = this._targetEl(step.target);
            if (el) {
                const r = el.getBoundingClientRect();
                const W = window.innerWidth;
                const band = this._sheetBand(el) ?? { top: 0, bottom: window.innerHeight };
                reachable = r.width > 0 && r.height > 0 && r.bottom > band.top && r.right > 0 && r.top < band.bottom && r.left < W;
            }
        }
        if (!step.action || !reachable) {
            const nextBtn = document.createElement('button');
            nextBtn.className = 'tour-btn tour-btn-primary';
            nextBtn.textContent = isLast ? 'Done' : 'Next';
            nextBtn.addEventListener('click', () => step.action ? this._advance() : this.next());
            nav.appendChild(nextBtn);
        }

        footer.append(counter, skipBtn, nav);
        tooltip.append(title, body, footer);

        // Move focus to the step's primary control (Next/Done), falling back
        // to Skip on do-it steps that render no Next button. Tab/Shift+Tab
        // then cycle through the tooltip controls — and, on do-it steps, the
        // spotlight target's own focusables so a keyboard user can reach the
        // control the step asks them to operate.
        const focusTarget = tooltip.querySelector('.tour-btn-primary') || tooltip.querySelector('.tour-skip');
        moveFocusIn(tooltip, focusTarget);

        // Rebuild the tooltip Tab-trap with this step's extras. Read steps
        // (with a Next button) keep focus strictly inside the tooltip; do-it
        // steps splice the spotlight target's focusable children into the cycle.
        this._updateTrap(step.action && step.target ? getFocusable(this._targetEl(step.target)) : []);

        this._els.ring.classList.toggle('tour-pulse', Boolean(step.action));
        this._installAction(step);

        this._layout();
        // Targets with CSS transitions (the Advanced panel slides in over
        // 0.3 s) get one deferred pass so the ring lands on their final rect.
        clearTimeout(this._relayoutTimer);
        this._relayoutTimer = setTimeout(() => this._layout(), 350);

        // One deferred re-render once a drawer/scroll transition settles, so
        // the do-it-vs-Next decision and the ring land on the final geometry.
        if (needsRecheck && this._recheckedStepIndex !== this._index) {
            this._recheckedStepIndex = this._index;
            const idx = this._index;
            clearTimeout(this._recheckTimer);
            this._recheckTimer = setTimeout(() => {
                this._recheckTimer = null;
                if (this._active && this._index === idx) this._renderStep();
            }, 420);
        }
    }

    /** Resolve the step's target element, falling back to centered on failure. */
    _targetEl(selector) {
        if (!selector) return null;
        const el = document.querySelector(selector);
        if (!el) console.warn(`[tour] target not found: ${selector} — falling back to centered`);
        return el;
    }

    /**
     * The strip of the screen where a control inside the phone inputs sheet
     * can be seen: below the sheet's sticky header, down to the sheet's
     * bottom edge. A control scrolled up under the header is hidden even
     * though it is inside the viewport. Null when `el` is not in the sheet,
     * or on desktop, where the header is not shown: the viewport applies.
     */
    _sheetBand(el) {
        const sheet = document.getElementById('input-panel');
        const header = document.getElementById('sheet-header');
        if (!sheet || !sheet.contains(el) || !header || !header.offsetHeight) return null;
        return {
            top: Math.max(0, header.getBoundingClientRect().bottom),
            bottom: Math.min(window.innerHeight, sheet.getBoundingClientRect().bottom),
        };
    }

    /**
     * Make an off-viewport target frameable. A target hidden by a collapsed
     * drawer (mobile inputs, right-side advanced) is opened via its toggle
     * button (never ui.js internals); any target outside the viewport is then
     * scrolled into view so the spotlight ring can frame it.
     * Returns true when visibility work was performed — the caller re-renders
     * once the drawer/scroll transition settles.
     */
    _makeTargetReachable(step) {
        if (!step.target) return false;
        const el = this._targetEl(step.target);
        if (!el) return false;

        // STATE-based reachability first: if the target lives inside a drawer
        // that is closed or mid-close (not `.visible`), reopen it BEFORE any
        // geometry check. Otherwise pressing Back while the drawer is sliding
        // shut would leave the target geometrically on-screen (mid-slide) even
        // though its owning panel is closing — the step would strand with no
        // Next button and no deferred recheck to open the drawer. Only open —
        // never toggle closed — and reuse the app's toggle button so we stay
        // decoupled from ui.js (it also re-shows the scrim).
        const inputPanel = document.getElementById('input-panel');
        const advancedPanel = document.getElementById('advanced-panel');
        let reopened = false;
        // #input-panel is only a closeable drawer in the mobile regime, where
        // the #inputs-btn toggle is actually shown (see style.css max-width:900px
        // and ui.js's own mobile check). On desktop it's a static always-visible
        // side panel that never carries `.visible`, so treating it as a closed
        // drawer here would click the desktop-hidden #inputs-btn and raise the
        // fixed scrim (z 250) over the panel — putting it between the pointer and
        // the spotlighted slider. Gate the reopen on the toggle being on-screen.
        const inputsBtn = document.getElementById('inputs-btn');
        const drawerRegime = inputsBtn && window.getComputedStyle(inputsBtn).display !== 'none';
        if (drawerRegime && inputPanel && inputPanel.contains(el) && !inputPanel.classList.contains('visible')) {
            inputsBtn.click();
            reopened = true;
        } else if (advancedPanel && advancedPanel.contains(el) && !advancedPanel.classList.contains('visible')) {
            // #advanced-panel is a true overlay drawer at every width (a
            // right-side panel on desktop, a bottom sheet on phones), so its
            // class-based reopen stays ungated.
            document.getElementById('advanced-btn')?.click();
            reopened = true;
        }

        // For the core inputs we bring the first slider itself into the hole
        // so the user can actually drag it.
        let focus = el;
        if (el.id === 'core-inputs') {
            const first = el.querySelector('input');
            if (first) focus = first;
        }
        const r = el.getBoundingClientRect();
        const W = window.innerWidth, H = window.innerHeight;
        // In the phone sheet the control must sit fully below the sticky
        // header (to within a pixel of rounding); elsewhere any part
        // on-screen will do.
        const band = this._sheetBand(el);
        const f = focus.getBoundingClientRect();
        const shown = band
            ? f.top >= band.top - 1 && f.bottom <= band.bottom + 1
            : r.width > 0 && r.height > 0 && r.bottom > 0 && r.right > 0 && r.top < H && r.left < W;
        if (reopened || shown) {
            // Already on-screen — or freshly reopened mid-close. Returning
            // `reopened` requests the deferred re-render so the do-it-vs-Next
            // decision and the ring land on the drawer's final OPEN geometry
            // once its transition settles, instead of mid-slide coordinates.
            return reopened;
        }
        // Scroll the spotlight target into view (minimal, axis-aware) so the
        // ring can frame it. The sheet's scroll-padding-top keeps it clear of
        // the sticky header.
        focus.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'auto' });
        return true;
    }

    _layout() {
        if (!this._active || !this._els) return;
        const { dims, ring, tooltip } = this._els;
        const step = this._steps[this._index];
        const W = window.innerWidth, H = window.innerHeight;
        const [dt, dr, db, dl] = dims;

        let el = this._targetEl(this._overrideTarget ?? step.target);
        // The hole and ring stay inside the part of the screen that shows
        // the target: the viewport, or the phone sheet below its header.
        const band = (el && this._sheetBand(el)) ?? { top: 0, bottom: H };
        if (el) {
            const r = el.getBoundingClientRect();
            if (r.width <= 0 || r.height <= 0 || r.bottom <= band.top || r.right <= 0 || r.top >= band.bottom || r.left >= W) {
                el = null;
            } else {
                this._attachTargetRelayoutListener(el);
            }
        }
        if (!el) this._detachTargetRelayoutListener();

        if (!el) {
            // Centered card: the top dim covers everything, ring hidden.
            Object.assign(dt.style, { left: '0px', top: '0px', width: `${W}px`, height: `${H}px` });
            for (const d of [dr, db, dl]) Object.assign(d.style, { left: '0px', top: '0px', width: '0px', height: '0px' });
            ring.style.display = 'none';
            tooltip.style.left = `${Math.max(12, (W - tooltip.offsetWidth) / 2)}px`;
            tooltip.style.top = `${Math.max(12, (H - tooltip.offsetHeight) / 2)}px`;
            return;
        }

        const r = el.getBoundingClientRect();
        const t = Math.max(band.top, r.top - PAD), l = Math.max(0, r.left - PAD);
        const b = Math.min(band.bottom, r.bottom + PAD), rt = Math.min(W, r.right + PAD);

        ring.style.display = 'block';
        Object.assign(ring.style, { left: `${l}px`, top: `${t}px`, width: `${rt - l}px`, height: `${b - t}px` });

        Object.assign(dt.style, { left: '0px', top: '0px', width: `${W}px`, height: `${t}px` });
        Object.assign(db.style, { left: '0px', top: `${b}px`, width: `${W}px`, height: `${H - b}px` });
        Object.assign(dl.style, { left: '0px', top: `${t}px`, width: `${l}px`, height: `${b - t}px` });
        Object.assign(dr.style, { left: `${rt}px`, top: `${t}px`, width: `${W - rt}px`, height: `${b - t}px` });

        // Tooltip: side with the most room; if no side plausibly fits (e.g. the
        // target is the whole canvas), float it at the top-center inside the hole.
        const tw = tooltip.offsetWidth, th = tooltip.offsetHeight, M = 12;
        const spaces = { bottom: H - b, top: t, right: W - rt, left: l };
        const side = Object.keys(spaces).sort((a, z) => spaces[z] - spaces[a])[0];
        let x, y;
        if (spaces[side] < 180) {
            x = Math.min(Math.max(l + (rt - l - tw) / 2, M), W - tw - M);
            y = Math.min(t + 16, H - th - M);
        } else if (side === 'bottom') {
            x = Math.min(Math.max(l, M), W - tw - M); y = b + M;
        } else if (side === 'top') {
            x = Math.min(Math.max(l, M), W - tw - M); y = Math.max(t - th - M, M);
        } else if (side === 'right') {
            x = rt + M; y = Math.min(Math.max(t, M), H - th - M);
        } else { // left
            x = Math.max(l - tw - M, M); y = Math.min(Math.max(t, M), H - th - M);
        }
        tooltip.style.left = `${x}px`;
        tooltip.style.top = `${y}px`;
    }

    /**
     * Re-layout when the current target's CSS transition finishes, so a
     * target that slides off-screen (e.g. the Advanced panel) falls back to the
     * centered-card layout instead of framing a hidden element.
     */
    _attachTargetRelayoutListener(el) {
        if (this._targetTransitionListener && this._targetTransitionListener.target === el) return;
        this._detachTargetRelayoutListener();
        const fn = () => this._layout();
        el.addEventListener('transitionend', fn);
        this._targetTransitionListener = { target: el, fn };
    }

    _detachTargetRelayoutListener() {
        if (!this._targetTransitionListener) return;
        const { target, fn } = this._targetTransitionListener;
        target.removeEventListener('transitionend', fn);
        this._targetTransitionListener = null;
    }

    _buildDom() {
        const mk = (cls) => {
            const d = document.createElement('div');
            d.className = cls;
            document.body.appendChild(d);
            return d;
        };
        const dims = ['top', 'right', 'bottom', 'left'].map(side => mk(`tour-dim tour-dim-${side}`));
        const ring = mk('tour-ring');
        const tooltip = mk('tour-tooltip');
        // Modal dialog semantics: the tooltip owns the focus while the tour is
        // up, and assistive tech treats the rest of the page as inert.
        tooltip.setAttribute('role', 'dialog');
        tooltip.setAttribute('aria-modal', 'true');
        tooltip.setAttribute('aria-labelledby', 'tour-tooltip-title');
        // Clicking a dim instead of the target: re-trigger the ring pulse,
        // nothing else. No nag tooltips, no auto-advance.
        dims.forEach(d => d.addEventListener('click', () => {
            if (!this._steps[this._index]?.action) return;
            ring.classList.remove('tour-pulse');
            void ring.offsetWidth; // restart the CSS animation
            ring.classList.add('tour-pulse');
        }));
        this._els = { dims, ring, tooltip };
    }

    _removeDom() {
        if (!this._els) return;
        const { dims, ring, tooltip } = this._els;
        [...dims, ring, tooltip].forEach(el => el.remove());
        this._els = null;
    }

    // Removes the current step's action listeners (installed only for do-it steps).
    _teardownCurrentAction() {
        this._teardownAction?.();
        this._teardownAction = null;
    }

    /** A do-it step's gesture was observed: advance, or finish on the last step. */
    _advance() {
        if (!this._active) return;
        if (this._index === this._steps.length - 1) this._end('done');
        else this._goTo(this._index + 1);
    }

    /**
     * Wire the DOM listeners that detect a do-it gesture. Pure DOM events —
     * the tour never reads app internals.
     */
    _installAction(step) {
        if (!step.action) return;
        const el = this._targetEl(step.target);
        const offs = [];
        const on = (target, type, fn) => {
            target.addEventListener(type, fn);
            offs.push(() => target.removeEventListener(type, fn));
        };

        switch (step.action.type) {
            case 'click': {
                if (!el) break;
                // Delegated targets (toolbar groups) count only real controls.
                // An optional `selector` narrows which descendant counts, and
                // an optional `advanceWhen` gate lets the step decide after a
                // qualifying click whether it really should advance.
                on(el, 'click', (e) => {
                    const selector = step.action.selector ?? 'button, input, a';
                    if (!e.target.closest(selector)) return;
                    if (!step.action.advanceWhen || step.action.advanceWhen(this._ctx)) {
                        this._advance();
                    }
                });
                break;
            }
            case 'change': {
                if (!el) break;
                on(el, 'change', () => this._advance());
                break;
            }
            default:
                console.warn(`[tour] unknown action type: ${step.action.type}`);
        }
        this._teardownAction = () => { offs.forEach(off => off()); };
    }
}

/**
 * The 12-step onboarding script, in Guide order. Copy stays at one or two
 * sentences per step: the tour orients, the Guide (?) documents.
 */
export const STEPS = [
    { target: null, title: 'Welcome to Rent or Buy?', body: 'A side-by-side simulator for the biggest financial decision most people make: buy a home, or rent and invest the difference. A quick tour of every feature — about a minute.' },
    { target: '#region-pills', title: 'Region presets', body: 'Tax rules, buyer costs and typical prices for five regions — US, France, Germany, Netherlands, UK. Pick one now and watch every number and the currency update.', action: { type: 'click', selector: '.preset-btn' } },
    { target: '#ftb-pill', title: 'First-time-buyer relief', body: 'Regions with buyer relief get this toggle — on by default, and it withdraws itself above the statutory price cap. Greyed out when the region or the price rules it out.' },
    { target: '#outlook-pills', title: 'Market outlook', body: 'Conservative, historical, or optimistic growth and inflation assumptions. Switch outlooks to stress the verdict — try Optimistic now.', action: { type: 'click', selector: '.preset-btn' } },
    { target: '#core-inputs', title: 'Your situation', body: 'Price, down payment, mortgage rate, rent — drag any slider, or tap its value to type an exact number, and the charts recompute live. The URL updates too: the address bar is always a shareable link.', action: { type: 'change' }, onLeave: () => { document.getElementById('input-panel')?.classList.remove('visible'); document.getElementById('drawer-scrim')?.classList.add('hidden'); } },
    { target: '#verdict-hero', title: 'The verdict', body: 'The headline: which strategy leaves you wealthier at your horizon, by how much, the breakeven year, and the Monte Carlo confidence. Four stat cards break down year-1 costs.' },
    { target: '#decision-chart', title: 'Net value over time', body: 'What you’d walk away with minus everything you put in, at every year — hover or tap for exact figures. Where the orange line crosses the blue is your breakeven.' },
    { target: '#fan-chart', title: 'How sure is this?', body: '500 simulated futures with randomized year-by-year returns. The fan shows the range of outcomes; the tornado below ranks which assumptions swing the result most.' },
    { target: '#advanced-btn', title: 'Advanced assumptions', body: 'Open the drawer: tax deductibility, capital gains, levies, maintenance — every default follows the selected region. Open it now, then press Next.', onLeave: () => {
        document.getElementById('advanced-panel')?.classList.remove('visible');
        // On a phone the Advanced button lives in the inputs sheet, which the
        // tour opened to reach it; the next steps frame the results.
        document.getElementById('input-panel')?.classList.remove('visible');
        document.getElementById('drawer-scrim')?.classList.add('hidden');
    } },
    { target: '#numbers', title: 'The numbers', body: 'Every figure behind the charts, year by year — expand the table or download it as CSV for your own analysis.' },
    { target: '#guide-btn', title: 'The Guide', body: 'The concepts behind the simulator — net value, breakeven, Monte Carlo — documented one tap or click away, with a Replay the Tour button at the bottom.' },
    { target: null, title: 'You’re all set', body: 'Everything you changed during the tour has been restored. Adjust the inputs to your own numbers — the URL is always a shareable link to your exact scenario.' },
];
