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

/**
 * Keep Monte Carlo pending: the server answers each request, but the page
 * receives the answer only when `release()` is called. Requests made after
 * a release are held again.
 */
async function holdMonteCarlo(page) {
  const held = [];
  await page.route('**/api/monte-carlo', async (route) => {
    const response = await route.fetch();
    held.push(() => route.fulfill({ response }));
  });
  return {
    count: () => held.length,
    release: () => Promise.all(held.splice(0).map((answer) => answer())),
  };
}

/** Move the home price slider the way a drag does: an input event. */
async function dragPrice(page, value) {
  await page.evaluate((v) => {
    const price = document.querySelector('#core-inputs input[type=range]');
    price.value = v;
    price.dispatchEvent(new Event('input', { bubbles: true }));
  }, value);
}

test('a region switch names the winner while its Monte Carlo run is pending', async ({ page }) => {
  await load(page);
  const line = page.locator('#verdict-line');
  await expect(line).toContainText('Too close to call');
  await holdMonteCarlo(page);

  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  // The UK result is shown; its Monte Carlo run has not answered.
  await expect(line).toContainText('£');
  await expect(page.locator('#verdict-confidence')).toHaveText('');
  await expect(line).not.toContainText('Too close to call');
  await expect(line).toContainText('leaves you');
});

// Guard: the carry-over for drags already works; it must keep working.
test('a slider drag inside a toss-up keeps the toss-up wording until Monte Carlo reports', async ({ page }) => {
  await load(page);
  const line = page.locator('#verdict-line');
  await expect(line).toContainText('~$1,248');
  const mc = await holdMonteCarlo(page);

  await dragPrice(page, 505000);
  // The new result is shown; its Monte Carlo run has not answered.
  await expect(line).not.toContainText('~$1,248');
  await expect(page.locator('#verdict-confidence')).toHaveText('');
  await expect(line).toContainText('Too close to call');

  // The drag kept the result close: Monte Carlo still calls it a toss-up.
  await expect.poll(mc.count).toBe(1);
  await mc.release();
  await expect(page.locator('#verdict-confidence')).toContainText('% of simulated futures');
  await expect(line).toContainText('Too close to call');
});

test('a toss-up call still in flight does not carry over to a region switch', async ({ page }) => {
  await load(page);
  const line = page.locator('#verdict-line');
  const mc = await holdMonteCarlo(page);
  await dragPrice(page, 505000);
  await expect.poll(mc.count).toBe(1);

  // The toss-up answer for the dragged price lands after the switch but
  // before the UK result.
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await mc.release();

  await expect(line).toContainText('£');
  await expect(page.locator('#verdict-confidence')).toHaveText('');
  await expect(line).not.toContainText('Too close to call');
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
