import { test, expect } from '@playwright/test';
import { startRealTour, walkTo } from './helpers.js';

/**
 * Phone layout: the title bar, the controls that move into the inputs
 * sheet, the bottom sheets, page scrolling and touch targets. PHONE is an
 * iPhone 13 with Safari's toolbars showing.
 */

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

test.describe('phone: title bar', () => {
  test.use(PHONE);

  test('the app name fits on one line', async ({ page }) => {
    const box = await page.locator('#app-name').boundingBox();
    expect(box.height).toBeLessThan(30);
  });
});

test('the Advanced button does not use the error red', async ({ page }) => {
  const bg = await page.locator('#advanced-btn').evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(bg).not.toBe('rgb(218, 54, 51)');
});

test('the footer credits the author', async ({ page }) => {
  await expect(page.locator('footer a[href="https://github.com/palsagar"]')).toHaveCount(1);
});

test.describe('phone: controls move into the inputs panel', () => {
  test.use(PHONE);

  test('region, outlook and Advanced sit in the inputs panel; Guide in the title bar', async ({ page }) => {
    for (const sel of [
      '#input-panel #region-pills',
      '#input-panel #ftb-pill',
      '#input-panel #outlook-pills',
      '#input-panel #advanced-btn',
      '#title-bar #guide-btn',
    ]) {
      await expect(page.locator(sel)).toHaveCount(1);
    }
  });

  test('they return to the preset bar, in order, when the screen widens', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await expect(page.locator('#preset-bar #region-pills')).toHaveCount(1);
    const order = await page.evaluate(() =>
      [...document.getElementById('preset-bar').children]
        .map((c) => c.id)
        .filter((id) => ['region-group', 'outlook-group', 'advanced-btn', 'guide-btn'].includes(id)),
    );
    expect(order).toEqual(['region-group', 'outlook-group', 'advanced-btn', 'guide-btn']);
  });
});

/** Resolve once `id`'s slide transition has finished. */
async function waitForSlideAtRest(page, id) {
  await page.waitForFunction((elId) => {
    const t = getComputedStyle(document.getElementById(elId)).transform;
    return t === 'none' || /^matrix\(1, 0, 0, 1, -?0(?:\.0+)?, -?0(?:\.0+)?\)$/.test(t);
  }, id, { timeout: 5_000 });
}

