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
    'Capped at',
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

const MINUS = '−';
const summaries = (page) => page.locator('.adv-group-values');

test('closed groups summarise the US values', async ({ page }) => {
  await boot(page);
  await expect(summaries(page)).toHaveText([
    'Buy 3% · Sell 6%',
    '≈ $12,200 in year 1',
    'On · 24% tax rate',
    'Tax-free up to $250k',
    '15% on gains',
  ]);
});

test('closed groups summarise the UK values, with and without the relief', async ({ page }) => {
  await boot(page);
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await expect(summaries(page)).toHaveText([
    'Buy 0% + £3,100 · Sell 1.75%',
    '≈ £3,602 in year 1',
    'Off',
    'Always tax-free',
    '24% on gains',
  ]);
  await page.locator('#ftb-pill .preset-btn').click();
  await expect(summaries(page).first()).toHaveText(`Buy 5% ${MINUS} £6,900 · Sell 1.75%`);
});

test('the Netherlands summary shows the yearly wealth tax', async ({ page }) => {
  await boot(page);
  await page.locator('#region-pills .preset-btn', { hasText: 'NL' }).click();
  await expect(summaries(page).last()).toHaveText('0% on gains · wealth tax 2.16%/yr');
});

test('a summary follows a typed value', async ({ page }) => {
  await boot(page);
  await openGroup(page, 'transaction');
  const row = field(page, 'closingCostSellerPct').locator('.slider-row');
  await row.locator('.slider-value').click();
  await row.locator('.slider-typed').fill('4.5');
  await row.locator('.slider-typed').press('Enter');
  await expect(summaries(page).first()).toHaveText('Buy 3% · Sell 4.5%');
});

test('switching the deduction off hides the two fields it controls', async ({ page }) => {
  await boot(page);
  await openGroup(page, 'mortgage-relief');
  await expect(field(page, 'marginalTaxRatePct')).toBeVisible();
  await expect(field(page, 'levyDeductionCap')).toBeVisible();
  await page.getByLabel('Deduct mortgage interest from income tax').uncheck();
  await expect(field(page, 'marginalTaxRatePct')).toBeHidden();
  await expect(field(page, 'levyDeductionCap')).toBeHidden();
  await expect(summaries(page).nth(2)).toHaveText('Off');
});

test('each home-sale rule shows only the fields it uses, and hidden values are still sent', async ({ page }) => {
  await boot(page);
  await openGroup(page, 'home-sale');
  const select = field(page, 'saleCgRegime').locator('select');
  const visible = async () => ({
    amount: await field(page, 'saleCgExemptAmount').isVisible(),
    years: await field(page, 'saleCgExemptAfterYears').isVisible(),
    rate: await field(page, 'saleCgRatePct').isVisible(),
  });
  expect(await visible()).toEqual({ amount: true, years: false, rate: true });
  await select.selectOption('exempt_after_years');
  await expect(field(page, 'saleCgExemptAfterYears')).toBeVisible();
  expect(await visible()).toEqual({ amount: false, years: true, rate: true });
  const sent = page.waitForRequest(
    (req) => req.url().endsWith('/api/simulate') && req.postDataJSON().saleCgRegime === 'fully_exempt',
  );
  await select.selectOption('fully_exempt');
  await expect(field(page, 'saleCgRatePct')).toBeHidden();
  expect(await visible()).toEqual({ amount: false, years: false, rate: false });
  expect((await sent).postDataJSON().saleCgRatePct).toBe(15);
});

test('each percentage-plus-fixed pair has one note under its fixed half', async ({ page }) => {
  await boot(page);
  const notes = page.locator('.adv-pair-note');
  await expect(notes).toHaveCount(3);
  for (const key of ['closingCostBuyerAmount', 'annualPropertyLevy', 'annualMaintenanceAmount']) {
    const next = await field(page, key).evaluate((el) => el.nextElementSibling?.className);
    expect(next).toContain('adv-pair-note');
  }
  await expect(notes.first()).toHaveText('Both apply. The total is the % of the price plus the fixed amount.');
});

const capButton = (page, name) => field(page, 'levyDeductionCap').getByRole('button', { name, exact: true });
const capQuery = (page) => new URL(page.url()).searchParams.get('levyDeductionCap');

test('the levy deduction choice stores no cap, a cap or not deductible', async ({ page }) => {
  await boot(page);
  await openGroup(page, 'mortgage-relief');
  const amount = field(page, 'levyDeductionCap').locator('.slider-row');
  // The US default is a $10,000 cap.
  await expect(capButton(page, 'Capped at…')).toHaveAttribute('aria-pressed', 'true');
  await expect(amount.locator('.slider-value')).toHaveText('$10,000');

  await capButton(page, 'No cap').click();
  await expect(amount).toBeHidden();
  await expect.poll(() => capQuery(page)).toBe('-1000');

  // 10,000 is the default config value, so the link leaves it out; the
  // last step reads the stored value instead.
  const stored = () => page.evaluate(async () => (await import('./js/state.js')).getConfig().levyDeductionCap);
  await capButton(page, 'Not deductible').click();
  await expect.poll(() => capQuery(page)).toBe('0');
  await expect.poll(stored).toBe(0);

  await capButton(page, 'Capped at…').click();
  await expect(amount.locator('.slider-value')).toHaveText('$10,000');
  await expect.poll(stored).toBe(10000);
});

for (const [value, choice] of [['-1000', 'No cap'], ['0', 'Not deductible'], ['25000', 'Capped at…']]) {
  test(`a shared link with levyDeductionCap=${value} opens on "${choice}"`, async ({ page }) => {
    await boot(page, `/?v=2&r=us&levyDeductionCap=${value}`);
    await openGroup(page, 'mortgage-relief');
    await expect(capButton(page, choice)).toHaveAttribute('aria-pressed', 'true');
    if (value === '25000') {
      await expect(field(page, 'levyDeductionCap').locator('.slider-value')).toHaveText('$25,000');
    }
  });
}

test('an old link with levyDeductionCap=0 and no version opens on "No cap"', async ({ page }) => {
  await boot(page, '/?levyDeductionCap=0');
  await openGroup(page, 'mortgage-relief');
  await expect(capButton(page, 'No cap')).toHaveAttribute('aria-pressed', 'true');
});
