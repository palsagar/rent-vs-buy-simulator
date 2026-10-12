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
    'Mortgage insurance (% of loan)',
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

const changedCount = (page, id) => group(page, id).locator('.adv-group-changed');
const resetButton = (page, id) => group(page, id).locator('.adv-reset');

/** Type an exact value into an Advanced slider (its group must be open). */
async function typeAdvanced(page, key, text) {
  const row = field(page, key).locator('.slider-row').first();
  await row.locator('.slider-value').click();
  await row.locator('.slider-typed').fill(text);
  await row.locator('.slider-typed').press('Enter');
}

test('a changed field gets a dot, a default line and a count, and reset undoes it', async ({ page }) => {
  await boot(page);
  await openGroup(page, 'transaction');
  await expect(resetButton(page, 'transaction')).toBeHidden();
  await typeAdvanced(page, 'closingCostSellerPct', '4.5');
  const seller = field(page, 'closingCostSellerPct');
  await expect(seller.locator('.adv-changed-dot')).toBeVisible();
  await expect(seller.locator('.adv-changed-note')).toHaveText('Region default: 6.0%');
  await expect(changedCount(page, 'transaction')).toHaveText(' · 1 changed');
  await resetButton(page, 'transaction').click();
  await expect(seller.locator('.slider-value')).toHaveText('6.0%');
  await expect(seller.locator('.adv-changed-dot')).toBeHidden();
  await expect(changedCount(page, 'transaction')).toHaveText('');
  await expect(resetButton(page, 'transaction')).toBeHidden();
});

test('the first-time-buyer relief, on or off, never counts as a change', async ({ page }) => {
  await boot(page);
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await expect(changedCount(page, 'transaction')).toHaveText('');
  await page.locator('#ftb-pill .preset-btn').click();
  await expect(summaries(page).first()).toHaveText(`Buy 5% ${MINUS} £6,900 · Sell 1.75%`);
  await expect(changedCount(page, 'transaction')).toHaveText('');
});

test('switching region clears the markers', async ({ page }) => {
  await boot(page);
  await openGroup(page, 'transaction');
  await typeAdvanced(page, 'closingCostSellerPct', '4.5');
  await expect(changedCount(page, 'transaction')).toHaveText(' · 1 changed');
  await page.locator('#region-pills .preset-btn', { hasText: 'FR' }).click();
  await expect(changedCount(page, 'transaction')).toHaveText('');
});

test('a link that matches no region shows no markers and no reset', async ({ page }) => {
  await boot(page, '/?closingCostSellerPct=4.5&marginalTaxRatePct=33');
  await expect(page.locator('.adv-group-changed')).toHaveText(['', '', '', '', '']);
  for (const id of ['transaction', 'mortgage-relief']) {
    await openGroup(page, id);
    await expect(resetButton(page, id)).toBeHidden();
  }
  await expect(page.locator('.adv-changed-dot:visible')).toHaveCount(0);
});

test('a changed field that gets hidden is not counted, but reset restores it', async ({ page }) => {
  await boot(page);
  await openGroup(page, 'mortgage-relief');
  await typeAdvanced(page, 'marginalTaxRatePct', '33');
  await expect(changedCount(page, 'mortgage-relief')).toHaveText(' · 1 changed');
  await page.getByLabel('Deduct mortgage interest from income tax').uncheck();
  // Only the switch counts now; the hidden rate has no effect.
  await expect(changedCount(page, 'mortgage-relief')).toHaveText(' · 1 changed');
  await resetButton(page, 'mortgage-relief').click();
  await expect(page.getByLabel('Deduct mortgage interest from income tax')).toBeChecked();
  await expect(field(page, 'marginalTaxRatePct').locator('.slider-value')).toHaveText('24%');
  await expect(changedCount(page, 'mortgage-relief')).toHaveText('');
});

test('the tour restore re-derives the markers from the restored relief', async ({ page }) => {
  await boot(page);
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await page.locator('#ftb-pill .preset-btn').click(); // relief off
  await page.evaluate(async () => {
    const { snapshotSettings } = await import('./js/inputs.js');
    window.__snap = snapshotSettings();
  });
  await page.locator('#ftb-pill .preset-btn').click(); // relief on
  await page.evaluate(async () => {
    const { restoreSettings } = await import('./js/inputs.js');
    restoreSettings(window.__snap);
  });
  await expect(summaries(page).first()).toHaveText(`Buy 5% ${MINUS} £6,900 · Sell 1.75%`);
  await expect(changedCount(page, 'transaction')).toHaveText('');
});

