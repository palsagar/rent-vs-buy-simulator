import { test, expect } from '@playwright/test';

/**
 * The error banner: a busy server (HTTP 503) is asked again on its own,
 * and a failure that remains says what failed and offers a retry that
 * does not reload the page. Seeded Monte Carlo makes the configs stable:
 *   ?propertyPrice=1295000 -> Renting leaves you ~$643,253 wealthier
 */

const BUSY = { status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Server busy — try again shortly' }) };
const BOOM = { status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) };

/** Seed the tour flag, and record whether the banner ever shows. */
async function prepare(page) {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
    window.__bannerSeen = false;
    document.addEventListener('DOMContentLoaded', () => {
      const banner = document.getElementById('error-banner');
      new MutationObserver(() => {
        if (banner.classList.contains('visible')) window.__bannerSeen = true;
      }).observe(banner, { attributes: true });
    });
  });
}

async function waitForConfidence(page, timeout = 20_000) {
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout },
  );
}

async function load(page) {
  await prepare(page);
  await page.goto('/');
  await waitForConfidence(page);
}

/** Count the requests made to one endpoint. */
function countRequests(page, path) {
  let n = 0;
  page.on('request', (req) => {
    if (req.url().endsWith(path)) n += 1;
  });
  return () => n;
}

/** Move the home price slider the way a drag does: an input event. */
async function dragPrice(page, value) {
  await page.evaluate((v) => {
    const price = document.querySelector('#core-inputs input[type=range]');
    price.value = v;
    price.dispatchEvent(new Event('input', { bubbles: true }));
  }, value);
}

const banner = (page) => page.locator('#error-banner');

test('a busy Monte Carlo run is asked again without showing the banner', async ({ page }) => {
  const mcRequests = countRequests(page, '/api/monte-carlo');
  let calls = 0;
  await page.route('**/api/monte-carlo', (route) => {
    calls += 1;
    return calls <= 2 ? route.fulfill(BUSY) : route.continue();
  });
  await prepare(page);
  await page.goto('/');
  await waitForConfidence(page, 10_000);
  await expect(page.locator('#verdict-confidence')).toContainText('% of simulated futures');
  expect(await page.evaluate(() => window.__bannerSeen)).toBe(false);
  expect(mcRequests()).toBe(3);
});

test('when the server stays busy, the banner offers Try again, which re-runs only Monte Carlo', async ({ page }) => {
  test.setTimeout(45_000);
  const mcRequests = countRequests(page, '/api/monte-carlo');
  const simRequests = countRequests(page, '/api/simulate');
  await page.route('**/api/monte-carlo', (route) => route.fulfill(BUSY));
  await prepare(page);
  await page.goto('/');

  await expect(banner(page)).toHaveText(
    /Couldn't work out how sure the answer is: the server is busy\. Try again in a moment\./,
    { timeout: 15_000 },
  );
  expect(mcRequests()).toBe(4);
  await expect(page.locator('#error-retry')).toBeVisible();
  await expect(page.locator('#error-reload')).toBeHidden();

  await page.unroute('**/api/monte-carlo');
  const simBefore = simRequests();
  await page.locator('#error-retry').click();
  await expect(banner(page)).toBeHidden();
  await expect(page.locator('#verdict-confidence')).toContainText('% of simulated futures');
  expect(simRequests()).toBe(simBefore);
});

test('a change during the wait cancels the retry silently', async ({ page }) => {
  const mcRequests = countRequests(page, '/api/monte-carlo');
  let first = null;
  await page.route('**/api/monte-carlo', (route) => {
    if (first === null) {
      first = route;
      return undefined;
    }
    return route.continue();
  });
  await prepare(page);
  await page.goto('/');
  await expect.poll(() => first !== null, { timeout: 20_000 }).toBe(true);
  await expect(page.locator('#verdict-line')).not.toBeEmpty();

  // The busy answer lands 400 ms after the drag, so the page is waiting to
  // ask again when the drag's own Monte Carlo run starts (600 ms after it).
  await dragPrice(page, 1295000);
  await page.waitForTimeout(400);
  await first.fulfill(BUSY);

  await expect(page.locator('#verdict-confidence')).toContainText('Renting wins in', { timeout: 20_000 });
  // Long enough for a retry that was not cancelled to be sent.
  await page.waitForTimeout(1500);
  expect(mcRequests()).toBe(2);
  expect(await page.evaluate(() => window.__bannerSeen)).toBe(false);
});

