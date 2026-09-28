import { test, expect } from '@playwright/test';

/** Typing an exact value by tapping a slider's value label. Desktop size:
 *  the inputs panel is always visible there. */

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
    ];
  });
  expect(parsed).toEqual([
    437000, 437000, 437000, -2000, 6.5, 6.5, 6.5, 1234.5, NaN, NaN,
    8, 13, 1234, 1235, 1235,
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