test('a UK price above the relief ceiling does not mark the buying costs as changed', async ({ page }) => {
  await boot(page);
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  const price = page.locator('#core-inputs .slider-row', { hasText: 'Home price' });
  await price.locator('.slider-value').click();
  await price.locator('.slider-typed').fill('650000');
  await price.locator('.slider-typed').press('Enter');
  await expect(summaries(page).first()).toHaveText(`Buy 5% ${MINUS} £6,900 · Sell 1.75%`);
  await expect(changedCount(page, 'transaction')).toHaveText('');
});

test('the region default line shows the exact default when the rounded one would match the field', async ({ page }) => {
  await boot(page);
  await page.locator('#region-pills .preset-btn', { hasText: 'NL' }).click();
  await openGroup(page, 'mortgage-relief');
  await typeAdvanced(page, 'marginalTaxRatePct', '38');
  // The field shows 0 decimals, so a rounded default would also read "38%".
  await expect(field(page, 'marginalTaxRatePct').locator('.adv-changed-note')).toHaveText('Region default: 37.56%');
});

test('the region default line shows the exact amount when the compact one would match the field', async ({ page }) => {
  await boot(page);
  await openGroup(page, 'home-sale');
  await typeAdvanced(page, 'saleCgExemptAmount', '250400');
  // The field shows "$250k", so a compact default would also read "$250k".
  await expect(field(page, 'saleCgExemptAmount').locator('.adv-changed-note')).toHaveText('Region default: $250,000');
});

test('two different negative levy caps both mean no cap, so neither counts as a change', async ({ page }) => {
  // No shipped region defaults to "no cap", so give the US bundle one.
  await page.route('**/api/regions', async (route) => {
    const regions = await (await route.fetch()).json();
    regions.find((r) => r.id === 'us').taxPrimitives.levyDeductionCap = -1000;
    await route.fulfill({ json: regions });
  });
  await boot(page, '/?v=2&r=us&levyDeductionCap=-500');
  await openGroup(page, 'mortgage-relief');
  await expect(capButton(page, 'No cap')).toHaveAttribute('aria-pressed', 'true');
  await expect(field(page, 'levyDeductionCap').locator('.adv-changed-note')).toBeHidden();
  await expect(changedCount(page, 'mortgage-relief')).toHaveText('');
});

test('a one-year home-sale rule reads "1 yr"', async ({ page }) => {
  await boot(page);
  await openGroup(page, 'home-sale');
  await field(page, 'saleCgRegime').locator('select').selectOption('exempt_after_years');
  await typeAdvanced(page, 'saleCgExemptAfterYears', '1');
  await expect(summaries(page).nth(3)).toHaveText('Tax-free after 1 yr');
});

test('a keyboard reset leaves focus on the group header', async ({ page }) => {
  await boot(page);
  await openGroup(page, 'transaction');
  await typeAdvanced(page, 'closingCostSellerPct', '4.5');
  await resetButton(page, 'transaction').focus();
  await page.keyboard.press('Enter');
  await expect(resetButton(page, 'transaction')).toBeHidden();
  await expect(group(page, 'transaction').locator('summary')).toBeFocused();
});

test('the levy choice buttons are labelled as one group', async ({ page }) => {
  await boot(page);
  await openGroup(page, 'mortgage-relief');
  const choices = page.getByRole('group', { name: 'Levy is also deductible' });
  await expect(choices.getByRole('button')).toHaveText(['No cap', 'Capped at…', 'Not deductible']);
});

test.describe('phone text size', () => {
  test.use(PHONE);

  test('the Advanced summaries, notes, reset and levy choice are at least 12px', async ({ page }) => {
    await boot(page);
    await page.click('#inputs-btn');
    await openGroup(page, 'transaction');
    await typeAdvanced(page, 'closingCostSellerPct', '4.5');
    const tiny = await page.evaluate(() =>
      [...document.querySelectorAll('.adv-group-summary, .adv-changed-note, .adv-reset, .seg-picker--text .seg-btn')]
        .filter((el) => parseFloat(getComputedStyle(el).fontSize) < 12)
        .map((el) => el.className),
    );
    expect(tiny).toEqual([]);
  });
});