test('a failed update can be tried again', async ({ page }) => {
  await load(page);
  await page.route('**/api/simulate', (route) => route.fulfill(BOOM));
  await dragPrice(page, 1295000);
  await expect(banner(page)).toHaveText(/Couldn't update the results: boom/);

  await page.unroute('**/api/simulate');
  await page.locator('#error-retry').click();
  await expect(page.locator('#verdict-line')).toContainText('Renting leaves you');
  await expect(banner(page)).toBeHidden();
  await expect(page.locator('#verdict-confidence')).toContainText('% of simulated futures');
});

test('a change retires the banner for the config it left', async ({ page }) => {
  await load(page);
  const mcRequests = countRequests(page, '/api/monte-carlo');
  await page.route('**/api/monte-carlo', (route) => route.fulfill(BOOM));
  await dragPrice(page, 1295000);
  await expect(banner(page)).toHaveText(/Couldn't work out how sure the answer is: boom/);
  await expect.poll(mcRequests).toBe(1);

  // The next price's run is pending: the old failure no longer applies.
  await page.unroute('**/api/monte-carlo');
  const held = [];
  await page.route('**/api/monte-carlo', async (route) => {
    const response = await route.fetch();
    held.push(() => route.fulfill({ response }));
  });
  await dragPrice(page, 1300000);
  await expect(banner(page)).toBeHidden();
  await expect(page.locator('#results-spinner .busy-chip')).toBeVisible();

  await expect.poll(() => held.length).toBe(1);
  await Promise.all(held.map((answer) => answer()));
  await expect(page.locator('#verdict-confidence')).toContainText('% of simulated futures');
  expect(mcRequests()).toBe(2);
  expect(await banner(page).isVisible()).toBe(false);
});

for (const button of ['#error-dismiss', '#error-retry']) {
  test(`focus moves to the results when ${button} closes the banner`, async ({ page }) => {
    await load(page);
    await page.route('**/api/simulate', (route) => route.fulfill(BOOM));
    await dragPrice(page, 1295000);
    await expect(banner(page)).toBeVisible();
    await page.unroute('**/api/simulate');
    await page.locator(button).focus();
    await page.keyboard.press('Enter');
    await expect(banner(page)).toBeHidden();
    await expect(page.locator('#verdict-hero')).toBeFocused();
  });
}

test('trying an update again clears the Monte Carlo failure it will re-run', async ({ page }) => {
  await load(page);
  await page.route('**/api/simulate', (route) => route.fulfill(BOOM));
  await page.route('**/api/monte-carlo', (route) => route.fulfill(BOOM));
  await dragPrice(page, 1295000);
  await expect(banner(page)).toHaveText(/Couldn't update the results: boom/);
  await page.waitForResponse('**/api/monte-carlo');

  // The retried update stays pending: nothing should take the banner's place.
  await page.unroute('**/api/simulate');
  await page.unroute('**/api/monte-carlo');
  await page.route('**/api/simulate', () => {});
  await page.locator('#error-retry').click();
  await expect(banner(page)).toBeHidden();
  await page.waitForTimeout(300);
  expect(await banner(page).isVisible()).toBe(false);
});

test('a dismissed banner comes back on the next failure', async ({ page }) => {
  await load(page);
  await page.route('**/api/simulate', (route) => route.fulfill(BOOM));
  await dragPrice(page, 1295000);
  await expect(banner(page)).toBeVisible();
  await page.locator('#error-dismiss').click();
  await expect(banner(page)).toBeHidden();

  await dragPrice(page, 1300000);
  await expect(banner(page)).toBeVisible();
});

test('the banner is announced and sits above an open dialog', async ({ page }) => {
  await load(page);
  await expect(banner(page)).toHaveAttribute('role', 'alert');
  await page.locator('#guide-btn').click();
  await expect(page.locator('#guide-overlay')).toBeVisible();
  await page.route('**/api/monte-carlo', (route) => route.fulfill(BOOM));
  // The guide traps focus, so the value is set through the DOM.
  await dragPrice(page, 1295000);
  await expect(banner(page)).toHaveText(/Couldn't work out how sure the answer is: boom/);
  const onTop = await page.evaluate(() => {
    const b = document.getElementById('error-banner');
    const r = b.getBoundingClientRect();
    return b.contains(document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2));
  });
  expect(onTop).toBe(true);
});

test('a regions failure offers a reload', async ({ page }) => {
  await page.route('**/api/regions', (route) => route.fulfill(BOOM));
  await load(page);
  await expect(banner(page)).toHaveText(/Couldn't load the region settings, so the US defaults are shown\./);
  await expect(page.locator('#error-reload')).toBeVisible();
  await expect(page.locator('#error-retry')).toBeHidden();
});

test.describe('on a phone', () => {
  test.use({ viewport: { width: 390, height: 664 }, hasTouch: true, isMobile: true });

  test('the banner shows above the inputs sheet, with finger-sized buttons', async ({ page }) => {
    await load(page);
    await page.locator('#inputs-btn').click();
    await expect(page.locator('#input-panel')).toHaveClass(/visible/);
    await page.route('**/api/monte-carlo', (route) => route.fulfill(BOOM));
    await dragPrice(page, 1295000);
    await expect(banner(page)).toBeVisible();

    const geometry = await page.evaluate(() => {
      const b = document.getElementById('error-banner');
      const r = b.getBoundingClientRect();
      const buttons = [...b.querySelectorAll('button')]
        .filter((btn) => !btn.hidden)
        .map((btn) => btn.getBoundingClientRect().height);
      return {
        inside: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight,
        onTop: b.contains(document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)),
        buttons,
      };
    });
    expect(geometry.inside).toBe(true);
    expect(geometry.onTop).toBe(true);
    expect(geometry.buttons.length).toBeGreaterThan(0);
    for (const h of geometry.buttons) expect(h).toBeGreaterThanOrEqual(44);
  });
});
