import { test, expect } from '@playwright/test';

/**
 * Phone-size regressions: the preset bar layout, share-URL writes while a
 * slider is dragged, touch gestures on the charts and over an open overlay,
 * and the slider thumb.
 *
 * The viewport is an iPhone 13 with Safari's toolbars showing. Touch swipes
 * go through CDP because Playwright's touchscreen API only taps, so this
 * file needs Chromium -- Playwright's default browser, which the config
 * does not override.
 */

test.use({ viewport: { width: 390, height: 664 }, hasTouch: true, isMobile: true });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  // The confidence line is the last thing to render (Monte Carlo), so every
  // chart, the tornado included, exists once it has text.
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout: 20_000 },
  );
});

/** Drag one finger 200px upward from the centre of `selector`. */
async function swipeUp(page, selector) {
  const box = await page.locator(selector).boundingBox();
  const cdp = await page.context().newCDPSession(page);
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
  for (let i = 1; i <= 10; i++) {
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y: y - i * 20 }] });
    await page.waitForTimeout(16);
  }
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
}

test('preset bar controls stay on one row instead of stacking', async ({ page }) => {
  // Just above the phone breakpoint: the bar is still a bar, and narrower
  // than its contents, which is when the groups used to be squeezed.
  await page.setViewportSize({ width: 920, height: 700 });
  await expect(page.locator('#preset-bar #region-pills')).toHaveCount(1);
  const tops = await page.evaluate(() =>
    [...document.querySelectorAll('#preset-bar button')]
      .filter((b) => b.offsetParent !== null)
      .map((b) => Math.round(b.getBoundingClientRect().top)),
  );
  expect(new Set(tops).size).toBe(1);
});

/** Make history.replaceState throw the way Safari does past its limit. */
async function throttleHistoryLikeSafari(page) {
  // Safari throws once a page makes more than 100 history updates in 10 s.
  await page.evaluate(() => {
    history.replaceState = () => {
      throw new DOMException(
        'Attempt to use history.replaceState() more than 100 times per 10 seconds',
        'SecurityError',
      );
    };
  });
}