test.describe('phone: inputs sheet', () => {
  test.use(PHONE);

  test('the Edit your numbers button stays pinned to the bottom of the screen', async ({ page }) => {
    const btn = page.locator('#inputs-btn');
    await expect(btn).toHaveText('Edit your numbers');
    for (const y of [0, 600]) {
      await page.evaluate((top) => {
        window.scrollTo(0, top);
        document.getElementById('results').scrollTo(0, top);
      }, y);
      const box = await btn.boundingBox();
      expect(box.y + box.height).toBeGreaterThan(664 - 80);
      expect(box.y + box.height).toBeLessThanOrEqual(664);
    }
  });

  test('the pinned button does not cover the tour target on The numbers step', async ({ page }) => {
    await startRealTour(page);
    await walkTo(page, 9);
    await expect(page.locator('.tour-title')).toHaveText('The numbers');
    const where = await page.evaluate(() => {
      const t = document.getElementById('numbers').getBoundingClientRect();
      const b = document.getElementById('inputs-btn').getBoundingClientRect();
      return {
        inView: t.top >= 0 && t.bottom <= innerHeight,
        overlap: t.top < b.bottom && b.top < t.bottom && t.left < b.right && b.left < t.right,
      };
    });
    expect(where).toEqual({ inView: true, overlap: false });
    await page.evaluate(() => window.__testTour.skip());
  });

  test('the inputs open as a full-width sheet from the bottom', async ({ page }) => {
    await page.click('#inputs-btn');
    await expect(page.locator('#input-panel')).toHaveClass(/visible/);
    await waitForSlideAtRest(page, 'input-panel');
    const box = await page.locator('#input-panel').boundingBox();
    expect(box.width).toBe(390);
    expect(Math.round(box.y + box.height)).toBe(664);
    expect(Math.round(box.height)).toBe(Math.round(664 * 0.6));
  });

  test('the sheet header is exactly 64px, even with a two-line verdict', async ({ page }) => {
    await page.click('#inputs-btn');
    await waitForSlideAtRest(page, 'input-panel');
    await page.evaluate(() => {
      document.getElementById('sheet-verdict').textContent =
        'Buying wins after 14 years, and the odds favour buying under this outlook';
    });
    const { header, verdict } = await page.evaluate(() => ({
      header: document.getElementById('sheet-header').getBoundingClientRect().height,
      verdict: document.getElementById('sheet-verdict').getBoundingClientRect().height,
    }));
    expect(header).toBe(64);
    // Two lines at 13px * 1.35: more than one line, and inside the header.
    expect(verdict).toBeGreaterThan(30);
    expect(verdict).toBeLessThan(header - 2);
  });

  test('Outlook is labelled once in the sheet, and the pills keep an accessible name', async ({ page }) => {
    await expect(page.locator('#sheet-outlook .preset-label')).toBeHidden();
    await expect(page.locator('#sheet-outlook').getByRole('group', { name: 'Outlook' })).toHaveCount(1);
    // On a wide screen the group returns to the preset bar with its label.
    await page.setViewportSize({ width: 1280, height: 800 });
    await expect(page.locator('#preset-bar #outlook-group .preset-label')).toBeVisible();
  });

  test('Done closes the sheet and its scrim', async ({ page }) => {
    await page.click('#inputs-btn');
    await waitForSlideAtRest(page, 'input-panel');
    await page.click('#sheet-done');
    await expect(page.locator('#input-panel')).not.toHaveClass(/visible/);
    await expect(page.locator('#drawer-scrim')).toBeHidden();
  });

  test('after Enter opens the sheet, Tab moves into the sheet', async ({ page }) => {
    await page.locator('#inputs-btn').focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('#input-panel')).toHaveClass(/visible/);
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => document.getElementById('input-panel').contains(document.activeElement))).toBe(true);
  });

  test('widening past the phone size with the sheet open closes the sheet and its scrim', async ({ page }) => {
    // A large iPhone turned to landscape is 932-956 px wide.
    await page.click('#inputs-btn');
    await expect(page.locator('#input-panel')).toHaveClass(/visible/);
    await page.setViewportSize({ width: 1280, height: 800 });
    await expect(page.locator('#drawer-scrim')).toBeHidden();
    await expect(page.locator('#input-panel')).not.toHaveClass(/visible/);
  });
});

test.describe('phone: live verdict in the sheet', () => {
  test.use(PHONE);

  test('the sheet shows a one-line verdict that follows the inputs', async ({ page }) => {
    await page.click('#inputs-btn');
    const line = page.locator('#sheet-verdict');
    await expect(line).toHaveText('Too close to call · ~$1,248 apart after 10 yrs');
    await page.evaluate(() => {
      const price = document.querySelector('#core-inputs input[type=range]');
      price.value = 1295000;
      price.dispatchEvent(new Event('input'));
    });
    await expect(line).toHaveText('Renting ahead by ~$739,670 after 10 yrs');
  });

  test('a failed Monte Carlo run drops the toss-up wording from the sheet too', async ({ page }) => {
    await page.route('**/api/monte-carlo', (route) =>
      route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) }),
    );
    await page.click('#inputs-btn');
    await page.evaluate(() => {
      const price = document.querySelector('#core-inputs input[type=range]');
      price.value = 1295000;
      price.dispatchEvent(new Event('input'));
    });
    await expect(page.locator('#error-banner')).toContainText('Monte Carlo failed: boom');
    await expect(page.locator('#sheet-verdict')).toHaveText('Renting ahead by ~$739,670 after 10 yrs');
  });
});

