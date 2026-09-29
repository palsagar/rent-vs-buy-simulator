import { test, expect } from '@playwright/test';
import { waitForPills, startRealTour, performCurrentAction } from './helpers.js';

/**
 * Onboarding tour.
 *
 * The Tour engine is step-agnostic — steps are injected — so most tests drive
 * tiny custom step arrays via `startTour`. The real 12-step STEPS script gets
 * its own walkthrough test.
 */

test.beforeEach(async ({ page }) => {
  // Seed 'done' so the welcome gate stays out of the way of engine tests.
  // Each Playwright test gets a fresh context, so the seed never leaks
  // between tests; startTour/startRealTour clear it again so flag assertions
  // stay meaningful.
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
});

/** Instantiate and start a Tour in the page with a custom step array. */
async function startTour(page, steps) {
  await page.evaluate(async (steps) => {
    const { Tour } = await import('./js/tour.js');
    window.__testTour = new Tour({ steps });
    window.__testTour.start();
  }, steps);
  // Clear the beforeEach seed so the test's own flag writes are what gets asserted.
  await page.evaluate(() => localStorage.removeItem('rvb.tour.v1'));
}

test('read steps render the overlay, navigate with Next/Back, and tear down on Escape', async ({ page }) => {
  await startTour(page, [
    { target: null, title: 'Step one', body: 'Centered intro.' },
    { target: '#verdict-hero', title: 'Step two', body: 'Targeted at the verdict.' },
  ]);

  await expect(page.locator('.tour-dim')).toHaveCount(4);
  await expect(page.locator('.tour-ring')).toHaveCount(1);
  await expect(page.locator('.tour-tooltip')).toHaveCount(1);
  await expect(page.locator('.tour-title')).toHaveText('Step one');
  await expect(page.locator('.tour-counter')).toHaveText('1 / 2');

  await page.locator('.tour-footer .tour-btn-primary').click(); // Next
  await expect(page.locator('.tour-counter')).toHaveText('2 / 2');
  await expect(page.locator('.tour-title')).toHaveText('Step two');

  await page.locator('.tour-footer .tour-btn-secondary').click(); // Back
  await expect(page.locator('.tour-counter')).toHaveText('1 / 2');

  await page.keyboard.press('Escape');
  await expect(page.locator('.tour-dim')).toHaveCount(0);
  await expect(page.locator('.tour-tooltip')).toHaveCount(0);
  const flag = await page.evaluate(() => localStorage.getItem('rvb.tour.v1'));
  expect(flag).toBe('skipped');
});

test('the dim rects block the page while the hole passes events to the target', async ({ page }) => {
  await waitForPills(page);
  await startTour(page, [
    { target: '#region-pills', title: 'Only step', body: 'Targeted.' },
  ]);

  const probe = await page.evaluate(() => {
    const dim = document.querySelector('.tour-dim-top');
    const dr = dim.getBoundingClientRect();
    const atDim = document.elementFromPoint(dr.left + dr.width / 2, dr.top + dr.height / 2);
    const target = document.getElementById('region-pills');
    const tr = target.getBoundingClientRect();
    const atHole = document.elementFromPoint(tr.left + tr.width / 2, tr.top + tr.height / 2);
    return {
      dimBlocked: atDim?.classList.contains('tour-dim') ?? false,
      holeOpen: atHole === target || target.contains(atHole),
    };
  });
  expect(probe.dimBlocked).toBe(true);
  expect(probe.holeOpen).toBe(true);
});

test('a click do-it step has no Next button and advances when the target is clicked', async ({ page }) => {
  await waitForPills(page);
  await startTour(page, [
    { target: '#region-pills', title: 'Pick a region', body: 'Click a region pill.', action: { type: 'click', selector: '.preset-btn' } },
    { target: null, title: 'Done', body: 'Finished.' },
  ]);

  await expect(page.locator('.tour-footer .tour-btn-primary')).toHaveCount(0); // do-it: no Next
  await expect(page.locator('.tour-ring')).toHaveClass(/tour-pulse/);

  await page.locator('#region-pills .preset-btn').first().click(); // through the hole
  await page.waitForFunction(() => window.__testTour.stepIndex === 1);
});

