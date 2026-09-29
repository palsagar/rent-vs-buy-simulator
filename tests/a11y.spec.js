import { test, expect } from '@playwright/test';

/**
 * Accessibility regressions: overlay focus management, dialog semantics,
 * keyboard accordion, and the mobile inputs-drawer scrim.
 *
 * Test conventions match tests/tour.spec.js: the beforeEach seeds the tour
 * flag so the first-visit welcome gate stays out of the way, and tests that
 * care about the welcome control their own flag via addInitScript before
 * goto.
 */

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
});

test('tour traps focus inside the tooltip and Esc restores focus to the launcher', async ({ page }) => {
  // Open the Guide, then Replay the Tour from it — the launcher of record is
  // the #btn-replay-tour button that started the tour.
  await page.click('#guide-btn');
  await expect(page.locator('#guide-overlay')).toBeVisible();
  await page.click('#btn-replay-tour');
  await page.waitForFunction(() => window.__rvb.tour?.active === true);
  await expect(page.locator('.tour-tooltip')).toBeVisible();

  // Focus landed on the step's primary control (Next).
  expect(
    await page.evaluate(() => document.activeElement?.className ?? '')
  ).toContain('tour-btn-primary');

  // Repeated Tab presses never escape the tooltip.
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press('Tab');
    const probe = await page.evaluate(() => {
      const tooltip = document.querySelector('.tour-tooltip');
      const ae = document.activeElement;
      return { inside: tooltip ? tooltip.contains(ae) : false, cls: ae?.className ?? '' };
    });
    expect(probe.inside).toBe(true);
    expect(probe.cls).toMatch(/tour-btn|tour-skip/);
  }

  // The dialog is modal: role + aria-modal + labelled by its title.
  const dialog = await page.evaluate(() => {
    const t = document.querySelector('.tour-tooltip');
    return { role: t.getAttribute('role'), modal: t.getAttribute('aria-modal'), labelledby: t.getAttribute('aria-labelledby') };
  });
  expect(dialog.role).toBe('dialog');
  expect(dialog.modal).toBe('true');
  expect(dialog.labelledby).toContain('tour-tooltip-title');

  // Esc tears down the tour and hands focus back to a control that is actually
  // VISIBLE. The launcher of record is #btn-replay-tour, which now lives inside
  // the just-closed Guide overlay, so the tour must fall back to an always-on-
  // page control (#guide-btn) instead of focusing something hidden.
  await page.keyboard.press('Escape');
  await expect(page.locator('.tour-tooltip')).toHaveCount(0);
  const restored = await page.evaluate(() => {
    const ae = document.activeElement;
    const cs = window.getComputedStyle(ae);
    return { id: ae?.id ?? '', visHidden: cs.visibility === 'hidden', displayNone: cs.display === 'none' };
  });
  expect(restored.id).toBe('guide-btn');
  expect(restored.visHidden).toBe(false);
  expect(restored.displayNone).toBe(false);
  // After the overlay's 0.3s fade, the focused control must still be visible.
  await page.waitForTimeout(400);
  const afterFade = await page.evaluate(() => {
    const ae = document.activeElement;
    const cs = window.getComputedStyle(ae);
    return { id: ae?.id ?? '', visHidden: cs.visibility === 'hidden', displayNone: cs.display === 'none' };
  });
  expect(afterFade.id).toBe('guide-btn');
  expect(afterFade.visHidden).toBe(false);
  expect(afterFade.displayNone).toBe(false);
});

test('guide accordion toggles with Enter/Space and navigates with Shift+Tab', async ({ page }) => {
  await page.click('#guide-btn');
  await expect(page.locator('#guide-overlay')).toBeVisible();

  const section = page.locator('.guide-section').nth(0);
  const firstHeader = page.locator('.guide-section-header').nth(0);

  await firstHeader.focus();
  await expect(firstHeader).toBeFocused();
  expect(await firstHeader.getAttribute('aria-expanded')).toBe('false');

  // Enter toggles the section open and mirrors it on aria-expanded.
  await page.keyboard.press('Enter');
  await expect(section).toHaveClass(/open/);
  await expect(firstHeader).toHaveAttribute('aria-expanded', 'true');

  // Space toggles it closed again.
  await page.keyboard.press(' ');
  await expect(section).not.toHaveClass(/open/);
  await expect(firstHeader).toHaveAttribute('aria-expanded', 'false');

  // Shift+Tab navigates backward to the previous header, which stays
  // operable (the multiple-open model is untouched — A11Y-05 accepted).
  await page.locator('.guide-section-header').nth(1).focus();
  await page.keyboard.press('Shift+Tab');
  await expect(page.locator('.guide-section-header').nth(0)).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('.guide-section-header').nth(0)).toHaveAttribute('aria-expanded', 'true');
});

test('inputs drawer scrim closes the drawer and hides itself', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 600 });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });

  const scrim = page.locator('#drawer-scrim');
  const drawer = page.locator('#input-panel');
  await expect(scrim).toBeHidden();

  await page.click('#inputs-btn');
  await expect(drawer).toHaveClass(/visible/);
  await expect(scrim).toBeVisible();

  // The drawer slides in over 0.3s; wait until its transform reaches rest so
  // the hit-test below measures the settled layout, not a mid-flight panel
  // whose left edge still covers the slider centre with the scrim/page.
  await page.waitForFunction(() => {
    const t = getComputedStyle(document.getElementById('input-panel')).transform;
    return t === 'none' || /^matrix\(1, 0, 0, 1, -?0(?:\.0+)?, -?0(?:\.0+)?\)$/.test(t);
  }, null, { timeout: 5_000 });

  // Hit-test (elementFromPoint, not programmatic dispatch): the drawer must sit
  // ABOVE its own scrim, so a pointer over a slider centre lands on the
  // slider/track — never on the scrim intercepting the tap.
  const hit = await page.evaluate(() => {
    const slider = document.querySelector('#input-panel input');
    const r = slider.getBoundingClientRect();
    const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return {
      isSlider: at === slider || slider.contains(at),
      insideDrawer: at ? document.getElementById('input-panel').contains(at) : false,
      isScrim: at?.id === 'drawer-scrim',
    };
  });
  expect(hit.isSlider).toBe(true);
  expect(hit.isScrim).toBe(false);

  await scrim.click({ position: { x: 400, y: 100 } });
  await expect(drawer).not.toHaveClass(/visible/);
  await expect(scrim).toBeHidden();
});