test.describe('phone: Advanced sheet', () => {
  test.use(PHONE);

  async function openBothSheets(page) {
    await page.click('#inputs-btn');
    await waitForSlideAtRest(page, 'input-panel');
    await page.locator('#advanced-btn').scrollIntoViewIfNeeded();
    await page.click('#advanced-btn');
    await expect(page.locator('#advanced-panel')).toHaveClass(/visible/);
    await waitForSlideAtRest(page, 'advanced-panel');
  }

  test('Advanced opens above the inputs sheet and leaves the live verdict in view', async ({ page }) => {
    await openBothSheets(page);
    const hit = await page.evaluate(() => {
      const adv = document.getElementById('advanced-panel');
      const verdict = document.getElementById('sheet-verdict');
      const a = adv.getBoundingClientRect();
      const v = verdict.getBoundingClientRect();
      return {
        width: a.width,
        onAdvanced: adv.contains(document.elementFromPoint(a.left + a.width / 2, a.top + a.height / 2)),
        verdictInView: verdict.contains(document.elementFromPoint(v.left + 10, v.top + v.height / 2)),
      };
    });
    expect(hit).toEqual({ width: 390, onAdvanced: true, verdictInView: true });
  });

  test('a tap on the scrim closes both sheets', async ({ page }) => {
    await openBothSheets(page);
    await page.mouse.click(195, 60);
    await expect(page.locator('#input-panel')).not.toHaveClass(/visible/);
    await expect(page.locator('#advanced-panel')).not.toHaveClass(/visible/);
  });

  test('Done closes both sheets and returns focus to the Edit your numbers button', async ({ page }) => {
    await openBothSheets(page);
    await page.click('#sheet-done');
    await expect(page.locator('#input-panel')).not.toHaveClass(/visible/);
    await expect(page.locator('#advanced-panel')).not.toHaveClass(/visible/);
    expect(await page.evaluate(() => document.activeElement.id)).toBe('inputs-btn');
  });

  test('the Advanced close button hands focus to the Advanced button', async ({ page }) => {
    await openBothSheets(page);
    await page.locator('#advanced-close').focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('#advanced-panel')).not.toHaveClass(/visible/);
    await expect(page.locator('#input-panel')).toHaveClass(/visible/);
    await expect(page.locator('#advanced-btn')).toBeFocused();
  });

  test('the tour closes the inputs sheet when it leaves the Advanced step', async ({ page }) => {
    await startRealTour(page);
    await walkTo(page, 8);
    // The Advanced step opens the inputs sheet, where the Advanced button lives.
    await expect(page.locator('#input-panel')).toHaveClass(/visible/);
    await walkTo(page, 9);
    await expect(page.locator('.tour-counter')).toHaveText('10 / 12');
    await expect(page.locator('#input-panel')).not.toHaveClass(/visible/);
    await expect(page.locator('#drawer-scrim')).toBeHidden();
    await page.evaluate(() => window.__testTour.skip());
  });

  // The spec's acceptance needs all 12 steps to complete at phone size,
  // with Region presets done by tapping a pill rather than by Next.
  test('the tour completes all 12 steps on a phone', async ({ page }) => {
    await startRealTour(page);
    const gestures = await walkTo(page, 12);
    expect(gestures).toContain(1);
    expect(await page.evaluate(() => window.__testTour.active)).toBe(false);
    expect(await page.evaluate(() => localStorage.getItem('rvb.tour.v1'))).toBe('done');
  });
});

/**
 * Where `sel` (or the tour ring, for '.tour-ring') sits against the part of
 * the inputs sheet that shows content: below its sticky header, down to the
 * bottom of the screen. `hit` is whether a tap at its centre reaches it.
 */
function sheetView(page, sel) {
  return page.evaluate((s) => {
    const el = document.querySelector(s);
    const r = el.getBoundingClientRect();
    const top = document.getElementById('sheet-header').getBoundingClientRect().bottom;
    const bottom = Math.min(innerHeight, document.getElementById('input-panel').getBoundingClientRect().bottom);
    const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return {
      inBand: r.height > 0 && r.top >= top - 1 && r.bottom <= bottom + 1,
      hit: s === '.tour-ring' || el.contains(at),
    };
  }, sel);
}

