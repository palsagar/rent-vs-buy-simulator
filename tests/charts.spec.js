import { test, expect } from '@playwright/test';

/** Chart geometry and readouts. Default config: 10-year horizon. */

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

test('the net value chart x-axis ends at the horizon', async ({ page }) => {
  await load(page);
  const range = await page.evaluate(() => document.getElementById('decision-chart')._fullLayout.xaxis.range);
  expect(range[0]).toBeCloseTo(0, 5);
  expect(range[1]).toBeCloseTo(10, 5);
});

test('the Buy and Rent end labels never overprint', async ({ page }) => {
  await load(page); // the two end values are $28,656 apart
  const overlap = await page.evaluate(() => {
    const [a, b] = [...document.querySelectorAll('#decision-chart .annotation-text')]
      .filter((t) => t.textContent === 'Buy' || t.textContent === 'Rent')
      .map((t) => t.getBoundingClientRect());
    return a.top < b.bottom && b.top < a.bottom && a.left < b.right && b.left < a.right;
  });
  expect(overlap).toBe(false);
});

test('the hover readout shows the year with one decimal', async ({ page }) => {
  await load(page);
  const box = await page.locator('#decision-chart').boundingBox();
  await page.mouse.move(box.x + box.width * 0.4, box.y + box.height / 2);
  const hover = page.locator('#decision-chart .hoverlayer');
  await expect(hover).toContainText('Buy');
  expect(await hover.textContent()).not.toMatch(/\d\.\d{2,}/);
});

async function hoverChart(page, id) {
  const box = await page.locator(`#${id}`).boundingBox();
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
  await expect(page.locator(`#${id} .modebar`)).toBeVisible();
  return page.locator(`#${id} .modebar-btn`);
}

test('a time-series chart offers zoom, pan, reset and save on hover', async ({ page }) => {
  await load(page);
  const buttons = await hoverChart(page, 'decision-chart');
  await expect(buttons).toHaveCount(4);
  const titles = await buttons.evaluateAll((els) => els.map((b) => b.getAttribute('data-title')));
  expect(titles).toEqual(['Zoom', 'Pan', 'Reset axes', 'Save as image']);
});

test('a bar chart only offers to save it', async ({ page }) => {
  await load(page);
  const buttons = await hoverChart(page, 'tornado-chart');
  await expect(buttons).toHaveCount(1);
  await expect(buttons).toHaveAttribute('data-title', 'Save as image');
});

test('Save as image downloads a named picture of the chart', async ({ page }) => {
  await load(page);
  await hoverChart(page, 'decision-chart');
  const download = page.waitForEvent('download');
  await page.locator('#decision-chart .modebar-btn[data-title="Save as image"]').click();
  expect((await download).suggestedFilename()).toBe('rent-or-buy-net-value.png');
});

test('zoom narrows the chart and Reset axes restores it', async ({ page }) => {
  await load(page);
  const buttons = await hoverChart(page, 'decision-chart');
  await page.locator('#decision-chart .modebar-btn[data-title="Zoom"]').click();
  const box = await page.locator('#decision-chart .nsewdrag').boundingBox();
  await page.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.6, { steps: 8 });
  await page.mouse.up();
  const range = () => page.evaluate(() => document.getElementById('decision-chart')._fullLayout.xaxis.range);
  await expect.poll(async () => (await range())[1] - (await range())[0]).toBeLessThan(5);
  await hoverChart(page, 'decision-chart');
  await page.locator('#decision-chart .modebar-btn[data-title="Reset axes"]').click();
  await expect.poll(async () => (await range())[1]).toBeCloseTo(10, 5);
  expect((await range())[0]).toBeCloseTo(0, 5);
  await expect(buttons).toHaveCount(4);
});

test('the tornado tap line stays hidden with a mouse', async ({ page }) => {
  await load(page);
  await expect(page.locator('#tornado-detail')).toBeHidden();
});

test.describe('on a phone', () => {
  test.use({ viewport: { width: 390, height: 664 } });

  test('the breakeven label stays inside the plot when it falls near the horizon', async ({ page }) => {
    await load(page); // default config: breakeven at 7.0 years, on a 10-year horizon
    const { labelRight, plotRight } = await page.evaluate(() => {
      const el = document.getElementById('decision-chart');
      const label = [...el.querySelectorAll('.annotation-text')]
        .find((t) => t.textContent.startsWith('breakeven'));
      const size = el._fullLayout._size;
      return {
        labelRight: label.getBoundingClientRect().right,
        plotRight: el.getBoundingClientRect().left + size.l + size.w,
      };
    });
    expect(labelRight).toBeLessThanOrEqual(plotRight);
  });
});
