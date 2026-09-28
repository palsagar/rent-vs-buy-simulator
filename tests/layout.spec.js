import { test, expect } from '@playwright/test';

/**
 * Phone layout: the title bar, the controls that move into the inputs
 * sheet, the bottom sheets, page scrolling and touch targets. PHONE is an
 * iPhone 13 with Safari's toolbars showing.
 */

const PHONE = { viewport: { width: 390, height: 664 }, hasTouch: true, isMobile: true };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout: 20_000 },
  );
});

test.describe('phone: title bar', () => {
  test.use(PHONE);

  test('the app name fits on one line', async ({ page }) => {
    const box = await page.locator('#app-name').boundingBox();
    expect(box.height).toBeLessThan(30);
  });
});

test('the Advanced button does not use the error red', async ({ page }) => {
  const bg = await page.locator('#advanced-btn').evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(bg).not.toBe('rgb(218, 54, 51)');
});

test('the footer credits the author', async ({ page }) => {
  await expect(page.locator('footer a[href="https://github.com/palsagar"]')).toHaveCount(1);
});

test.describe('phone: controls move into the inputs panel', () => {
  test.use(PHONE);

  test('region, outlook and Advanced sit in the inputs panel; Guide in the title bar', async ({ page }) => {
    for (const sel of [
      '#input-panel #region-pills',
      '#input-panel #ftb-pill',
      '#input-panel #outlook-pills',
      '#input-panel #advanced-btn',
      '#title-bar #guide-btn',
    ]) {
      await expect(page.locator(sel)).toHaveCount(1);
    }
  });

  test('they return to the preset bar, in order, when the screen widens', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await expect(page.locator('#preset-bar #region-pills')).toHaveCount(1);
    const order = await page.evaluate(() =>
      [...document.getElementById('preset-bar').children]
        .map((c) => c.id)
        .filter((id) => ['region-group', 'outlook-group', 'advanced-btn', 'guide-btn'].includes(id)),
    );
    expect(order).toEqual(['region-group', 'outlook-group', 'advanced-btn', 'guide-btn']);
  });
});
