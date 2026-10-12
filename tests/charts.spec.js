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
