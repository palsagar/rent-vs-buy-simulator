import { test, expect } from '@playwright/test';

/**
 * Umami analytics.
 *
 * The Playwright webServer runs WITHOUT UMAMI_DOMAIN/UMAMI_ID, so the tag is
 * never injected here: (a) guards the inert-by-construction contract, (b)-(c)
 * pin the trackEvent wrapper contract. Injection itself is verified by the
 * curl smoke in the deploy runbook.
 */

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
});

test('(a) dev server injects no Umami tag', async ({ page }) => {
  await expect(page.locator('script[data-website-id]')).toHaveCount(0);
});

test('(b) trackEvent without window.umami does not throw', async ({ page }) => {
  const ok = await page.evaluate(async () => {
    const { trackEvent } = await import('./js/analytics.js');
    try {
      trackEvent('test-event');
      trackEvent('test-event', { foo: 1 });
      return true;
    } catch {
      return false;
    }
  });
  expect(ok).toBe(true);
});

test('(c) trackEvent forwards name and props to window.umami.track', async ({ page }) => {
  const calls = await page.evaluate(async () => {
    window.__umamiCalls = [];
    window.umami = { track: (n, p) => window.__umamiCalls.push([n, p]) };
    const { trackEvent } = await import('./js/analytics.js');
    trackEvent('test-event', { foo: 1 });
    return window.__umamiCalls;
  });
  expect(calls).toEqual([['test-event', { foo: 1 }]]);
});

/** Stub window.umami before page scripts run; events land in window.__umamiCalls.
 *  addInitScript only applies to LATER navigations, so each test below calls
 *  page.goto('/') again after stubbing (the beforeEach goto runs without it). */
async function stubUmami(page) {
  await page.addInitScript(() => {
    window.__umamiCalls = [];
    window.umami = { track: (n, p) => window.__umamiCalls.push([n, p]) };
  });
}

/** Dismiss the first-visit welcome modal without starting the tour. */
async function dismissWelcome(page) {
  const skip = page.locator('#start-sim-btn');
  if (await skip.isVisible().catch(() => false)) await skip.click();
}

async function waitForPills(page) {
  await page.waitForFunction(() => document.querySelectorAll('#region-pills .preset-btn').length > 0);
}

async function eventNames(page) {
  return page.evaluate(() => window.__umamiCalls.map((c) => c[0]));
}

test('(d) tour start and skip fire tour-started / tour-skipped', async ({ page }) => {
  await stubUmami(page);
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await page.locator('#start-tour-btn').click();
  await expect.poll(() => eventNames(page)).toContain('tour-started');
  await page.keyboard.press('Escape');
  await expect.poll(() => eventNames(page)).toContain('tour-skipped');
});

test('region-changed fires with the selected region id', async ({ page }) => {
  await stubUmami(page);
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await dismissWelcome(page);
  await waitForPills(page);
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await expect.poll(() => page.evaluate(() => window.__umamiCalls))
    .toContainEqual(['region-changed', { region: 'uk' }]);
});

test('outlook-changed fires with the selected outlook key', async ({ page }) => {
  await stubUmami(page);
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await dismissWelcome(page);
  await page.locator('#outlook-pills .preset-btn', { hasText: 'Optimistic' }).click();
  await expect.poll(() => page.evaluate(() => window.__umamiCalls))
    .toContainEqual(['outlook-changed', { outlook: 'optimistic' }]);
});

test('ftb-toggled fires when the first-time-buyer pill is clicked', async ({ page }) => {
  await stubUmami(page);
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await dismissWelcome(page);
  await waitForPills(page);
  // The US region has no FTB relief, so switch to the UK first.
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await page.locator('#ftb-pill .preset-btn').click();
  await expect.poll(() => page.evaluate(() => window.__umamiCalls))
    .toContainEqual(['ftb-toggled', { on: false }]);
});

test('restore-quiet: tour restore uses applyPreset, not synthetic clicks', async ({ page }) => {
  await stubUmami(page);
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await dismissWelcome(page);
  await waitForPills(page);

  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await expect.poll(() => page.evaluate(() => window.__umamiCalls))
    .toContainEqual(['region-changed', { region: 'uk' }]);

  await page.evaluate(() => { window.__umamiCalls = []; });

  await page.evaluate(() => window.__rvb.tour.start());
  await expect.poll(() => eventNames(page)).toContain('tour-started');
  await page.keyboard.press('Escape');
  await expect.poll(() => eventNames(page)).toContain('tour-skipped');

  const names = await eventNames(page);
  expect(names).not.toContain('region-changed');
  expect(names).not.toContain('outlook-changed');
  expect(names).not.toContain('ftb-toggled');
});
