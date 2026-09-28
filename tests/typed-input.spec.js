import { test, expect } from '@playwright/test';
import { startRealTour, performCurrentAction } from './helpers.js';

/** Typing an exact value by tapping a slider's value label. Desktop size
 *  (the inputs panel is always visible there), except the phone block. */

const PHONE = { viewport: { width: 390, height: 664 }, hasTouch: true, isMobile: true };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout: 20_000 },
  );
});

test('parseTypedNumber reads grouping and decimal separators', async ({ page }) => {
  const parsed = await page.evaluate(async () => {
    const { parseTypedNumber: p } = await import('./js/format.js');
    return [
      p('$437,000', true), p('437.000', true), p('437 000', true), p('−2,000', true),
      p('6.5', false), p('6,5', false), p('6.5%', false), p('1.234,5', false),
      p('abc', false), p('', true),
      // Whole-number fields: a lone separator groups digits only when
      // exactly three digits follow it; the result is rounded.
      p('7.5', true), p('12,5', true), p('1,234', true), p('1234.56', true),
      p('1,234.56', true),
      // A trailing k or M multiplies; any other letter is unreadable.
      p('450k', true), p('1.5M', true), p('2,5k', false), p('12abc', true), p('1e5', true),
    ];
  });
  expect(parsed).toEqual([
    437000, 437000, 437000, -2000, 6.5, 6.5, 6.5, 1234.5, NaN, NaN,
    8, 13, 1234, 1235, 1235,
    450000, 1500000, 2500, NaN, NaN,
  ]);
});

test('tapping the price value lets you type an exact price', async ({ page }) => {
  const value = page.locator('#core-inputs .slider-value').first();
  await value.click();
  const field = page.locator('#core-inputs .slider-typed').first();
  await expect(field).toBeVisible();
  await expect(field).toHaveAttribute('inputmode', 'decimal');
  await expect(field).toHaveValue('500000');
  await field.fill('437,000');
  const rerun = page.waitForRequest(
    (req) => req.url().endsWith('/api/simulate') && req.postDataJSON().propertyPrice === 437000,
  );
  await field.press('Enter');
  await rerun;
  await expect(value).toBeVisible();
  await expect(value).toHaveText('$437k');
});

test('a typed value outside the slider range is clamped to it', async ({ page }) => {
  await page.locator('#core-inputs .slider-value').first().click();
  const field = page.locator('#core-inputs .slider-typed').first();
  await field.fill('5000000');
  await field.press('Enter');
  await expect(page.locator('#core-inputs .slider-value').first()).toHaveText('$2.0M');
});

test('Escape cancels the typed value', async ({ page }) => {
  await page.locator('#core-inputs .slider-value').first().click();
  const field = page.locator('#core-inputs .slider-typed').first();
  await field.fill('999999');
  await field.press('Escape');
  await expect(page.locator('#core-inputs .slider-value').first()).toHaveText('$500k');
  await expect(field).toBeHidden();
});

test('leaving the field without an edit changes nothing', async ({ page }) => {
  // A hand-edited link can hold a value the whole-number rule would read
  // as digit grouping ("500000.123"), so an unedited field is not re-read.
  await page.goto('/?propertyPrice=500000.123');
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout: 20_000 },
  );
  let simulated = 0;
  page.on('request', (req) => {
    if (req.url().endsWith('/api/simulate')) simulated += 1;
  });
  const value = page.locator('#core-inputs .slider-value').first();
  const field = page.locator('#core-inputs .slider-typed').first();
  await value.click();
  await field.press('Enter');
  await expect(value).toBeVisible();
  await value.click();
  await field.blur();
  await expect(value).toBeVisible();
  await page.waitForTimeout(700); // past the 300 ms re-run debounce
  expect(simulated).toBe(0);
  await expect(value).toHaveText('$500k');
});

test('the typed field uses 16px text so iOS does not zoom the page', async ({ page }) => {
  await page.locator('#core-inputs .slider-value').first().click();
  const size = await page.locator('#core-inputs .slider-typed').first().evaluate((el) => getComputedStyle(el).fontSize);
  expect(size).toBe('16px');
});

test("the value button's accessible name includes the shown value", async ({ page }) => {
  const value = page.locator('#core-inputs .slider-value').first();
  await expect(value).toHaveAccessibleName('Home price $500k, type an exact value');
  // Dragging sets the shown value outside refresh(); the name must follow.
  await page.locator('#core-inputs input[type=range]').first().fill('600000');
  await expect(value).toHaveText('$600k');
  await expect(value).toHaveAccessibleName('Home price $600k, type an exact value');
});

test('in the tour, Escape in the field keeps the step and Enter completes it', async ({ page }) => {
  await startRealTour(page);
  while (await page.evaluate(() => window.__testTour.stepIndex) < 4) {
    const hasNext = await page.locator('.tour-footer .tour-btn-primary').count();
    if (hasNext) await page.locator('.tour-footer .tour-btn-primary').click();
    else await performCurrentAction(page);
    await page.waitForTimeout(100);
  }
  await expect(page.locator('.tour-title')).toHaveText('Your situation');
  const value = page.locator('#core-inputs .slider-value').first();
  const field = page.locator('#core-inputs .slider-typed').first();

  await value.click();
  await field.fill('450000');
  await field.press('Escape');
  await expect(field).toHaveCount(0);
  await page.waitForTimeout(300);
  expect(await page.evaluate(() => [window.__testTour.active, window.__testTour.stepIndex])).toEqual([true, 4]);

  await value.click();
  await field.fill('450000');
  await field.press('Enter');
  await expect(page.locator('.tour-counter')).toHaveText('6 / 12');
  await page.evaluate(() => window.__testTour.skip());
});

test.describe('phone', () => {
  test.use(PHONE);

  test('Escape in the field closes the field, not the inputs sheet', async ({ page }) => {
    await page.click('#inputs-btn');
    await expect(page.locator('#input-panel')).toHaveClass(/visible/);
    await page.locator('#core-inputs .slider-value').first().click();
    const field = page.locator('#core-inputs .slider-typed').first();
    await field.fill('450000');
    await field.press('Escape');
    await expect(field).toHaveCount(0);
    await expect(page.locator('#input-panel')).toHaveClass(/visible/);
  });

  test('the value is hidden while its field is open', async ({ page }) => {
    await page.click('#inputs-btn');
    const value = page.locator('#core-inputs .slider-value').first();
    await value.click();
    await expect(page.locator('#core-inputs .slider-typed')).toHaveCount(1);
    await expect(value).toBeHidden();
  });

  test('a slider name lines up with its value', async ({ page }) => {
    await page.click('#inputs-btn');
    // Measure the text itself: a stretched flex item's box would hide the offset.
    const [name, value] = await page.evaluate(() => {
      const header = document.querySelector('#core-inputs .slider-header');
      return ['.slider-name', '.slider-value'].map((sel) => {
        const range = document.createRange();
        range.selectNodeContents(header.querySelector(sel));
        const r = range.getBoundingClientRect();
        return r.top + r.height / 2;
      });
    });
    expect(Math.abs(name - value)).toBeLessThanOrEqual(2);
  });
});