test.describe('first-time-buyer relief in a shared link', () => {
  const ftbPill = (page) => page.locator('#ftb-pill .preset-btn');
  const uk = (page) => page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  const shareLink = (page) =>
    page.evaluate(async () => (await import('./js/state.js')).shareUrl());
  const ftbParam = (link) => new URL(link).searchParams.get('ftb');

  /** Type an exact home price into the core price field. */
  async function typePrice(page, text) {
    const price = page.locator('#core-inputs .slider-row', { hasText: 'Home price' });
    await price.locator('.slider-value').click();
    await price.locator('.slider-typed').fill(text);
    await price.locator('.slider-typed').press('Enter');
  }

  test('an edited relief value opens with the relief still on (#51)', async ({ page }) => {
    await boot(page);
    await uk(page);
    await openGroup(page, 'transaction');
    await typeAdvanced(page, 'closingCostBuyerAmount', '4000');
    await expect(ftbPill(page)).toHaveClass(/active/);
    await expect(changedCount(page, 'transaction')).toHaveText(' · 1 changed');
    await expect(summaries(page).first()).toHaveText('Buy 0% + £4,000 · Sell 1.75%');

    const link = await shareLink(page);
    await boot(page, link);
    await expect(ftbPill(page)).toHaveClass(/active/);
    await expect(changedCount(page, 'transaction')).toHaveText(' · 1 changed');
    await expect(summaries(page).first()).toHaveText('Buy 0% + £4,000 · Sell 1.75%');
    await openGroup(page, 'transaction');
    await resetButton(page, 'transaction').click();
    await expect(summaries(page).first()).toHaveText('Buy 0% + £3,100 · Sell 1.75%');
    await expect(changedCount(page, 'transaction')).toHaveText('');
    expect(ftbParam(link)).toBe('1');
  });

  test('a price move keeps an edited relief value until the price crosses the ceiling', async ({ page }) => {
    await boot(page);
    await uk(page);
    await openGroup(page, 'transaction');
    await typeAdvanced(page, 'closingCostBuyerAmount', '4000');
    await typePrice(page, '400000');
    await expect(summaries(page).first()).toHaveText('Buy 0% + £4,000 · Sell 1.75%');
    // Above the ceiling the relief does not exist, so the base values apply.
    await typePrice(page, '650000');
    await expect(summaries(page).first()).toHaveText(`Buy 5% ${MINUS} £6,900 · Sell 1.75%`);
    await expect(ftbPill(page)).toHaveClass(/disabled/);
    // Back below it, the region's relief applies again, as a pill click would.
    await typePrice(page, '400000');
    await expect(summaries(page).first()).toHaveText('Buy 0% + £3,100 · Sell 1.75%');
    await expect(ftbPill(page)).toHaveClass(/active/);
  });

  test('relief off travels, even when the numbers look like the relief', async ({ page }) => {
    await boot(page);
    await uk(page);
    await ftbPill(page).click(); // relief off
    await openGroup(page, 'transaction');
    await typeAdvanced(page, 'closingCostBuyerPct', '0');
    await typeAdvanced(page, 'closingCostBuyerAmount', '3100');
    await expect(changedCount(page, 'transaction')).toHaveText(' · 2 changed');

    const link = await shareLink(page);
    await boot(page, link);
    await expect(ftbPill(page)).not.toHaveClass(/active/);
    await expect(changedCount(page, 'transaction')).toHaveText(' · 2 changed');
    await openGroup(page, 'transaction');
    await resetButton(page, 'transaction').click();
    await expect(summaries(page).first()).toHaveText(`Buy 5% ${MINUS} £6,900 · Sell 1.75%`);
    expect(ftbParam(link)).toBe('0');
  });

  test('a relief priced out by the ceiling still travels', async ({ page }) => {
    await boot(page);
    await uk(page);
    await typePrice(page, '650000');
    await expect(ftbPill(page)).toHaveClass(/disabled/);

    const link = await shareLink(page);
    await boot(page, link);
    await typePrice(page, '400000');
    await expect(ftbPill(page)).toHaveClass(/active/);
    await expect(summaries(page).first()).toHaveText('Buy 0% + £3,100 · Sell 1.75%');
    expect(ftbParam(link)).toBe('1');
  });

  test.describe('a link written before the setting was carried', () => {
    const ftbInAddressBar = (page) => () => new URL(page.url()).searchParams.get('ftb');

    test('infers the relief from the numbers and adds it to the address bar', async ({ page }) => {
      await boot(page, '/?closingCostBuyerPct=0&closingCostBuyerAmount=3100&r=uk&v=2');
      await expect(ftbPill(page)).toHaveClass(/active/);
      await expect.poll(ftbInAddressBar(page)).toBe('1');
    });

    test('above the ceiling, withdraws the relief values it carries', async ({ page }) => {
      await boot(page, '/?propertyPrice=650000&closingCostBuyerPct=0&closingCostBuyerAmount=3100&r=uk&v=2');
      const cfg = await page.evaluate(async () => (await import('./js/state.js')).getConfig());
      expect(cfg.closingCostBuyerPct).toBe(5);
      expect(cfg.closingCostBuyerAmount).toBe(-6900);
      await expect(ftbPill(page)).toHaveClass(/disabled/);
    });

    test('ignores a setting that is not 1 or 0', async ({ page }) => {
      await boot(page, '/?closingCostBuyerPct=0&closingCostBuyerAmount=3100&r=uk&ftb=yes&v=2');
      await expect(ftbPill(page)).toHaveClass(/active/);
      await expect.poll(ftbInAddressBar(page)).toBe('1');
    });
  });

  test('a hand-built link that states the relief without its numbers gets the relief values', async ({ page }) => {
    await boot(page, '/?r=uk&ftb=1&v=2');
    await expect(ftbPill(page)).toHaveClass(/active/);
    const cfg = await page.evaluate(async () => (await import('./js/state.js')).getConfig());
    expect([cfg.closingCostBuyerPct, cfg.closingCostBuyerAmount]).toEqual([0, 3100]);
    await expect(summaries(page).first()).toHaveText('Buy 0% + £3,100 · Sell 6%');
  });

  test('a relief stated off for a region without one does not carry over to the next region', async ({ page }) => {
    await boot(page, '/?r=us&ftb=0&v=2');
    await uk(page);
    await expect(ftbPill(page)).toHaveClass(/active/);
    await expect(summaries(page).first()).toHaveText('Buy 0% + £3,100 · Sell 1.75%');
  });

  test('regions without a relief carry no setting', async ({ page }) => {
    await boot(page);
    await uk(page);
    await page.locator('#region-pills .preset-btn', { hasText: 'US' }).click();
    expect(ftbParam(await shareLink(page))).toBeNull();
    await page.locator('#region-pills .preset-btn', { hasText: 'FR' }).click();
    expect(ftbParam(await shareLink(page))).toBe('1');
  });

  test('the tour restore keeps an edited relief value', async ({ page }) => {
    await boot(page);
    await uk(page);
    await openGroup(page, 'transaction');
    await typeAdvanced(page, 'closingCostBuyerAmount', '4000');
    await page.evaluate(async () => {
      const { snapshotSettings } = await import('./js/inputs.js');
      window.__snap = snapshotSettings();
    });
    await ftbPill(page).click(); // relief off
    await ftbPill(page).click(); // relief on, back to the region's values
    await page.evaluate(async () => {
      const { restoreSettings } = await import('./js/inputs.js');
      restoreSettings(window.__snap);
    });
    await expect(summaries(page).first()).toHaveText('Buy 0% + £4,000 · Sell 1.75%');
    await expect(ftbPill(page)).toHaveClass(/active/);
    await expect(changedCount(page, 'transaction')).toHaveText(' · 1 changed');
  });

  test.describe('phone', () => {
    test.use(PHONE);

    test('an edited relief value opens with the relief on in the inputs sheet', async ({ page }) => {
      // The seller cost is the UK value, so only the edited relief value counts.
      await boot(page, '/?closingCostBuyerPct=0&closingCostBuyerAmount=4000&closingCostSellerPct=1.75&r=uk&ftb=1&v=2');
      await page.click('#inputs-btn');
      await expect(page.locator('#input-panel #ftb-pill .preset-btn')).toHaveClass(/active/);
      await expect(changedCount(page, 'transaction')).toHaveText(' · 1 changed');
    });
  });
});
