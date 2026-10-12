import { test, expect } from '@playwright/test';

/**
 * Welcome modal CTA visibility regression.
 *
 * The expert-QA barrage flagged the welcome CTAs ("Take the Tour" /
 * "Skip to Simulator") as falling below the fold on shorter viewports after
 * the welcome copy grew. The fix trims the welcome copy and pins the action
 * row (flex footer, never part of the scrollable body), so the CTAs must sit
 * fully inside the viewport without any scrolling — on desktop and mobile,
 * and under 200% zoom.
 */

const VIEWPORTS = [
  { width: 1280, height: 720, label: 'desktop' },
  { width: 390, height: 844, label: 'mobile' },
];

// A link that sets its own numbers gets the shared-scenario welcome.
const SHARED = '/?propertyPrice=750000&r=us&v=2';

for (const [vp, url] of VIEWPORTS.flatMap((vp) => [[vp, '/'], [vp, SHARED]])) {
  test(`welcome action row stays fully in-view at ${vp.width}x${vp.height} without scrolling (${url})`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    // Fresh profile：no flag seeded, so the welcome gate shows.
    await page.addInitScript(() => {
      try { localStorage.removeItem('rvb.tour.v1'); } catch (e) {}
    });
    await page.goto(url);
    await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });

    await expect(page.locator('#welcome-overlay')).toBeVisible();

    // Bounding-box check (not merely "present"): both CTAs must be fully
    // inside the viewport, unobscured, without scrolling to reach them.
    const inView = await page.evaluate(() => {
      const vh = window.innerHeight;
      const vw = window.innerWidth;
      for (const sel of ['#start-tour-btn', '#start-sim-btn']) {
        const el = document.querySelector(sel);
        if (!el) return false;
        const r = el.getBoundingClientRect();
        if (r.top < 0 || r.bottom > vh || r.left < 0 || r.right > vw || r.height <= 0) return false;
      }
      return true;
    });
    expect(inView).toBe(true);
  });
}

for (const url of ['/', SHARED]) {
  test(`welcome action row stays in-view at 200% zoom (700px viewport) (${url})`, async ({ page }) => {
    // Simulate 200% zoom by halving the CSS viewport; the welcome modal's
    // pinned action row should still keep both CTAs fully on screen.
    await page.setViewportSize({ width: 700, height: 450 });
    await page.addInitScript(() => {
      try { localStorage.removeItem('rvb.tour.v1'); } catch (e) {}
    });
    await page.goto(url);
    await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
    await expect(page.locator('#welcome-overlay')).toBeVisible();

    const inView = await page.evaluate(() => {
      const vh = window.innerHeight;
      const vw = window.innerWidth;
      for (const sel of ['#start-tour-btn', '#start-sim-btn']) {
        const r = document.querySelector(sel).getBoundingClientRect();
        if (r.top < 0 || r.bottom > vh || r.left < 0 || r.right > vw || r.height <= 0) return false;
      }
      return true;
    });
    expect(inView).toBe(true);
  });
}

async function openFresh(page, url) {
  await page.addInitScript(() => {
    try { localStorage.removeItem('rvb.tour.v1'); } catch (e) {}
  });
  await page.goto(url);
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await expect(page.locator('#welcome-overlay')).toBeVisible();
}

test('a shared link opens on a welcome that offers to view it', async ({ page }) => {
  await openFresh(page, SHARED);
  await expect(page.locator('#welcome-title')).toHaveText('Someone shared a scenario with you');
  await expect(page.locator('.welcome-hero-sub')).toHaveText('Their numbers are already filled in');
  const first = page.locator('.welcome-actions button').first();
  await expect(first).toHaveId('start-sim-btn');
  await expect(first).toHaveText('View this shared scenario');
  await expect(first).toBeFocused();
  await expect(page.locator('#start-tour-btn')).toHaveText('Take the tour first');

  await first.click();
  await expect(page.locator('#welcome-overlay')).toBeHidden();
  expect(await page.evaluate(() => localStorage.getItem('rvb.tour.v1'))).toBe('skipped');
  await expect(page.locator('#core-inputs input[type=range]').first()).toHaveValue('750000');
});

// A plain visit's own link, and a link that only repeats the defaults.
for (const url of ['/?r=us&v=2', '/?propertyPrice=500000&v=2']) {
  test(`a link with only default values gets the usual welcome (${url})`, async ({ page }) => {
    await openFresh(page, url);
    const first = page.locator('.welcome-actions button').first();
    await expect(first).toHaveId('start-tour-btn');
    await expect(first).toHaveText('Take the Tour');
    await expect(page.locator('#welcome-title')).toHaveText('Buy vs. Rent Financial Simulator');
  });
}