test('a failing share-URL write does not stop the simulation', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', (err) => pageErrors.push(err.message));
  await throttleHistoryLikeSafari(page);
  const rerun = page.waitForRequest(
    (req) => req.url().endsWith('/api/simulate') && req.postDataJSON().propertyPrice === 750000,
    { timeout: 5_000 },
  );
  await page.evaluate(() => {
    const price = document.querySelector('#core-inputs input[type=range]');
    price.value = 750000;
    price.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await rerun;
  // Past the 300 ms URL write too: a refused write is not an app error.
  await page.waitForTimeout(500);
  expect(pageErrors).toEqual([]);
});

test('a failing share-URL write does not stop a region switch', async ({ page }) => {
  await throttleHistoryLikeSafari(page);
  // The UK bundle carries a flat council-tax levy; the US one has none.
  const rerun = page.waitForRequest(
    (req) => req.url().endsWith('/api/simulate') && req.postDataJSON().annualPropertyLevy > 0,
    { timeout: 5_000 },
  );
  await page.evaluate(() => [...document.querySelectorAll('#region-pills .preset-btn')].find((b) => b.textContent === 'UK').click());
  await rerun;
});

test('a region switch writes its id and its numbers to the link together', async ({ page }) => {
  const written = await page.evaluate(async () => {
    const urls = [];
    const original = history.replaceState.bind(history);
    history.replaceState = (state, title, url) => {
      urls.push(String(url));
      return original(state, title, url);
    };
    [...document.querySelectorAll('#region-pills .preset-btn')]
      .find((b) => b.textContent === 'UK')
      .click();
    await new Promise((resolve) => setTimeout(resolve, 1000));
    return urls;
  });
  // A link that names the UK but still carries US numbers would reload as
  // a UK label over a US scenario.
  expect(written.length).toBeGreaterThan(0);
  for (const url of written) {
    const query = new URLSearchParams(url.split('?')[1]);
    expect(query.get('r')).toBe('uk');
    expect(Number(query.get('annualPropertyLevy'))).toBeGreaterThan(0);
  }
});

test('dragging a slider coalesces share-URL writes into one', async ({ page }) => {
  const result = await page.evaluate(async () => {
    let calls = 0;
    const original = history.replaceState.bind(history);
    history.replaceState = (...args) => {
      calls++;
      return original(...args);
    };
    const price = document.querySelector('#core-inputs input[type=range]');
    for (let i = 0; i < 150; i++) {
      price.value = 300000 + i * 5000;
      price.dispatchEvent(new Event('input', { bubbles: true }));
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
    return { calls, price: new URLSearchParams(location.search).get('propertyPrice') };
  });
  expect(result.calls).toBe(1);
  // The link still ends on the last value the slider reached.
  expect(result.price).toBe('1045000');
});

/** How far the content has scrolled, whichever element is scrolling it. */
function contentScroll(page) {
  return page.evaluate(() => window.scrollY + document.getElementById('results').scrollTop);
}

for (const chart of ['#decision-chart', '#tornado-chart']) {
  test(`a swipe that starts on ${chart} scrolls the page`, async ({ page }) => {
    await page.evaluate((sel) => document.querySelector(sel).scrollIntoView({ block: 'center' }), chart);
    const before = await contentScroll(page);
    await swipeUp(page, chart);
    await expect.poll(() => contentScroll(page)).toBeGreaterThan(before + 50);
  });
}

test.describe('an open overlay holds the page still', () => {
  // A swipe that did scroll the page can keep moving it for a moment
  // (momentum), so each check waits this long before reading the scroll.
  const SETTLE_MS = 500;

  test('a swipe in the Guide scrolls the Guide, not the page', async ({ page }) => {
    await page.click('#guide-btn');
    await expect(page.locator('#guide-overlay')).toBeVisible();
    // Closed sections: the Guide is shorter than the screen, so the whole
    // swipe goes past it.
    for (let i = 0; i < 4; i++) await swipeUp(page, '#guide-overlay .modal');
    await page.waitForTimeout(SETTLE_MS);
    expect(await page.evaluate(() => window.scrollY)).toBe(0);

    // Open sections: the Guide is taller than its box and scrolls inside.
    for (const header of await page.locator('.guide-section-header').all()) await header.click();
    await page.waitForTimeout(SETTLE_MS); // the sections expand over 0.3 s
    await swipeUp(page, '#guide-overlay .modal');
    await expect.poll(() => page.locator('#guide-overlay .modal').evaluate((el) => el.scrollTop)).toBeGreaterThan(50);
    expect(await page.evaluate(() => window.scrollY)).toBe(0);

    // Closed again, a swipe scrolls the page.
    await page.click('#guide-overlay .modal-close');
    await expect(page.locator('#guide-overlay')).toBeHidden();
    await swipeUp(page, '#verdict-hero');
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(50);
  });

  test('a swipe on the welcome modal does not scroll the page', async ({ context }) => {
    // A second page without the seeded tour flag, so the welcome shows.
    const fresh = await context.newPage();
    await fresh.addInitScript(() => {
      try { localStorage.removeItem('rvb.tour.v1'); } catch (e) {}
    });
    await fresh.goto('/');
    await expect(fresh.locator('#welcome-overlay')).toBeVisible();
    await fresh.waitForFunction(
      () => document.getElementById('verdict-confidence').textContent.length > 0,
      null,
      { timeout: 20_000 },
    );
    for (let i = 0; i < 4; i++) await swipeUp(fresh, '#welcome-overlay .modal');
    await fresh.waitForTimeout(SETTLE_MS);
    expect(await fresh.evaluate(() => window.scrollY)).toBe(0);
  });
});

test.describe('rotating a landscape phone to portrait', () => {
  // 844 px is still under the 900 px phone breakpoint, so the phone layout
  // applies before and after the turn.
  test.use({ viewport: { width: 844, height: 390 } });

  test('leaves no sideways scroll on the page', async ({ page }) => {
    // The numbers table is the widest thing that cannot shrink on its own.
    await page.locator('#numbers > summary').click();
    await expect(page.locator('#data-table table')).toBeVisible();

    await page.setViewportSize({ width: 390, height: 664 });
    // Charts re-lay out on the resize; the page is narrow again once they do.
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth))
      .toBeLessThanOrEqual(0);
  });
});

test('tapping a chart still shows its values', async ({ page }) => {
  await page.evaluate(() => document.getElementById('decision-chart').scrollIntoView({ block: 'center' }));
  const box = await page.locator('#decision-chart').boundingBox();
  await page.touchscreen.tap(box.x + box.width * 0.4, box.y + box.height / 2);
  await expect(page.locator('#decision-chart .hoverlayer')).toContainText('Buy');
});

test('the phone-size slider thumb rule survives CSS parsing', async ({ page }) => {
  // Chromium and WebKit (the engine in every iPhone browser) drop a whole
  // selector list that names a -moz- pseudo-element they do not know, so
  // the enlarged thumb has to be its own rule per engine.
  const width = await page.evaluate(() => {
    for (const sheet of document.styleSheets) {
      for (const rule of sheet.cssRules) {
        if (!rule.media?.mediaText.includes('max-width: 900px')) continue;
        for (const inner of rule.cssRules) {
          if (inner.selectorText?.includes('::-webkit-slider-thumb')) return inner.style.width;
        }
      }
    }
    return null;
  });
  expect(width).toBe('20px');
});
