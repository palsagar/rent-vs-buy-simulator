import { test, expect } from '@playwright/test';

/**
 * An exact tie (ADR-0010 amendment): when Buy - Rent is under half a unit
 * of currency, the server reports winner "tie" and no part of the page
 * names a winner. No slider setting lands within half a dollar, so each
 * test takes the server's real answer and makes its verdict a tie in
 * flight, as advanced.spec.js does for /api/regions.
 */

const PHONE = { viewport: { width: 390, height: 664 }, hasTouch: true, isMobile: true };

async function loadTie(page) {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.route('**/api/simulate', async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.verdict.winner = 'tie';
    body.verdict.difference = 0;
    body.breakevenYear = null;
    await route.fulfill({ response, json: body });
  });
  await page.route('**/api/monte-carlo', async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.buyWinsPct = 50;
    body.tornado.base = 0;
    // Every lower test ends level too, so its hover has nothing to name.
    body.tornado.low = body.tornado.low.map(() => 0.2);
    await route.fulfill({ response, json: body });
  });
  await page.goto('/');
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout: 20_000 },
  );
}

test('the headline says the two end equally well off, with no amount', async ({ page }) => {
  await loadTie(page);
  await expect(page.locator('#verdict-line')).toHaveText(
    'Buying and renting leave you equally well off after 10 years',
  );
  await expect(page.locator('#verdict-line .amount-buy, #verdict-line .amount-rent')).toHaveCount(0);
});

test('the breakeven line names neither side', async ({ page }) => {
  await loadTie(page);
  await expect(page.locator('#verdict-breakeven')).toHaveText('Neither pulls ahead within 10 years');
});

test('the confidence line shows buying\'s share of the simulated futures', async ({ page }) => {
  await loadTie(page);
  await expect(page.locator('#verdict-confidence')).toContainText('Buying wins in 50% of simulated futures');
});

test('the tornado sentence and hovers say the two are level', async ({ page }) => {
  await loadTie(page);
  await expect(page.locator('#tornado-summary')).toHaveText(
    'Buying and renting are level, so any change here would put one of them ahead.',
  );
  const hover = await page.evaluate(() => {
    const el = document.getElementById('tornado-chart');
    return el.data[0].customdata[el.data[0].y.indexOf('Home price')];
  });
  expect(hover).toMatch(/<br>Buying and renting level$/);
});

test.describe('phone', () => {
  test.use(PHONE);

  test('the live verdict in the inputs sheet says the two end level', async ({ page }) => {
    await loadTie(page);
    await page.click('#inputs-btn');
    await expect(page.locator('#sheet-verdict')).toHaveText('Buying and renting end level after 10 yrs');
  });
});