test('keyboard users can reach and activate a do-it spotlit target', async ({ page }) => {
  // A do-it step renders no Next button, so Tab must reach the spotlit
  // control (a region pill) even though it lives outside the tooltip trap.
  await page.waitForFunction(() => document.querySelectorAll('#region-pills .preset-btn').length > 0);
  await page.evaluate(async () => {
    const { Tour } = await import('./js/tour.js');
    window.__kbTour = new Tour({
      steps: [
        { target: '#region-pills', title: 'Pick a region', body: 'Click a region pill.', action: { type: 'click', selector: '.preset-btn' } },
        { target: null, title: 'Done', body: 'Finished.' },
      ],
    });
    window.__kbTour.start();
  });
  await page.waitForFunction(() => window.__kbTour?.active === true);
  await expect(page.locator('.tour-footer .tour-btn-primary')).toHaveCount(0); // do-it: no Next

  // Tab from the tooltip's Skip fallback until a region pill is focused.
  let reached = false;
  for (let i = 0; i < 12 && !reached; i++) {
    await page.keyboard.press('Tab');
    reached = await page.evaluate(() => document.activeElement?.matches('#region-pills .preset-btn') ?? false);
  }
  expect(reached).toBe(true);

  // Enter on the focused pill activates it, advancing the tour.
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => window.__kbTour?.stepIndex === 1);
});

test('opening the Guide during its tour step ends the tour first (single modal)', async ({ page }) => {
  // A read step spotlights the live Guide button; clicking it must not stack a
  // second focus trap — the tour ends and its overlay comes down first.
  await page.evaluate(async () => {
    const { Tour } = await import('./js/tour.js');
    window.__gmTour = new Tour({
      steps: [
        { target: '#guide-btn', title: 'The Guide step', body: 'Click it.' },
        { target: null, title: 'Done', body: 'Finished.' },
      ],
    });
    window.__gmTour.start();
  });
  await page.waitForFunction(() => window.__gmTour?.active === true);
  await expect(page.locator('.tour-tooltip')).toBeVisible();

  await page.click('#guide-btn');
  await page.waitForFunction(() => window.__gmTour?.active === false);
  await expect(page.locator('.tour-tooltip')).toHaveCount(0);
  await expect(page.locator('#guide-overlay')).toBeVisible();
});

test('starting a second tour while one is active tears the first down', async ({ page }) => {
  // double-start race: tour B starts while tour A is still live. Starting B
  // must retire A first so A's overlay and focus trap come down, and ending B
  // must not leave an orphaned A behind in the registry (single active modal).
  await page.evaluate(async () => {
    const { Tour } = await import('./js/tour.js');
    window.__tourA = new Tour({
      steps: [
        { target: null, title: 'A', body: 'First tour.' },
        { target: null, title: 'A2', body: 'Second step.' },
      ],
    });
    window.__tourA.start();
  });
  await page.waitForFunction(() => window.__tourA?.active === true);
  await expect(page.locator('.tour-tooltip')).toHaveCount(1);

  // Start a second, different tour instance while A is still live.
  await page.evaluate(async () => {
    const { Tour } = await import('./js/tour.js');
    window.__tourB = new Tour({
      steps: [
        { target: null, title: 'B', body: 'Second tour.' },
      ],
    });
    window.__tourB.start();
  });

  // Exactly ONE tour surface remains — A was torn down, B is live.
  await page.waitForFunction(() => window.__tourB?.active === true);
  await expect(page.locator('.tour-tooltip')).toHaveCount(1);
  await expect(page.locator('.tour-dim')).toHaveCount(4);
  expect(await page.evaluate(() => window.__tourA.active)).toBe(false);
  expect(await page.evaluate(() => window.__tourB.active)).toBe(true);

  // Ending B (the only live tour) clears the registry; A's guarded unregister
  // must not have left a stale reference to an already-ended tour.
  await page.evaluate(() => window.__tourB.skip());
  await expect(page.locator('.tour-tooltip')).toHaveCount(0);
  const registry = await page.evaluate(async () => {
    const { currentActiveTour } = await import('./js/tour.js');
    return currentActiveTour();
  });
  expect(registry).toBe(null);
});

test('welcome dialog is labelled by an existing heading', async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.removeItem('rvb.tour.v1'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await expect(page.locator('#welcome-overlay')).toBeVisible();

  const probe = await page.evaluate(() => {
    const w = document.getElementById('welcome-overlay');
    const labelledby = w.getAttribute('aria-labelledby');
    const el = labelledby ? document.getElementById(labelledby) : null;
    return { labelledby, exists: !!el, tag: el?.tagName ?? null };
  });
  expect(probe.labelledby).toBe('welcome-title');
  expect(probe.exists).toBe(true);
  expect(probe.tag).toBe('H1');
});