test('a change do-it step advances when a slider dispatches change inside the target', async ({ page }) => {
  await page.waitForFunction(() => document.querySelectorAll('#core-inputs input').length > 0);
  await startTour(page, [
    { target: '#core-inputs', title: 'Move a slider', body: 'Change any core input.', action: { type: 'change' } },
    { target: null, title: 'Done', body: 'Finished.' },
  ]);

  await expect(page.locator('.tour-footer .tour-btn-primary')).toHaveCount(0);

  await page.evaluate(() => {
    const input = document.querySelector('#core-inputs input');
    const step = Number(input.step || 1);
    input.value = String(Math.min(Number(input.max), Number(input.value) + step));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.waitForFunction(() => window.__testTour.stepIndex === 1);
});

test('missing-target action step renders a primary button and advances on click', async ({ page }) => {
  await startTour(page, [
    { target: '#no-such-element', title: 'Ghost action', body: 'Target is missing.', action: { type: 'click' } },
    { target: null, title: 'Step 2', body: 'Done.' },
  ]);

  await expect(page.locator('.tour-footer .tour-btn-primary')).toHaveCount(1);
  await page.locator('.tour-footer .tour-btn-primary').click();
  await page.waitForFunction(() => window.__testTour.stepIndex === 1);
});

test('a missing target falls back to centered placement and stays advanceable', async ({ page }) => {
  await startTour(page, [
    { target: '#no-such-element', title: 'Ghost', body: 'Nowhere to point.' },
  ]);
  await expect(page.locator('.tour-tooltip')).toBeVisible();
  await expect(page.locator('.tour-ring')).toBeHidden();
  await page.locator('.tour-footer .tour-btn-primary').click(); // Done
  expect(await page.evaluate(() => localStorage.getItem('rvb.tour.v1'))).toBe('done');
});

test('the full STEPS walkthrough completes and restores the pre-tour settings', async ({ page }) => {
  await waitForPills(page);
  const before = await page.evaluate(async () => {
    const { getConfig, getRegionId } = await import('./js/state.js');
    return { config: getConfig(), regionId: getRegionId() };
  });

  await startRealTour(page);
  await expect(page.locator('.tour-counter')).toHaveText('1 / 12');

  for (let guard = 0; guard < 12; guard++) {
    const done = await page.evaluate(() => !window.__testTour.active);
    if (done) break;
    const hasNext = await page.locator('.tour-footer .tour-btn-primary').count();
    if (hasNext) await page.locator('.tour-footer .tour-btn-primary').click();
    else await performCurrentAction(page);
    // Do-it steps may trigger async recomputes; give the loop a beat.
    await page.waitForTimeout(100);
  }

  expect(await page.evaluate(() => window.__testTour.active)).toBe(false);
  await expect(page.locator('.tour-tooltip')).toHaveCount(0);
  expect(await page.evaluate(() => localStorage.getItem('rvb.tour.v1'))).toBe('done');

  const after = await page.evaluate(async () => {
    const { getConfig, getRegionId } = await import('./js/state.js');
    return { config: getConfig(), regionId: getRegionId() };
  });
  expect(after).toEqual(before);
});

test('skip mid-tour restores settings and writes the skipped flag', async ({ page }) => {
  await waitForPills(page);

  // Dirty the state, then capture the baseline: the tour snapshots whatever
  // is live at start() time, so the restore must land back here (UK), not on
  // the pre-dirty default (US).
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  const beforeRegion = await page.evaluate(async () => {
    const { getRegionId } = await import('./js/state.js');
    return getRegionId();
  });

  await startRealTour(page);
  await page.locator('.tour-footer .tour-btn-primary').click(); // step 1 → 2
  await performCurrentAction(page);                  // region click → step 3
  await page.keyboard.press('Escape');

  expect(await page.evaluate(() => window.__testTour.active)).toBe(false);
  expect(await page.evaluate(() => localStorage.getItem('rvb.tour.v1'))).toBe('skipped');
  const afterRegion = await page.evaluate(async () => {
    const { getRegionId } = await import('./js/state.js');
    return getRegionId();
  });
  expect(afterRegion).toBe(beforeRegion);
});

test('onLeave fires on Escape-triggered tour exit', async ({ page }) => {
  await page.evaluate(async () => {
    const { Tour } = await import('./js/tour.js');
    window.__onLeaveCalls = 0;
    window.__onLeaveActionTornDown = null;
    const steps = [
      { target: null, title: 'Step 1', body: 'Intro.' },
      {
        target: '#region-pills',
        title: 'Step 2',
        body: 'Exit me.',
        action: { type: 'click', selector: '.preset-btn' },
        onLeave: () => {
          window.__onLeaveCalls = (window.__onLeaveCalls || 0) + 1;
          window.__onLeaveActionTornDown = window.__testTour._teardownAction === null;
        },
      },
    ];
    window.__testTour = new Tour({ steps });
    window.__testTour.start();
  });
  await page.evaluate(() => localStorage.removeItem('rvb.tour.v1'));

  await page.locator('.tour-footer .tour-btn-primary').click(); // step 1 → 2
  await page.keyboard.press('Escape');

  expect(await page.evaluate(() => window.__onLeaveCalls)).toBe(1);
  expect(await page.evaluate(() => window.__onLeaveActionTornDown)).toBe(true);
});

test('first visit shows the welcome and Take the Tour starts the tour', async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.removeItem('rvb.tour.v1'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });

  await expect(page.locator('#welcome-overlay')).toBeVisible();
  await expect(page.locator('#start-tour-btn')).toBeVisible();

  await page.click('#start-tour-btn');
  await page.waitForFunction(() => window.__rvb.tour?.active === true);
  expect(await page.evaluate(() => window.__rvb.tour.stepIndex)).toBe(0);
  await expect(page.locator('#welcome-overlay')).toBeHidden();
});

