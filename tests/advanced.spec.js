import { test, expect } from '@playwright/test';

/**
 * The Advanced inputs: grouping, summaries, hiding, the levy-cap control,
 * and the "changed from the region default" markers. Desktop size unless a
 * block says otherwise.
 */

const PHONE = { viewport: { width: 390, height: 664 }, hasTouch: true, isMobile: true };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
});

/** Load the app at `path` and wait until the first results are in. */
async function boot(page, path = '/') {
  await page.goto(path);
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout: 20_000 },
  );
}

test('Advanced fields appear in group order with plain labels', async ({ page }) => {
  await boot(page);
  const labels = await page.locator('#advanced-inputs').evaluate((host) =>
    [...host.querySelectorAll('.slider-name, .checkbox-row')].map((el) => el.textContent.trim()),
  );
  expect(labels).toEqual([
    'Buying costs (% of price)',
    'Buying costs (fixed amount)',
    'Selling costs (% of price)',
    'Property levy (% of value per year)',
    'Property levy (fixed per year)',
    'Renter pays the levy too',
    'Home insurance (per year)',
    'Maintenance (% of value per year)',
    'Maintenance (fixed per year)',
    'Cost inflation',
    'Deduct mortgage interest from income tax',
    'Your top income-tax rate',
    'Levy is also deductible',
    'When is profit on the home taxed?',
    'Tax-free profit',
    'Tax-free after (years owned)',
    'Tax rate on taxable profit',
    'Tax on investment profit',
    'Wealth tax: assumed return',
    'Wealth tax: rate',
  ]);
});
