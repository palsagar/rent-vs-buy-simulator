import { test, expect } from '@playwright/test';

/**
 * Printing: a light page with a summary of the numbers, the verdict with
 * its caveats open, and the charts laid out at paper width. Playwright does
 * not fire beforeprint for emulated print media, so the tests fire it.
 */

test.use({ viewport: { width: 1280, height: 800 } });

async function load(page) {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout: 20_000 },
  );
}

async function startPrint(page) {
  await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
  await page.emulateMedia({ media: 'print' });
}

const chartWidth = (page) =>
  page.evaluate(() => document.querySelector('#decision-chart .main-svg').getBoundingClientRect().width);

test('the printed page shows your numbers and paper-width charts, without the controls', async ({ page }) => {
  await load(page);
  await startPrint(page);

  const summary = page.locator('#print-summary');
  await expect(summary).toBeVisible();
  for (const text of ['Your numbers', 'Home price', '$500k', 'Region', 'United States']) {
    await expect(summary).toContainText(text);
  }
  await expect(page.locator('#print-summary-link')).toContainText('Open this scenario online: http');
  for (const hidden of ['#input-panel', '#preset-bar', '#share-btn', '#csv-btn', '#numbers']) {
    await expect(page.locator(hidden)).toBeHidden();
  }
  await expect(page.locator('#region-caveats')).toHaveAttribute('open', '');
  const filter = await page.evaluate(() => getComputedStyle(document.querySelector('.chart')).filter);
  expect(filter).toContain('invert');
  expect(await page.locator('#decision-chart').evaluate((el) => el.getBoundingClientRect().width)).toBe(640);
  expect(await chartWidth(page)).toBe(640);
});

test('the screen is unchanged after printing', async ({ page }) => {
  await load(page);
  const before = await chartWidth(page);
  await startPrint(page);
  // As in a browser: the screen layout is back when afterprint fires.
  await page.emulateMedia({ media: 'screen' });
  await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));

  await expect(page.locator('#region-caveats')).not.toHaveAttribute('open', '');
  expect(await page.locator('#decision-chart').getAttribute('style')).toBeFalsy();
  expect(await chartWidth(page)).toBe(before);
});

test('the summary lists the Advanced values that differ from the region', async ({ page }) => {
  await load(page);
  await page.evaluate(() => {
    const row = [...document.querySelectorAll('#advanced-inputs .slider-row')]
      .find((r) => r.textContent.includes('Selling costs (% of price)'));
    const input = row.querySelector('input[type=range]');
    input.value = 4;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
  // The summary prints the numbers the results are for, so wait for them.
  await expect(page.locator('#verdict-hero')).toHaveClass(/stale/);
  await expect(page.locator('#verdict-hero')).not.toHaveClass(/stale/);
  await startPrint(page);
  const summary = page.locator('#print-summary');
  await expect(summary).toContainText('Changed in Advanced');
  await expect(summary).toContainText('Selling costs (% of price)');
});

test('the summary leaves out an Advanced value that does not apply', async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  // Mortgage insurance applies only below 20% down, so at 25% it is hidden.
  await page.goto('/?downPaymentPct=25&mortgageInsuranceRatePct=1&r=us&v=3');
  await page.waitForFunction(() => document.getElementById('verdict-confidence').textContent.length > 0);
  await startPrint(page);
  await expect(page.locator('#print-summary')).toBeVisible();
  await expect(page.locator('#print-summary')).not.toContainText('Mortgage insurance');
});

test('when the latest change failed, the page prints the numbers its results are for', async ({ page }) => {
  await load(page);
  await page.route('**/api/simulate', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) }),
  );
  await page.evaluate(() => {
    const price = document.querySelector('#core-inputs input[type=range]');
    price.value = 750000;
    price.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await expect(page.locator('#error-banner')).toBeVisible();
  await startPrint(page);
  const summary = page.locator('#print-summary');
  await expect(summary).toContainText('$500k');
  await expect(summary).not.toContainText('$750k');
  await expect(page.locator('#print-summary-link')).not.toContainText('propertyPrice=750000');
  await expect(page.locator('#print-stale')).toBeVisible();
  await expect(page.locator('#print-stale')).toHaveText('These results are for the numbers below, not your latest change.');
});

test('the relief values of the printed scenario do not count as changes', async ({ page }) => {
  await load(page);
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await expect(page.locator('#verdict-line')).toContainText('£');
  await expect(page.locator('#verdict-hero')).not.toHaveClass(/stale/);
  // £600k is above the relief's £500k ceiling; that result fails, so the
  // printout is the £289k scenario, where the relief applies.
  await page.route('**/api/simulate', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) }),
  );
  await page.evaluate(() => {
    const price = document.querySelector('#core-inputs input[type=range]');
    price.value = 600000;
    price.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await expect(page.locator('#error-banner')).toBeVisible();
  await startPrint(page);
  await expect(page.locator('#print-stale')).toBeVisible();
  await expect(page.locator('#print-summary')).not.toContainText('Buying costs');
});

test('an up-to-date page prints no stale notice', async ({ page }) => {
  await load(page);
  await startPrint(page);
  await expect(page.locator('#print-summary')).toBeVisible();
  await expect(page.locator('#print-stale')).toBeHidden();
});

test('the page prints to PDF', async ({ page, browserName }) => {
  test.skip(browserName !== 'chromium', 'page.pdf() is Chromium only');
  await load(page);
  await startPrint(page);
  // Printing to PDF fires its own beforeprint and afterprint inside ours.
  const pdf = await page.pdf({ format: 'A4' });
  expect(pdf.length).toBeGreaterThan(1000);
  await page.emulateMedia({ media: 'screen' });
  await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
  await expect(page.locator('#region-caveats')).not.toHaveAttribute('open', '');
});
