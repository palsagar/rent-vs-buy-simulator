import { test, expect } from '@playwright/test';
import { startRealTour, walkTo } from './helpers.js';

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

test('parseTypedNumber reads a k or M number with a decimal point, and dashes as minus', async ({ page }) => {
  const parsed = await page.evaluate(async () => {
    const { parseTypedNumber: p } = await import('./js/format.js');
    return [
      // Before k or M, a lone separator is the decimal point, even with
      // three digits after it.
      p('1.250M', true), p('0.475M', true), p('2.500k', true),
      // En dash and figure dash, as some keyboards type them.
      p('\u20132500', true), p('\u20122500', true),
    ];
  });
  expect(parsed).toEqual([1250000, 475000, 2500, -2500, -2500]);
});

test('parseTypedNumber rejects separators that do not group digits in threes', async ({ page }) => {
  const parsed = await page.evaluate(async () => {
    const { parseTypedNumber: p } = await import('./js/format.js');
    return [
      // Two separators in a row.
      p('5..0', false), p('1,,000', true), p('1.,5', false),
      // Grouping must split the digits into threes after a first group of
      // one to three digits.
      p('1.23.4', false), p('1,2,345', true), p('1234,000', true), p('1,2.5', false),
      // A grouping separator at either end.
      p('.500', true), p('1,000,', true),
      // Well-formed grouping still reads.
      p('1.234.567', false), p('1,234,567', true), p('1,234.56', true), p('-1.234,5', false),
      // A lone separator at either end that is a decimal point still reads.
      p('.5', false), p('5.', false), p(',5', false), p('500,', true),
      p('1,000.', true), p('1.000,', true),
    ];
  });
  expect(parsed).toEqual([
    NaN, NaN, NaN,
    NaN, NaN, NaN, NaN,
    NaN, NaN,
    1234567, 1234567, 1235, -1234.5,
    0.5, 5, 0.5, 500,
    1000, 1000,
  ]);
});

test('a typed value with malformed separators keeps the old value', async ({ page }) => {
  // "5..0" once read as 50, which the mortgage rate clamps to 10%.
  const row = page.locator('#core-inputs .slider-row', { hasText: 'Mortgage rate' });
  const before = await row.locator('.slider-value').textContent();
  await row.locator('.slider-value').click();
  const field = row.locator('.slider-typed');
  await field.fill('5..0');
  await field.press('Enter');
  await expect(row.locator('.slider-value')).toHaveText(before);
});

test('a typed negative levy cap is stored as uncapped, with the thumb at its left end', async ({ page }) => {
  // Any negative cap means uncapped, but the slider shows that only at its
  // minimum; -500 would leave the thumb on 0, "levy not deductible".
  await page.click('#advanced-btn');
  const row = page.locator('#advanced-inputs .slider-row', { hasText: 'Levy deduction cap' });
  await row.locator('.slider-value').click();
  const field = row.locator('.slider-typed');
  await field.fill('-500');
  await field.press('Enter');
  await expect(row.locator('.slider-value')).toHaveText('uncapped');
  await expect(row.locator('input[type=range]')).toHaveValue('-1000');
  await expect.poll(() => new URL(page.url()).searchParams.get('levyDeductionCap')).toBe('-1000');
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
  await walkTo(page, 4);
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
  // The tour moved focus to its next step; the closed field leaves it there.
  expect(await page.evaluate(() => document.querySelector('.tour-tooltip').contains(document.activeElement))).toBe(true);
  await page.evaluate(() => window.__testTour.skip());
});

/** Height of the first core slider row: closed, then with its typed field open. */
async function rowHeights(page) {
  const row = page.locator('#core-inputs .slider-row').first();
  const closed = (await row.boundingBox()).height;
  await row.locator('.slider-value').click();
  await expect(row.locator('.slider-typed')).toBeVisible();
  return { closed, open: (await row.boundingBox()).height };
}

test('opening the typed field keeps the row height, so the rows below stay put', async ({ page }) => {
  // A taller row would shrink back on the next mousedown and move the
  // value button under the pointer before mouseup, losing the click.
  const { closed, open } = await rowHeights(page);
  expect(Math.abs(open - closed)).toBeLessThanOrEqual(1);
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

  test('opening the typed field keeps the row height', async ({ page }) => {
    await page.click('#inputs-btn');
    const { closed, open } = await rowHeights(page);
    expect(Math.abs(open - closed)).toBeLessThanOrEqual(1);
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