test('a seeded flag suppresses the welcome entirely', async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });

  await expect(page.locator('#welcome-overlay')).toBeHidden();
  expect(await page.evaluate(() => window.__rvb.tour?.active ?? false)).toBe(false);
});

test('Skip to Simulator writes the flag and dismisses without starting the tour', async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.removeItem('rvb.tour.v1'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });

  await page.click('#start-sim-btn');
  await expect(page.locator('#welcome-overlay')).toBeHidden();
  expect(await page.evaluate(() => localStorage.getItem('rvb.tour.v1'))).toBe('skipped');
  expect(await page.evaluate(() => window.__rvb.tour?.active ?? false)).toBe(false);
});

test('Replay the Tour from the guide restarts from step 1', async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await waitForPills(page);

  // Dirty state, then open the guide and replay.
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await page.click('#guide-btn');
  await expect(page.locator('#guide-overlay')).toBeVisible();
  await page.click('#btn-replay-tour');

  await page.waitForFunction(() => window.__rvb.tour?.active === true);
  expect(await page.evaluate(() => window.__rvb.tour.stepIndex)).toBe(0);
  await expect(page.locator('#guide-overlay')).toBeHidden();
});

test('mobile action step opens the inputs drawer instead of falling back to Next', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 600 });
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await waitForPills(page);

  await startRealTour(page);

  // Advance through any read steps until we reach step 5 ("Your situation").
  while (await page.evaluate(() => window.__testTour.stepIndex) < 4) {
    const hasNext = await page.locator('.tour-footer .tour-btn-primary').count();
    if (hasNext) await page.locator('.tour-footer .tour-btn-primary').click();
    else await performCurrentAction(page);
    await page.waitForTimeout(100);
  }
  await expect(page.locator('.tour-counter')).toHaveText('5 / 12');

  // The tour opens the closed inputs drawer and scrolls the first slider
  // into the spotlight; the step stays a do-it step (no Next button).
  await expect(page.locator('#input-panel')).toHaveClass(/visible/);
  await expect(page.locator('.tour-footer .tour-btn-primary')).toHaveCount(0);
  const sliderInView = await page.evaluate(() => {
    const el = document.querySelector('#core-inputs input');
    const r = el.getBoundingClientRect();
    const W = window.innerWidth, H = window.innerHeight;
    return r.width > 0 && r.height > 0 && r.bottom > 0 && r.right > 0 && r.top < H && r.left < W;
  });
  expect(sliderInView).toBe(true);

  // Perform the do-it gesture; the tour advances to step 6.
  await page.evaluate(() => {
    const input = document.querySelector('#core-inputs input');
    const step = Number(input.step || 1);
    input.value = String(Math.min(Number(input.max), Number(input.value) + step));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await expect(page.locator('.tour-counter')).toHaveText('6 / 12');
});

test('leaving the mobile inputs step closes the drawer and scrim the tour opened', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 600 });
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await waitForPills(page);

  await startRealTour(page);

  // Advance to the core-inputs do-it step (index 4 → '5 / 12'): the tour
  // opens the closed mobile inputs drawer so the target is reachable.
  while (await page.evaluate(() => window.__testTour.stepIndex) < 4) {
    const hasNext = await page.locator('.tour-footer .tour-btn-primary').count();
    if (hasNext) await page.locator('.tour-footer .tour-btn-primary').click();
    else await performCurrentAction(page);
    await page.waitForTimeout(100);
  }
  await expect(page.locator('.tour-counter')).toHaveText('5 / 12');
  await expect(page.locator('#input-panel')).toHaveClass(/visible/);

  // Performing the do-it gesture advances the tour, which must close the
  // drawer AND its scrim (later spotlight rings frame content, not a drawer).
  await page.evaluate(() => {
    const input = document.querySelector('#core-inputs input');
    const step = Number(input.step || 1);
    input.value = String(Math.min(Number(input.max), Number(input.value) + step));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await expect(page.locator('.tour-counter')).toHaveText('6 / 12');
  await expect(page.locator('#input-panel')).not.toHaveClass(/visible/);
  await expect(page.locator('#drawer-scrim')).toBeHidden();
});

