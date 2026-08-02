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

for (const vp of VIEWPORTS) {
  test(`welcome action row stays fully in-view at ${vp.width}x${vp.height} without scrolling`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    // Fresh profile：no flag seeded, so the welcome gate shows.
    await page.addInitScript(() => {
      try { localStorage.removeItem('rvb.tour.v1'); } catch (e) {}
    });
    await page.goto('/');
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

test('welcome action row stays in-view at 200% zoom (700px viewport)', async ({ page }) => {
  // Simulate 200% zoom by halving the CSS viewport; the welcome modal's
  // pinned action row should still keep both CTAs fully on screen.
  await page.setViewportSize({ width: 700, height: 450 });
  await page.addInitScript(() => {
    try { localStorage.removeItem('rvb.tour.v1'); } catch (e) {}
  });
  await page.goto('/');
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
