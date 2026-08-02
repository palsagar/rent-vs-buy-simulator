import { trackEvent } from './analytics.js';
import { snapshotSettings, restoreSettings } from './inputs.js';

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
        this._overrideTarget = null; // retargets the hole mid-step
        this._relayoutTimer = null;  // one deferred layout pass, covers target CSS transitions
        this._targetTransitionListener = null; // { target, fn } removes the relayout transition listener
        this._onKeydown = null;
        this._onResize = null;
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
        document.getElementById('guide-overlay')?.classList.add('hidden');
        document.getElementById('advanced-panel')?.classList.remove('visible');
        document.getElementById('input-panel')?.classList.remove('visible');
        this._snapshot = snapshotSettings();
        this._buildDom();
        this._active = true;
        trackEvent('tour-started');
        this._onKeydown = (e) => { if (e.key === 'Escape') this.skip(); };
        document.addEventListener('keydown', this._onKeydown);
        let resizeTimer = null;
        this._onResize = () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => this._layout(), 150);
        };
        window.addEventListener('resize', this._onResize);
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
            this._detachTargetRelayoutListener();
            Tour.writeFlag(result);
            this._removeDom();
            document.removeEventListener('keydown', this._onKeydown);
            window.removeEventListener('resize', this._onResize);
            this._active = false;
            this._index = -1;
        }
    }

    _goTo(i) {
        if (i < 0 || i >= this._steps.length) return;
        const prev = this._steps[this._index];
        this._teardownCurrentAction();
        if (prev?.onLeave) prev.onLeave(this._ctx);
        this._overrideTarget = null;
        this._index = i;
        this._renderStep();
    }

    _renderStep() {
        const step = this._steps[this._index];
        const { tooltip } = this._els;
        const isLast = this._index === this._steps.length - 1;

        tooltip.innerHTML = '';
        const title = document.createElement('div');
        title.className = 'tour-title';
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
        // Reachability, not just DOM presence, decides whether an action
        // step can actually be performed. A target that exists but is
        // off-screen (closed drawer, zero rect, outside viewport) must fall
        // back to the primary button so the tour never deadlocks.
        let reachable = false;
        if (step.action && step.target) {
            const el = this._targetEl(step.target);
            if (el) {
                const r = el.getBoundingClientRect();
                const W = window.innerWidth, H = window.innerHeight;
                reachable = r.width > 0 && r.height > 0 && r.bottom > 0 && r.right > 0 && r.top < H && r.left < W;
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

        this._els.ring.classList.toggle('tour-pulse', Boolean(step.action));
        this._installAction(step);

        this._layout();
        // Targets with CSS transitions (the Advanced panel slides in over
        // 0.3 s) get one deferred pass so the ring lands on their final rect.
        clearTimeout(this._relayoutTimer);
        this._relayoutTimer = setTimeout(() => this._layout(), 350);
    }

    /** Resolve the step's target element, falling back to centered on failure. */
    _targetEl(selector) {
        if (!selector) return null;
        const el = document.querySelector(selector);
        if (!el) console.warn(`[tour] target not found: ${selector} — falling back to centered`);
        return el;
    }

    _layout() {
        if (!this._active || !this._els) return;
        const { dims, ring, tooltip } = this._els;
        const step = this._steps[this._index];
        const W = window.innerWidth, H = window.innerHeight;
        const [dt, dr, db, dl] = dims;

        let el = this._targetEl(this._overrideTarget ?? step.target);
        if (el) {
            const r = el.getBoundingClientRect();
            if (r.width <= 0 || r.height <= 0 || r.bottom <= 0 || r.right <= 0 || r.top >= H || r.left >= W) {
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
        const t = Math.max(0, r.top - PAD), l = Math.max(0, r.left - PAD);
        const b = Math.min(H, r.bottom + PAD), rt = Math.min(W, r.right + PAD);

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
    { target: '#core-inputs', title: 'Your situation', body: 'Price, down payment, mortgage rate, rent — drag any slider and the charts recompute live. The URL updates too: the address bar is always a shareable link.', action: { type: 'change' } },
    { target: '#verdict-hero', title: 'The verdict', body: 'The headline: which strategy leaves you wealthier at your horizon, by how much, the breakeven year, and the Monte Carlo confidence. Four stat cards break down year-1 costs.' },
    { target: '#decision-chart', title: 'Net value over time', body: 'What you’d walk away with minus everything you put in, at every year — hover for exact figures. Where the orange line crosses the blue is your breakeven.' },
    { target: '#fan-chart', title: 'How sure is this?', body: '500 simulated futures with randomized year-by-year returns. The fan shows the range of outcomes; the tornado below ranks which assumptions swing the result most.' },
    { target: '#advanced-btn', title: 'Advanced assumptions', body: 'Open the drawer: tax deductibility, capital gains, levies, maintenance — every default follows the selected region. Click to open it now.', action: { type: 'click' }, onLeave: () => document.getElementById('advanced-panel')?.classList.remove('visible') },
    { target: '#numbers', title: 'The numbers', body: 'Every figure behind the charts, year by year — expand the table or download it as CSV for your own analysis.' },
    { target: '#guide-btn', title: 'The Guide', body: 'The concepts behind the simulator — net value, breakeven, Monte Carlo — documented one click away, with a Replay the Tour button at the bottom.' },
    { target: null, title: 'You’re all set', body: 'Everything you changed during the tour has been restored. Adjust the inputs to your own numbers — the URL is always a shareable link to your exact scenario.' },
];