test('Back pressed while the inputs drawer is mid-close returns to a drivable do-it step', async ({ page }) => {
  // Widen the drawer slide so "mid-close" is a stable, deterministic window:
  // the target is still geometrically on-screen while its owning drawer is
  // closing — the exact regression the state-based reachability fix addresses.
  await page.addInitScript(() => {
    const style = document.createElement('style');
    style.textContent = '#input-panel { transition: transform 1.2s ease !important; }';
    document.head.appendChild(style);
  });
  await page.setViewportSize({ width: 800, height: 600 });
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await waitForPills(page);

  await startRealTour(page);

  // Advance to the core-inputs do-it step (index 4), which opens the drawer.
  while (await page.evaluate(() => window.__testTour.stepIndex) < 4) {
    const hasNext = await page.locator('.tour-footer .tour-btn-primary').count();
    if (hasNext) await page.locator('.tour-footer .tour-btn-primary').click();
    else await performCurrentAction(page);
    await page.waitForTimeout(100);
  }
  await expect(page.locator('.tour-counter')).toHaveText('5 / 12');
  await expect(page.locator('#input-panel')).toHaveClass(/visible/);
  // The spotlight slider is actually on-screen (drawer fully open) before we dance.
  await page.waitForFunction(() => {
    const el = document.querySelector('#core-inputs input');
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && r.right > 0 && r.left < window.innerWidth;
  });

  // Perform the gesture — the tour advances to step 6 and onLeave begins
  // closing the drawer (over the widened transition). Back lands mid-close,
  // while #core-inputs is still geometrically on-screen.
  await page.evaluate(() => {
    const input = document.querySelector('#core-inputs input');
    const step = Number(input.step || 1);
    input.value = String(Math.min(Number(input.max), Number(input.value) + step));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await expect(page.locator('.tour-counter')).toHaveText('6 / 12');
  await expect(page.locator('#input-panel')).not.toHaveClass(/visible/);
  await page.locator('.tour-footer .tour-btn-secondary').click(); // Back

  // Back returns to the core-inputs step with the drawer REOPENED and the
  // step still driveable: a real do-it step with no Next button.
  await page.waitForFunction(() =>
    window.__testTour.stepIndex === 4 &&
    document.getElementById('input-panel')?.classList.contains('visible') &&
    !document.querySelector('.tour-footer .tour-btn-primary'),
  );
  // Still a do-it step on the core-inputs content, and the reopened drawer's
  // scrim is showing again (it had been hidden by onLeave during the close).
  await expect(page.locator('.tour-title')).toHaveText('Your situation');
  await expect(page.locator('#drawer-scrim')).toBeVisible();
});

test('desktop: a real pointer on the spotlighted core slider works — no scrim over the side panel', async ({ page }) => {
  // Desktop regime: the default/wide viewport keeps #inputs-btn hidden and
  // #input-panel as the static always-visible side panel (style.css only turns
  // it into a drawer at max-width:900px). A previous round's state-first reopen
  // branch treated the static panel as a closed drawer and clicked the hidden
  // #inputs-btn on every core-inputs step, raising the fixed scrim (z 250)
  // above the panel so a real mouse click at the spotlighted slider centre hit
  // the scrim, never the slider — the do-it step could not be completed.
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await waitForPills(page);

  await startRealTour(page);

  // Advance to the core-inputs do-it step (index 4 → '5 / 12').
  while (await page.evaluate(() => window.__testTour.stepIndex) < 4) {
    const hasNext = await page.locator('.tour-footer .tour-btn-primary').count();
    if (hasNext) await page.locator('.tour-footer .tour-btn-primary').click();
    else await performCurrentAction(page);
    await page.waitForTimeout(100);
  }
  await expect(page.locator('.tour-counter')).toHaveText('5 / 12');

  // The tour must NOT reopen the static side panel as a drawer on desktop: the
  // inputs toggle is hidden and the scrim must stay hidden, so nothing covers
  // the spotlighted slider.
  await expect(page.locator('#inputs-btn')).toBeHidden();
  await expect(page.locator('#drawer-scrim')).toBeHidden();

  // Real hit-test: the element under the slider's centre is the slider itself
  // (no scrim interposed).
  const centre = await page.evaluate(() => {
    const el = document.querySelector('#core-inputs input');
    const r = el.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  });
  expect(await page.evaluate(({ x, y }) => {
    const el = document.elementFromPoint(x, y);
    const slider = document.querySelector('#core-inputs input');
    return el === slider || (slider?.contains?.(el) ?? false);
  }, centre)).toBe(true);

  // Perform a REAL pointer gesture (not a programmatic value dispatch) at the
  // far-right end of the track so the native click lands on a different value
  // and fires the browser's real `change` event.
  const before = await page.evaluate(() => Number(document.querySelector('#core-inputs input').value));
  const right = await page.evaluate(() => {
    const r = document.querySelector('#core-inputs input').getBoundingClientRect();
    return { x: r.right - 3, y: r.top + r.height / 2 };
  });
  await page.mouse.click(right.x, right.y);
  const after = await page.evaluate(() => Number(document.querySelector('#core-inputs input').value));

  // The slider received the pointer (value changed) and the tour advanced off
  // the do-it step on the native change event.
  expect(after).not.toBe(before);
  await expect(page.locator('.tour-counter')).toHaveText('6 / 12');
  await expect(page.locator('#drawer-scrim')).toBeHidden();
});

test('step 8 keeps the Advanced drawer open while active and closes it on Next', async ({ page }) => {
  await waitForPills(page);
  await startRealTour(page);

  // Advance to step 8 (index 8): read steps via Next, do-it steps via their gesture.
  while (await page.evaluate(() => window.__testTour.stepIndex) < 8) {
    const hasNext = await page.locator('.tour-footer .tour-btn-primary').count();
    if (hasNext) await page.locator('.tour-footer .tour-btn-primary').click();
    else await performCurrentAction(page);
    await page.waitForTimeout(100);
  }
  await expect(page.locator('.tour-counter')).toHaveText('9 / 12');

  // Click the Advanced button: the drawer opens and STAYS open while active.
  await page.click('#advanced-btn');
  await expect(page.locator('#advanced-panel')).toHaveClass(/visible/);
  await expect(page.locator('.tour-counter')).toHaveText('9 / 12'); // still on step 8

  // Advancing with Next runs onLeave, which closes the drawer.
  await page.locator('.tour-footer .tour-btn-primary').click();
  await expect(page.locator('.tour-counter')).toHaveText('10 / 12');
  await expect(page.locator('#advanced-panel')).not.toHaveClass(/visible/);
});

test('restoring a priced-out FTB intent re-enables relief when the price drops', async ({ page }) => {
  await waitForPills(page);

  // Select UK and price it above the FTB cap so the FTB pill withdraws.
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  const priceRow = page.locator('#core-inputs .slider-row', { hasText: 'Home price' });
  const priceInput = priceRow.locator('input');
  await priceInput.fill('650000');
  await priceInput.evaluate((el) => el.dispatchEvent(new Event('change', { bubbles: true })));
  await expect(page.locator('#ftb-pill .preset-btn')).toHaveClass(/disabled/);

  // Start and immediately skip the tour; restore should preserve ftbOn=true.
  await startRealTour(page);
  await page.keyboard.press('Escape');
  await expect(page.locator('.tour-tooltip')).toHaveCount(0);

  // Lower the price below the cap; the restored intent should re-apply relief.
  await priceInput.fill('400000');
  await priceInput.evaluate((el) => el.dispatchEvent(new Event('change', { bubbles: true })));
  await expect(page.locator('#ftb-pill .preset-btn')).toHaveClass(/active/);
});

test('prefers-reduced-motion disables the pulse animation and overlay transitions', async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.removeItem('rvb.tour.v1'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await page.emulateMedia({ reducedMotion: 'reduce' });

  await page.click('#start-sim-btn');
  await expect(page.locator('#welcome-overlay')).toBeHidden();

  await startTour(page, [
    { target: '#guide-btn', title: 'Step 1', body: 'An action step so the ring pulses.', action: { type: 'click' } },
    { target: null, title: 'Step 2', body: 'Done.' },
  ]);

  const styles = await page.evaluate(() => ({
    welcomeTransition: getComputedStyle(document.getElementById('welcome-overlay')).transitionDuration,
    guideTransition: getComputedStyle(document.getElementById('guide-overlay')).transitionDuration,
    pulseAnimation: getComputedStyle(document.querySelector('.tour-ring.tour-pulse')).animationName,
  }));

  expect(styles.welcomeTransition).toBe('0s');
  expect(styles.guideTransition).toBe('0s');
  expect(styles.pulseAnimation).toBe('none');
});
