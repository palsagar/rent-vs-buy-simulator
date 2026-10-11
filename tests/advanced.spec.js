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

const group = (page, id) => page.locator(`details.adv-group[data-group="${id}"]`);
const field = (page, key) => page.locator(`.adv-field[data-key="${key}"]`);

/** Open one group by clicking its summary row. */
async function openGroup(page, id) {
  await group(page, id).locator('summary').click();
  await expect(group(page, id)).toHaveAttribute('open', '');
}

test('the Advanced section sits in the inputs panel as five closed groups', async ({ page }) => {
  await boot(page);
  await expect(page.locator('#input-panel #advanced-section')).toHaveCount(1);
  await expect(page.locator('#advanced-panel')).toHaveCount(0);
  await expect(page.locator('.adv-group-title')).toHaveText([
    'Buying and selling costs',
    'Yearly costs of owning',
    'Tax relief on the mortgage',
    'Tax when you sell the home',
    'Tax on investments',
  ]);
  for (const el of await page.locator('details.adv-group').all()) {
    await expect(el).not.toHaveAttribute('open', '');
  }
});

test('opening a group shows its fields next to the live results', async ({ page }) => {
  await boot(page);
  await openGroup(page, 'transaction');
  await expect(field(page, 'closingCostSellerPct')).toBeVisible();
  await expect(page.locator('#verdict-line')).toBeInViewport();
});

test('the Advanced button scrolls the section into view and focuses the first group', async ({ page }) => {
  await boot(page);
  await page.locator('#input-panel').evaluate((el) => { el.scrollTop = 0; });
  await page.click('#advanced-btn');
  await expect(page.locator('#advanced-section')).toBeInViewport();
  await expect(group(page, 'transaction').locator('summary')).toBeFocused();
});

test.describe('phone', () => {
  test.use(PHONE);

  test('the groups sit in the inputs sheet under the live verdict, with no Advanced button', async ({ page }) => {
    await boot(page);
    await expect(page.locator('#advanced-btn')).toBeHidden();
    await page.click('#inputs-btn');
    const summary = group(page, 'transaction').locator('summary');
    await summary.scrollIntoViewIfNeeded();
    await summary.click();
    await expect(field(page, 'closingCostBuyerPct')).toBeVisible();
    await expect(page.locator('#sheet-verdict')).toBeInViewport();
  });
});
