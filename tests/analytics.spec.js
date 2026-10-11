import { test, expect } from '@playwright/test';
import { startRealTour, walkTo } from './helpers.js';

/**
 * Umami analytics.
 *
 * The main Playwright webServer runs WITHOUT UMAMI_DOMAIN/UMAMI_ID, so the
 * tag is never injected there: (a) guards the inert-by-construction contract,
 * (b)-(c) pin the trackEvent wrapper contract. The "real tracker" tests at the
 * end use the second webServer, which injects the tag, and serve it the real
 * Umami script from tests/fixtures.
 */

test.describe('inert server', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  });

  test('(a) dev server injects no Umami tag', async ({ page }) => {
    await expect(page.locator('script[data-website-id]')).toHaveCount(0);
  });

  test('(b) trackEvent without window.umami does not throw', async ({ page }) => {
    const ok = await page.evaluate(async () => {
      const { trackEvent } = await import('./js/analytics.js');
      try {
        trackEvent('test-event');
        trackEvent('test-event', { foo: 1 });
        return true;
      } catch {
        return false;
      }
    });
    expect(ok).toBe(true);
  });

  test('(c) trackEvent forwards name and props to window.umami.track', async ({ page }) => {
    const calls = await page.evaluate(async () => {
      window.__umamiCalls = [];
      window.umami = { track: (n, p) => window.__umamiCalls.push([n, p]) };
      const { trackEvent } = await import('./js/analytics.js');
      trackEvent('test-event', { foo: 1 });
      return window.__umamiCalls;
    });
    expect(calls).toEqual([['test-event', { foo: 1 }]]);
  });
});

/** Stub window.umami before page scripts run; events land in window.__umamiCalls.
 *  addInitScript applies to the NEXT navigation, so each test below stubs
 *  first and then calls page.goto('/'). */
async function stubUmami(page) {
  await page.addInitScript(() => {
    window.__umamiCalls = [];
    window.umami = { track: (n, p) => window.__umamiCalls.push([n, p]) };
  });
}

/** Dismiss the first-visit welcome modal without starting the tour. */
async function dismissWelcome(page) {
  const skip = page.locator('#start-sim-btn');
  if (await skip.isVisible().catch(() => false)) await skip.click();
}

async function waitForPills(page) {
  await page.waitForFunction(() => document.querySelectorAll('#region-pills .preset-btn').length > 0);
}

async function eventNames(page) {
  return page.evaluate(() => window.__umamiCalls.map((c) => c[0]));
}

test('(d) tour start and skip fire tour-started / tour-skipped', async ({ page }) => {
  await stubUmami(page);
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await page.locator('#start-tour-btn').click();
  await expect.poll(() => eventNames(page)).toContain('tour-started');
  await page.keyboard.press('Escape');
  await expect.poll(() => eventNames(page)).toContain('tour-skipped');
});

test('region-changed fires with the selected region id', async ({ page }) => {
  await stubUmami(page);
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await dismissWelcome(page);
  await waitForPills(page);
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await expect.poll(() => page.evaluate(() => window.__umamiCalls))
    .toContainEqual(['region-changed', { region: 'uk' }]);
});

test('outlook-changed fires with the selected outlook key', async ({ page }) => {
  await stubUmami(page);
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await dismissWelcome(page);
  await page.locator('#outlook-pills .preset-btn', { hasText: 'Optimistic' }).click();
  await expect.poll(() => page.evaluate(() => window.__umamiCalls))
    .toContainEqual(['outlook-changed', { outlook: 'optimistic' }]);
});

test('ftb-toggled fires when the first-time-buyer pill is clicked', async ({ page }) => {
  await stubUmami(page);
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await dismissWelcome(page);
  await waitForPills(page);
  // The US region has no FTB relief, so switch to the UK first.
  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await page.locator('#ftb-pill .preset-btn').click();
  await expect.poll(() => page.evaluate(() => window.__umamiCalls))
    .toContainEqual(['ftb-toggled', { on: false }]);
});