test.describe('phone: the tour inside the inputs sheet', () => {
  test.use(PHONE);

  test('Region presets shows no Next while the sheet slides open', async ({ page }) => {
    await startRealTour(page);
    await page.locator('.tour-footer .tour-btn-primary').click(); // Welcome → Region presets
    await expect(page.locator('.tour-title')).toHaveText('Region presets');
    // Counted at once, before the tour's re-check ~420 ms later.
    expect(await page.locator('.tour-footer .tour-btn-primary').count()).toBe(0);
    await page.waitForFunction(() => window.__testTour._recheckTimer == null);
    await expect(page.locator('.tour-footer .tour-btn-primary')).toHaveCount(0);
    await page.evaluate(() => window.__testTour.skip());
  });

  test('Back from Market outlook shows each earlier control below the sheet header', async ({ page }) => {
    await startRealTour(page);
    await walkTo(page, 3);
    await expect(page.locator('.tour-title')).toHaveText('Market outlook');
    await expect.poll(() => sheetView(page, '#outlook-pills')).toEqual({ inBand: true, hit: true });

    await page.locator('.tour-footer .tour-btn-secondary').click(); // Back
    await expect(page.locator('.tour-title')).toHaveText('First-time-buyer relief');
    await expect.poll(() => sheetView(page, '#ftb-pill')).toEqual({ inBand: true, hit: true });
    await expect.poll(() => sheetView(page, '.tour-ring')).toEqual({ inBand: true, hit: true });
    // The ring keeps its full 8px margin above the pill, not clipped by the header.
    await expect.poll(() => page.evaluate(() =>
      document.getElementById('ftb-pill').getBoundingClientRect().top
        - document.querySelector('.tour-ring').getBoundingClientRect().top,
    )).toBeCloseTo(8, 0);

    await page.locator('.tour-footer .tour-btn-secondary').click(); // Back
    await expect(page.locator('.tour-title')).toHaveText('Region presets');
    await expect.poll(() => sheetView(page, '#region-pills')).toEqual({ inBand: true, hit: true });
    // Still a do-it step: the pills are there to tap, so no Next button.
    await expect(page.locator('.tour-footer .tour-btn-primary')).toHaveCount(0);
    await page.evaluate(() => window.__testTour.skip());
  });

  test('the Your situation ring stays inside the part of the sheet below its header', async ({ page }) => {
    await startRealTour(page);
    await walkTo(page, 4);
    await expect(page.locator('.tour-title')).toHaveText('Your situation');
    await expect.poll(() => sheetView(page, '.tour-ring')).toEqual({ inBand: true, hit: true });
    await expect.poll(() => sheetView(page, '#core-inputs input')).toEqual({ inBand: true, hit: true });
    await page.evaluate(() => window.__testTour.skip());
  });

  test('Your situation shows the first value button below the sheet header', async ({ page }) => {
    // The step asks people to tap a value to type a number.
    await startRealTour(page);
    await walkTo(page, 4);
    await expect(page.locator('.tour-title')).toHaveText('Your situation');
    await expect.poll(() => sheetView(page, '#core-inputs .slider-value')).toEqual({ inBand: true, hit: true });
    await page.evaluate(() => window.__testTour.skip());
  });
});

test.describe('phone: page scrolling', () => {
  test.use(PHONE);

  test('the document scrolls, not an inner panel', async ({ page }) => {
    const y = await page.evaluate(() => {
      window.scrollTo(0, 400);
      return window.scrollY;
    });
    expect(y).toBe(400);
  });

  test('a scroll inside an open sheet does not move the page behind it', async ({ page }) => {
    const style = await page.evaluate(() => ({
      inputs: getComputedStyle(document.getElementById('input-panel')).overscrollBehaviorY,
      advanced: getComputedStyle(document.getElementById('advanced-panel')).overscrollBehaviorY,
      scrim: getComputedStyle(document.getElementById('drawer-scrim')).touchAction,
    }));
    expect(style).toEqual({ inputs: 'contain', advanced: 'contain', scrim: 'none' });
  });
});

test.describe('phone: touch targets and text size', () => {
  test.use(PHONE);

  test('mortgage-term buttons, checkbox rows and dropdowns are at least 44px tall', async ({ page }) => {
    const small = await page.evaluate(() =>
      [...document.querySelectorAll('.seg-btn, .checkbox-row, .select-row select')]
        .map((el) => ({ what: el.className || el.tagName, h: Math.round(el.getBoundingClientRect().height) }))
        .filter((x) => x.h < 44),
    );
    expect(small).toEqual([]);
  });

  test('the typed-value buttons are at least 28px tall', async ({ page }) => {
    const heights = await page.evaluate(() =>
      [...document.querySelectorAll('.slider-value')].map((el) => el.getBoundingClientRect().height),
    );
    expect(Math.min(...heights)).toBeGreaterThanOrEqual(28);
  });

  test('stat labels and slider hints are at least 12px', async ({ page }) => {
    const tiny = await page.evaluate(() =>
      [...document.querySelectorAll('.stat-label, .slider-hint')]
        .filter((el) => parseFloat(getComputedStyle(el).fontSize) < 12).length,
    );
    expect(tiny).toBe(0);
  });

  test('dropdowns use 16px text so iOS does not zoom on focus', async ({ page }) => {
    const sizes = await page.evaluate(() =>
      [...document.querySelectorAll('.select-row select')].map((el) => getComputedStyle(el).fontSize),
    );
    expect(sizes.length).toBeGreaterThan(0);
    expect(new Set(sizes)).toEqual(new Set(['16px']));
  });
});
