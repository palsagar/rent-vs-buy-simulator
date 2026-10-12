import { test, expect } from '@playwright/test';

/** The region's caveats sit under the verdict, collapsed by default. */

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

async function regionNotes(page, id) {
  const regions = await (await page.request.get('/api/regions')).json();
  return regions.find((r) => r.id === id);
}

test('the caveats are one tap away under the verdict', async ({ page }) => {
  await load(page);
  const us = await regionNotes(page, 'us');
  const caveats = page.locator('#verdict-hero #region-caveats');
  await expect(caveats).toBeVisible();
  const count = us.notes.length;
  await expect(caveats.locator('summary')).toHaveText(
    `${count} ${count === 1 ? 'thing' : 'things'} to know about the United States numbers`,
  );
  const items = caveats.locator('li');
  await expect(items.first()).toBeHidden();
  await caveats.locator('summary').click();
  await expect(items).toHaveText(us.notes);
});

test('the summary counts the selected region’s caveats', async ({ page }) => {
  await load(page);
  const uk = await regionNotes(page, 'uk');
  expect(uk.notes.length).toBeGreaterThan(1);
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await expect(page.locator('#region-caveats summary')).toHaveText(
    `${uk.notes.length} things to know about the ${uk.label} numbers`,
  );
  await expect(page.locator('#region-caveats li')).toHaveCount(uk.notes.length);
});

test('the footer no longer holds the caveats', async ({ page }) => {
  await load(page);
  await expect(page.locator('footer #region-notes')).toHaveCount(0);
});

test('a link that matches no region shows no caveats', async ({ page }) => {
  await load(page, '?closingCostBuyerPct=9.9&propertyTaxRate=4.4&v=2');
  await expect(page.locator('#region-caveats')).toBeHidden();
});

test.describe('on a phone', () => {
  test.use({ viewport: { width: 390, height: 664 }, hasTouch: true, isMobile: true });

  test('the summary is finger-sized', async ({ page }) => {
    await load(page);
    const box = await page.locator('#region-caveats summary').boundingBox();
    expect(box.height).toBeGreaterThanOrEqual(44);
  });
});