test('restore-quiet: tour restore uses applyPreset, not synthetic clicks', async ({ page }) => {
  await stubUmami(page);
  await page.goto('/');
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await dismissWelcome(page);
  await waitForPills(page);

  await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
  await expect.poll(() => page.evaluate(() => window.__umamiCalls))
    .toContainEqual(['region-changed', { region: 'uk' }]);

  await page.evaluate(() => { window.__umamiCalls = []; });

  await page.evaluate(() => window.__rvb.tour.start());
  await expect.poll(() => eventNames(page)).toContain('tour-started');
  await page.keyboard.press('Escape');
  await expect.poll(() => eventNames(page)).toContain('tour-skipped');

  const names = await eventNames(page);
  expect(names).not.toContain('region-changed');
  expect(names).not.toContain('outlook-changed');
  expect(names).not.toContain('ftb-toggled');
});

// ── Real tracker ─────────────────────────────────────────────────────────
// The second webServer in playwright.config.js injects the tag for this
// fake Umami origin. Each test answers the origin's requests itself.
const TRACKED = 'http://127.0.0.1:8324';

/** Serve the real Umami script and record every payload it sends. */
async function fakeUmami(page) {
  const sent = [];
  await page.route('https://umami.test/script.js', (route) =>
    route.fulfill({ path: 'tests/fixtures/umami-script.js', contentType: 'text/javascript' }),
  );
  await page.route('https://umami.test/api/send', (route) => {
    const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type' };
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers: cors });
    sent.push(route.request().postDataJSON());
    return route.fulfill({ json: {}, headers: cors });
  });
  return sent;
}

/** Page views are the "event" payloads without a name. */
const pageViews = (sent) => sent.filter((s) => s.type === 'event' && !s.payload.name).map((s) => s.payload);
const events = (sent) => sent.filter((s) => s.payload.name).map((s) => [s.payload.name, s.payload.data]);
const named = (sent, name) => events(sent).filter(([n]) => n === name);

/** Load a tracked page with the tour already done, and wait for the app. */
async function openTracked(page, path = '/', options = {}) {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto(TRACKED + path, options);
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
  await waitForPills(page);
}

/** Like openTracked, but the Umami script waits until the app has rewritten
 *  the address bar: a tracker on a slow origin starts after that write. */
async function openTrackedLate(page, path) {
  let release;
  const held = new Promise((resolve) => { release = resolve; });
  // Registered after fakeUmami's route, so it runs first and then hands over.
  await page.route('https://umami.test/script.js', async (route) => {
    await held;
    await route.fallback();
  });
  const opened = openTracked(page, path, { waitUntil: 'commit' });
  const rewritten = () => page.url().startsWith(TRACKED) && page.url() !== TRACKED + path;
  await expect.poll(rewritten).toBe(true);
  release();
  await opened;
}

/** Drag the first core slider with the mouse, `dx` pixels from its middle. */
async function dragFirstSlider(page, dx = 40) {
  const box = await page.locator('#core-inputs input[type=range]').first().boundingBox();
  const y = box.y + box.height / 2;
  await page.mouse.move(box.x + box.width / 2, y);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + dx, y, { steps: 5 });
  await page.mouse.up();
}

/** After the step that would cause an extra send: long enough for the slider
 *  event's 500 ms debounce or Umami's 300 ms page-view delay, plus the fetch. */
const settle = (page) => page.waitForTimeout(800);

