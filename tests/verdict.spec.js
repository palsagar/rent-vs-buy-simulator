import { test, expect } from '@playwright/test';

/**
 * Verdict wording. Monte Carlo is seeded (seed 42), so these configs give
 * stable results:
 *   default config            -> Buying ahead by $1,248, wins 46% of futures (toss-up)
 *   ?propertyPrice=1295000    -> Renting ahead by $739,670, wins 96% (clear)
 */

async function load(page, query = '') {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto(`/${query}`);
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout: 20_000 },
  );
}

test('a winner that wins 40-60% of futures reads as a toss-up', async ({ page }) => {
  await load(page);
  await expect(page.locator('#verdict-line')).toHaveText(
    'Too close to call: buying and renting end within ~$1,248 of each other after 10 years',
  );
});

// Guard: passes before and after -- the clear case must keep naming the winner.
test('a clear verdict still names the winner', async ({ page }) => {
  await load(page, '?propertyPrice=1295000&r=us&v=2');
  await expect(page.locator('#verdict-line')).toHaveText(
    'Renting leaves you ~$739,670 wealthier if you sell after 10 years',
  );
});

test('negative net values come with a one-line explanation', async ({ page }) => {
  await load(page); // Buy -$190,046, Rent -$191,294
  await expect(page.locator('#net-note')).toBeVisible();
  await expect(page.locator('#net-note')).toHaveText(
    'Both net values count rent, mortgage payments and other costs as money spent, so they are often below zero. What decides the verdict is the gap between them.',
  );
});

// Guard: toBeHidden also passes while #net-note does not exist yet.
test('the explanation stays hidden when both net values are positive', async ({ page }) => {
  // Buy ends at about +$2.76M and Rent at about +$4.02M.
  await load(page, '?horizonYears=40&propertyPrice=50000&monthlyRent=500&propertyAppreciationAnnual=10&equityGrowthAnnual=15&r=us&v=2');
  await expect(page.locator('#net-note')).toBeHidden();
});

test('a failed Monte Carlo run clears the toss-up headline', async ({ page }) => {
  await load(page);
  await expect(page.locator('#verdict-line')).toContainText('Too close to call');

  // The next config is clear-cut, but its Monte Carlo run fails, so nothing
  // can replace the toss-up state carried over from the default config.
  await page.route('**/api/monte-carlo', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) }),
  );
  const priceRow = page.locator('#core-inputs .slider-row', { hasText: 'Home price' });
  const input = priceRow.locator('input');
  await input.fill('1295000');
  await input.evaluate((el) => el.dispatchEvent(new Event('input', { bubbles: true })));

  await expect(page.locator('#error-banner')).toContainText('Monte Carlo failed: boom');
  await expect(page.locator('#verdict-line')).toContainText('Renting leaves you');
  await expect(page.locator('#verdict-line')).not.toContainText('Too close to call');
});
