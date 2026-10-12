import { test, expect } from '@playwright/test';

/**
 * Mortgage insurance below 20% down (#44 item 11), and the v3 share link
 * that carries its rate. A link writes only values that differ from the
 * US default, so a link written before v3 says nothing about the rate:
 * it must take the rate of the link's region, not the US 0.5%.
 */

// Every FR value a share link carries, as a v2 link wrote them (with the
// first-time-buyer relief on). No mortgage insurance: v2 had none.
const FR_VALUES =
  'propertyPrice=290000&mortgageRateAnnual=3.45&monthlyRent=812' +
  '&mortgageTermYears=25&closingCostBuyerPct=6.958&propertyTaxRate=0' +
  '&annualHomeInsurance=220&annualMaintenancePct=0&annualPropertyLevy=1220' +
  '&annualMaintenanceAmount=1300&closingCostBuyerAmount=1300' +
  '&interestDeductionEnabled=false&marginalTaxRatePct=0&levyDeductionCap=0' +
  '&saleCgRegime=fully_exempt&saleCgExemptAmount=0&saleCgExemptAfterYears=30' +
  '&saleCgRatePct=36.2&portfolioCgRatePct=31.4';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
});

async function boot(page, path = '/') {
  await page.goto(path);
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout: 20_000 },
  );
}

const stored = (page) =>
  page.evaluate(async () => (await import('./js/state.js')).getConfig().mortgageInsuranceRatePct);
const field = (page) => page.locator('.adv-field[data-key="mortgageInsuranceRatePct"]');
const yearly = (page) => page.locator('details.adv-group[data-group="yearly"]');

async function openYearly(page) {
  await yearly(page).locator('summary').click();
  await expect(yearly(page)).toHaveAttribute('open', '');
}

test('an old French link takes France\'s rate, not the US one', async ({ page }) => {
  await boot(page, `/?${FR_VALUES}&r=fr&v=2`);
  expect(await stored(page)).toBe(0);
  // Nothing in the yearly group differs from the French defaults.
  await expect(yearly(page).locator('.adv-group-changed')).toHaveText('');
  await expect(field(page).locator('.adv-changed-dot')).toBeHidden();
});

test('an old French link with no region still opens in euros', async ({ page }) => {
  // Without `r` the region is matched from the values. The US default
  // rate this link cannot carry must not stop France from matching.
  await boot(page, `/?${FR_VALUES}&v=2`);
  await expect(page.locator('#verdict-hero')).toContainText('€');
  expect(await stored(page)).toBe(0);
});

test('a v3 link without the rate means the US default it stands for', async ({ page }) => {
  // In France the 0.5% was chosen on purpose, so it is marked as changed.
  await boot(page, `/?${FR_VALUES}&downPaymentPct=10&r=fr&v=3`);
  expect(await stored(page)).toBe(0.5);
  await openYearly(page);
  await expect(field(page).locator('.adv-changed-note')).toHaveText('Region default: 0.00%');
});

test('the field shows only below 20% down, and the yearly summary counts it', async ({ page }) => {
  await boot(page, '/?downPaymentPct=10');
  // 0.5% of the $450,000 borrowed is $2,250 on top of the $12,200 at 20% down.
  await expect(yearly(page).locator('.adv-group-values')).toHaveText('≈ $14,450 in year 1');
  await openYearly(page);
  await expect(field(page)).toBeVisible();
  await expect(field(page).locator('.slider-value')).toHaveText('0.50%');
  await expect(field(page)).toContainText('stops once you owe 78% of the price or less');

  const down = page.locator('#core-inputs .slider-row', { hasText: 'Down payment' });
  await down.locator('.slider-value').click();
  await down.locator('.slider-typed').fill('20');
  await down.locator('.slider-typed').press('Enter');
  await expect(field(page)).toBeHidden();
  await expect(yearly(page).locator('.adv-group-values')).toHaveText('≈ $12,200 in year 1');
});

test('a changed rate is written to the link, which is v3', async ({ page }) => {
  await boot(page, '/?downPaymentPct=10&r=us&v=3');
  await openYearly(page);
  const row = field(page).locator('.slider-row');
  await row.locator('.slider-value').click();
  await row.locator('.slider-typed').fill('1.25');
  await row.locator('.slider-typed').press('Enter');
  await expect.poll(() => new URL(page.url()).searchParams.get('mortgageInsuranceRatePct')).toBe('1.25');
  expect(new URL(page.url()).searchParams.get('v')).toBe('3');
});

test('the default US link never carries the rate', async ({ page }) => {
  await boot(page);
  await expect.poll(() => new URL(page.url()).searchParams.get('r')).toBe('us');
  const params = new URL(page.url()).searchParams;
  expect(params.has('mortgageInsuranceRatePct')).toBe(false);
  expect(params.get('v')).toBe('3');
});

test('the cost breakdown shows what the insurance costs', async ({ page }) => {
  await boot(page, '/?downPaymentPct=10');
  // $187.50 a month for the 109 months until the balance reaches 78% of the price.
  const bar = await page.evaluate(() => {
    const trace = document.getElementById('breakdown-chart').data[0];
    return trace.x[trace.y.indexOf('Mortgage insurance')];
  });
  expect(bar).toBeCloseTo(20437.5, 6);
});
