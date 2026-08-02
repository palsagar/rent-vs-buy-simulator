import { test, expect } from '@playwright/test';

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

async function waitForPills(page) {
  await page.waitForFunction(() => document.querySelectorAll('#region-pills .preset-btn').length > 0);
}

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

/** Start a tour with the real 12-step STEPS script. */
async function startRealTour(page) {
  await waitForPills(page);
  await page.evaluate(async () => {
    const { Tour, STEPS } = await import('./js/tour.js');
    window.__testTour = new Tour({ steps: STEPS });
    window.__testTour.start();
  });
  // Clear the beforeEach seed so the test's own flag writes are what gets asserted.
  await page.evaluate(() => localStorage.removeItem('rvb.tour.v1'));
}

/** Perform the gesture the current do-it step asks for. */
async function performCurrentAction(page) {
  const idx = await page.evaluate(() => window.__testTour.stepIndex);
  switch (idx) {
    case 1: // region pill click
      await page.locator('#region-pills .preset-btn').first().click();
      break;
    case 3: // outlook pill click
      await page.locator('#outlook-pills .preset-btn').first().click();
      break;
    case 4: { // core-inputs change
      await page.evaluate(() => {
        const input = document.querySelector('#core-inputs input');
        const step = Number(input.step || 1);
        input.value = String(Math.min(Number(input.max), Number(input.value) + step));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      });
      break;
    }
    case 8: // advanced button click
      await page.click('#advanced-btn');
      break;
    default:
      throw new Error(`step ${idx} is not a do-it step`);
  }
  await page.waitForFunction((i) => window.__testTour.stepIndex === i + 1, idx);
}

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

test('mobile action step falls back to a Next button when the target is off-screen', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 600 });
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await waitForPills(page);

  await startRealTour(page);

  // Advance through any read steps until we reach step 5 ("Your situation"),
  // whose #core-inputs target is off-screen on the narrow mobile viewport.
  while (await page.evaluate(() => window.__testTour.stepIndex) < 4) {
    const hasNext = await page.locator('.tour-footer .tour-btn-primary').count();
    if (hasNext) await page.locator('.tour-footer .tour-btn-primary').click();
    else await performCurrentAction(page);
    await page.waitForTimeout(100);
  }

  await expect(page.locator('.tour-counter')).toHaveText('5 / 12');
  const nextBtn = page.locator('.tour-footer .tour-btn-primary');
  await expect(nextBtn).toHaveCount(1);
  await nextBtn.click();
  await expect(page.locator('.tour-counter')).toHaveText('6 / 12');
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