test.describe('real tracker', () => {
  test('one page view per load, without the app params', async ({ page }) => {
    const sent = await fakeUmami(page);
    await openTracked(page);
    await expect.poll(() => pageViews(sent).length).toBe(1);

    await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
    await dragFirstSlider(page);
    await expect.poll(() => named(sent, 'value-changed').length).toBe(1);
    // The app did rewrite the address bar, so the hook had page views to drop.
    await expect.poll(() => page.url()).toContain('r=uk');
    await settle(page);

    expect(pageViews(sent).map((p) => p.url)).toEqual([`${TRACKED}/`]);
    expect(events(sent)).toContainEqual(['region-changed', { region: 'uk' }]);
    for (const { payload } of sent) expect(payload.url).toBe(`${TRACKED}/`);
  });

  test('a campaign link keeps utm_* and drops the app params', async ({ page }) => {
    const sent = await fakeUmami(page);
    await openTracked(page, '/?utm_source=test&propertyPrice=500000', {
      referer: 'https://news.example/',
    });
    await expect.poll(() => pageViews(sent).length).toBe(1);
    // The app's next URL write drops utm_source; that is not a new page.
    await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
    await expect.poll(() => page.url()).toContain('r=uk');
    await settle(page);

    const views = pageViews(sent);
    expect(views.map((p) => p.url)).toEqual([`${TRACKED}/?utm_source=test`]);
    expect(views[0].referrer).toBe('https://news.example/');
  });

  test('advanced-opened fires on a real open only', async ({ page }) => {
    const sent = await fakeUmami(page);
    await openTracked(page);
    // The tour opens the drawer the same way: a programmatic click.
    await page.evaluate(() => document.getElementById('advanced-btn').click());
    await page.locator('#advanced-close').click();
    await page.locator('#advanced-btn').click();
    await page.locator('#advanced-close').click();
    await expect.poll(() => named(sent, 'advanced-opened').length).toBe(1);
    await settle(page);
    expect(named(sent, 'advanced-opened')).toEqual([['advanced-opened', undefined]]);
  });

  test('value-changed fires once per slider release and per typed value', async ({ page }) => {
    const sent = await fakeUmami(page);
    await openTracked(page);
    await dragFirstSlider(page);
    await expect.poll(() => named(sent, 'value-changed').length).toBe(1);

    const value = page.locator('#core-inputs .slider-value').first();
    await value.click();
    await page.locator('#core-inputs .slider-typed').first().fill('437000');
    await page.keyboard.press('Enter');
    await expect.poll(() => named(sent, 'value-changed').length).toBe(2);
    // The tour's do-it gesture in helpers.js: synthetic input and change.
    await page.evaluate(() => {
      const input = document.querySelector('#core-inputs input');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await settle(page);
    expect(named(sent, 'value-changed')).toEqual([
      ['value-changed', { field: 'propertyPrice', via: 'slider' }],
      ['value-changed', { field: 'propertyPrice', via: 'typed' }],
    ]);
  });

  test('link-shared fires on a real Share click only', async ({ page }) => {
    const sent = await fakeUmami(page);
    await openTracked(page);
    await page.evaluate(() => document.getElementById('share-btn').click());
    await page.locator('#share-btn').click();
    await expect.poll(() => named(sent, 'link-shared').length).toBe(1);
    await settle(page);
    expect(named(sent, 'link-shared')).toHaveLength(1);
  });

  test('two quick slider releases send two value-changed', async ({ page }) => {
    const sent = await fakeUmami(page);
    await openTracked(page);
    // Both releases land well inside the keyboard path's 500 ms debounce.
    await dragFirstSlider(page, 40);
    await dragFirstSlider(page, -40);
    await expect.poll(() => named(sent, 'value-changed').length).toBe(2);
    await settle(page);
    expect(named(sent, 'value-changed')).toEqual([
      ['value-changed', { field: 'propertyPrice', via: 'slider' }],
      ['value-changed', { field: 'propertyPrice', via: 'slider' }],
    ]);
  });

  test('arrow keys on a slider send one value-changed', async ({ page }) => {
    const sent = await fakeUmami(page);
    await openTracked(page);
    await page.locator('#core-inputs input[type=range]').first().focus();
    for (let i = 0; i < 10; i++) await page.keyboard.press('ArrowRight');
    await expect.poll(() => named(sent, 'value-changed').length).toBe(1);
    await settle(page);
    expect(named(sent, 'value-changed')).toEqual([
      ['value-changed', { field: 'propertyPrice', via: 'slider' }],
    ]);
  });

  test('a shared link sends link-opened once, beside one clean page view', async ({ page }) => {
    const sent = await fakeUmami(page);
    await openTracked(page, '/?propertyPrice=500000&r=uk&v=2');
    await expect.poll(() => named(sent, 'link-opened').length).toBe(1);
    // A click makes the app rewrite the address bar: a page view to drop.
    await page.locator('#region-pills .preset-btn', { hasText: 'US' }).click();
    await expect.poll(() => page.url()).not.toContain('r=uk');
    await settle(page);
    expect(pageViews(sent).map((p) => p.url)).toEqual([`${TRACKED}/`]);
    expect(named(sent, 'link-opened')).toEqual([['link-opened', undefined]]);
  });

  test('a plain visit sends no link-opened', async ({ page }) => {
    const sent = await fakeUmami(page);
    await openTracked(page);
    await expect.poll(() => pageViews(sent).length).toBe(1);
    await settle(page);
    expect(named(sent, 'link-opened')).toHaveLength(0);
  });

  test.describe('tracker starts after the first address-bar write', () => {
    test('a plain visit: one page view of / and no link-opened', async ({ page }) => {
      const sent = await fakeUmami(page);
      await openTrackedLate(page, '/');
      expect(page.url()).toContain('r=us');
      await expect.poll(() => pageViews(sent).length).toBe(1);
      await settle(page);
      expect(pageViews(sent).map((p) => p.url)).toEqual([`${TRACKED}/`]);
      expect(named(sent, 'link-opened')).toHaveLength(0);
    });

    test('a campaign link keeps utm_*', async ({ page }) => {
      const sent = await fakeUmami(page);
      await openTrackedLate(page, '/?utm_source=test');
      expect(page.url()).not.toContain('utm_source');
      await expect.poll(() => pageViews(sent).length).toBe(1);
      await settle(page);
      expect(pageViews(sent).map((p) => p.url)).toEqual([`${TRACKED}/?utm_source=test`]);
    });

    test('a shared link: one page view of / and one link-opened', async ({ page }) => {
      const sent = await fakeUmami(page);
      await openTrackedLate(page, '/?propertyPrice=500000&r=uk&v=2');
      await expect.poll(() => named(sent, 'link-opened').length).toBe(1);
      await settle(page);
      expect(pageViews(sent).map((p) => p.url)).toEqual([`${TRACKED}/`]);
      expect(named(sent, 'link-opened')).toEqual([['link-opened', undefined]]);
    });
  });

  test.describe('phone', () => {
    test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });

    test('opening the inputs sheet and tapping a region are both sent', async ({ page }) => {
      const sent = await fakeUmami(page);
      await openTracked(page);
      await page.locator('#inputs-btn').tap();
      await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).tap();
      await expect.poll(() => events(sent)).toContainEqual(['region-changed', { region: 'uk' }]);
      expect(named(sent, 'inputs-opened')).toHaveLength(1);
    });

    test("the tour's own clicks send no interaction events", async ({ page }) => {
      const sent = await fakeUmami(page);
      await openTracked(page);
      // Steps 1-4 sit in the inputs sheet, which the tour opens with a
      // programmatic click; step 4's gesture is a synthetic slider change.
      await startRealTour(page);
      await walkTo(page, 5);
      await page.evaluate(() => window.__testTour.skip());
      await expect.poll(() => named(sent, 'tour-skipped').length).toBe(1);
      await settle(page);
      const names = events(sent).map(([n]) => n);
      expect(names).toContain('tour-started');
      expect(names).not.toContain('inputs-opened');
      expect(names).not.toContain('value-changed');
    });
  });
});
