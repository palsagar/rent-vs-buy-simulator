import { test, expect } from '@playwright/test';

/**
 * An exact tie (ADR-0010 amendment): when Buy - Rent is under half a unit
 * of currency, the server reports winner "tie" and no part of the page
 * names a winner. Slider steps never land within half a dollar, but a
 * typed price can: the first test uses one. The others take the server's
 * real answer and make its verdict a tie in flight, as advanced.spec.js
 * does for /api/regions, so they do not depend on where the tie falls.
 */

const PHONE = { viewport: { width: 390, height: 664 }, hasTouch: true, isMobile: true };

async function loadTie(page, { level = false } = {}) {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.route('**/api/simulate', async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.verdict.winner = 'tie';
    body.verdict.difference = 0;
    body.breakevenYear = null;
    // Level every year, not only at the horizon.
    if (level) body.series.netRent = [...body.series.netBuy];
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

test('a typed price where the two end level reads as a tie, end to end', async ({ page }) => {
  // At a $535,634 home and every other US default, Buy - Rent is +$0.39.
  // Found by bisecting the price; like the amounts in verdict.spec.js, an
  // engine change can move it ($535,633 is +$1.19, $535,636 is -$1.22).
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  const simulated = page.waitForResponse('**/api/simulate');
  await page.goto('/?propertyPrice=535634');
  expect((await (await simulated).json()).verdict.winner).toBe('tie');
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout: 20_000 },
  );
  await expect(page.locator('#verdict-line')).toHaveText(
    'Buying and renting leave you equally well off after 10 years',
  );
  await expect(page.locator('#tornado-summary')).toHaveText(
    'Buying and renting are level, so any change here would put one of them ahead.',
  );
});

test('the headline says the two end equally well off, with no amount', async ({ page }) => {
  await loadTie(page);
  await expect(page.locator('#verdict-line')).toHaveText(
    'Buying and renting leave you equally well off after 10 years',
  );
  await expect(page.locator('#verdict-line .amount-buy, #verdict-line .amount-rent')).toHaveCount(0);
});

test('the breakeven line names neither side when the two are level every year', async ({ page }) => {
  await loadTie(page, { level: true });
  await expect(page.locator('#verdict-breakeven')).toHaveText('Neither pulls ahead within 10 years');
});

test('a tie at the horizon still says who leads before it', async ({ page }) => {
  // The default config, with no crossing reported: renting leads in the
  // early years (buying pays its up-front costs), so it is named.
  await loadTie(page);
  await expect(page.locator('#verdict-breakeven')).toHaveText(
    /^(Buying|Renting) is ahead until the two end level at year 10$/,
  );
});

test('a tie at the horizon keeps the breakeven of an earlier crossing', async ({ page }) => {
  // Ends level after 30 years, but buying overtakes renting near year 9 and
  // leads by about $45,711 at year 20.
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  const simulated = page.waitForResponse('**/api/simulate');
  await page.goto('/?horizonYears=30&equityGrowthAnnual=8.025318049137098&r=us&v=3');
  const body = await (await simulated).json();
  expect(body.verdict.winner).toBe('tie');
  expect(body.breakevenYear).not.toBeNull();
  const year = Math.ceil(body.breakevenYear);
  expect(year).toBeLessThan(30);
  await expect(page.locator('#verdict-breakeven')).toHaveText(
    `Buying is ahead from year ${year} until the two end level at year 30`,
  );
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
