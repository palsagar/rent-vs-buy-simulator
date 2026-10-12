import { test, expect } from '@playwright/test';
import fs from 'node:fs';

/** The numbers table and its CSV download share one list of columns. */

const TABLE_HEADERS = [
  'Year',
  'Home value',
  'Portfolio (rent)',
  'Portfolio (buy)',
  'Mortgage balance',
  'Out of pocket (buy)',
  'Out of pocket (rent)',
  'Everything put in',
  'Net (buy)',
  'Net (rent)',
];

const CSV_HEADER =
  'Month,Year,Home value (USD),Portfolio rent side (USD),Portfolio buy side (USD),' +
  'Mortgage balance (USD),Out of pocket buy side (USD),Out of pocket rent side (USD),' +
  'Everything put in (USD),Net value buy side (USD),Net value rent side (USD)';

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

async function download(page) {
  const pending = page.waitForEvent('download');
  await page.locator('#csv-btn').click();
  const dl = await pending;
  return { name: dl.suggestedFilename(), text: fs.readFileSync(await dl.path(), 'utf8') };
}

test('the table has every value column, with the year you sell in bold', async ({ page }) => {
  await load(page);
  await page.locator('#numbers summary').click();
  await expect(page.locator('#data-table th')).toHaveText(TABLE_HEADERS);
  const cellCounts = await page.locator('#data-table tbody tr').evaluateAll((rows) =>
    rows.map((r) => r.cells.length),
  );
  expect(cellCounts.length).toBe(11);
  for (const n of cellCounts) expect(n).toBe(10);

  const last = page.locator('#data-table tbody tr').last();
  await expect(last).toHaveClass(/horizon-row/);
  await expect(last.locator('td').first()).toHaveText('10');
  await expect(page.locator('#numbers .numbers-note')).toHaveText(
    'One row per year. The last row, in bold, is the year you sell, which the verdict uses.',
  );
});

test('the CSV names its units and its scenario', async ({ page }) => {
  await load(page);
  await page.locator('#numbers summary').click();
  const { name, text } = await download(page);
  expect(name).toBe('rent-or-buy-us-10-years-500000.csv');
  expect(text.startsWith('﻿')).toBe(true);
  const lines = text.slice(1).split('\n');
  expect(lines[0]).toBe(CSV_HEADER);
  expect(lines.length).toBe(122);
  expect(lines[1].startsWith('0,0.0000,')).toBe(true);
  for (const line of lines.slice(1)) {
    const fields = line.split(',');
    expect(fields.length).toBe(11);
    for (const money of fields.slice(2)) expect(money).toMatch(/^-?\d+\.\d{2}$/);
  }
});

test('the CSV carries the region currency and name', async ({ page }) => {
  await load(page);
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await expect(page.locator('#verdict-line')).toContainText('£');
  await page.locator('#numbers summary').click();
  const { name, text } = await download(page);
  expect(text.split('\n')[0]).toContain('Home value (GBP)');
  expect(name).toMatch(/^rent-or-buy-uk-10-years-\d+\.csv$/);
});

test('the CSV names the scenario on screen, not a switch that failed', async ({ page }) => {
  await load(page);
  await page.route('**/api/simulate', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) }),
  );
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await expect(page.locator('#error-banner')).toBeVisible();
  await page.locator('#numbers summary').click();
  const { name, text } = await download(page);
  expect(name).toBe('rent-or-buy-us-10-years-500000.csv');
  expect(text.split('\n')[0]).toContain('Home value (USD)');
});

test('a result that lands after a region switch keeps the region it was asked for', async ({ page }) => {
  await load(page);
  // The $550k request is held until the UK switch, then answered inside
  // the switch's 300 ms wait; the UK request that follows fails.
  let held = null;
  await page.route('**/api/simulate', async (route) => {
    if (held === null) {
      const response = await route.fetch();
      held = () => route.fulfill({ response });
      return;
    }
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) });
  });
  await page.evaluate(() => {
    const price = document.querySelector('#core-inputs input[type=range]');
    price.value = 550000;
    price.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await expect.poll(() => held !== null).toBe(true);
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await held();
  await expect(page.locator('#error-banner')).toBeVisible();
  await page.locator('#numbers summary').click();
  const { name, text } = await download(page);
  expect(name).toBe('rent-or-buy-us-10-years-550000.csv');
  expect(text.split('\n')[0]).toContain('Home value (USD)');
});
