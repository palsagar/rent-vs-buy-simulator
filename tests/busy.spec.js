import { test, expect } from '@playwright/test';

/**
 * The busy state: while a result on screen is out of date for the live
 * config, its section fades back and an "Updating…" chip floats at the
 * top of the visible results. Seeded Monte Carlo makes the configs stable:
 *   ?propertyPrice=1295000 -> Renting ahead by ~$739,670
 */

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

/**
 * Keep a request pending: the server answers it, but the page gets the
 * answer only when `release()` is called. Later requests are held again.
 */
async function hold(page, path) {
  const held = [];
  await page.route(path, async (route) => {
    const response = await route.fetch();
    held.push(() => route.fulfill({ response }));
  });
  return {
    count: () => held.length,
    release: () => Promise.all(held.splice(0).map((answer) => answer())),
  };
}

/** Move the home price slider the way a drag does: an input event. */
async function dragPrice(page, value) {
  await page.evaluate((v) => {
    const price = document.querySelector('#core-inputs input[type=range]');
    price.value = v;
    price.dispatchEvent(new Event('input', { bubbles: true }));
  }, value);
}

const chip = (page) => page.locator('#results-spinner .busy-chip');

test('a pending Monte Carlo run dims its section and says the confidence is coming', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await load(page);
  const mc = await hold(page, '**/api/monte-carlo');
  await dragPrice(page, 1295000);

  const sure = page.locator('[data-result="monte-carlo"]');
  await expect(sure).toHaveClass(/stale/);
  await expect(sure).toHaveAttribute('aria-busy', 'true');
  await expect(chip(page)).toBeVisible();

  // The new verdict is on screen (a drag keeps the toss-up wording).
  await expect(page.locator('#verdict-line')).toContainText('~$739,670');
  await expect(page.locator('#verdict-hero')).not.toHaveClass(/stale/);
  await expect(page.locator('#verdict-pending')).toBeVisible();
  await expect(page.locator('#verdict-pending')).toHaveText(' · Checking how sure this is…');
  await expect(page.locator('#verdict-confidence')).toHaveText('');

  await expect.poll(mc.count).toBeGreaterThan(0);
  await mc.release();
  await expect(sure).not.toHaveClass(/stale/);
  await expect(sure).toHaveAttribute('aria-busy', 'false');
  await expect(chip(page)).toBeHidden();
  await expect(page.locator('#verdict-pending')).toBeHidden();
  await expect(page.locator('#verdict-confidence')).toContainText('% of simulated futures');
});

test('the chip stays in view when the results are scrolled', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await load(page);
  await hold(page, '**/api/monte-carlo');
  await dragPrice(page, 1295000);
  await page.evaluate(() => { document.getElementById('results').scrollTop = 1e6; });
  await expect(chip(page)).toBeVisible();
  const results = await page.locator('#results').boundingBox();
  const box = await chip(page).boundingBox();
  expect(box.y).toBeGreaterThanOrEqual(results.y);
  expect(box.y + box.height).toBeLessThanOrEqual(results.y + 60);
});

test.describe('on a phone', () => {
  test.use({ viewport: { width: 390, height: 664 }, hasTouch: true, isMobile: true });

  test('the chip stays at the top of the screen when the page is scrolled', async ({ page }) => {
    await load(page);
    await hold(page, '**/api/monte-carlo');
    await dragPrice(page, 1295000);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await expect(chip(page)).toBeVisible();
    const box = await chip(page).boundingBox();
    expect(box.y).toBeGreaterThanOrEqual(0);
    expect(box.y + box.height).toBeLessThanOrEqual(60);
  });
});

test('a failed run stops the chip but keeps the out-of-date results dimmed', async ({ page }) => {
  await load(page);
  await page.route('**/api/simulate', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) }),
  );
  await dragPrice(page, 1295000);
  await expect(page.locator('#error-banner')).toBeVisible();
  await expect(page.locator('#results-spinner')).not.toHaveClass(/visible/);
  await expect(page.locator('#verdict-hero')).toHaveClass(/stale/);
});

test('showing the chip never moves the cards', async ({ page }) => {
  await load(page);
  const top = () => page.evaluate(() => document.getElementById('verdict-hero').getBoundingClientRect().top);
  await expect(chip(page)).toBeHidden();
  const before = await top();
  const sim = await hold(page, '**/api/simulate');
  await dragPrice(page, 1295000);
  await expect(chip(page)).toBeVisible();
  expect(await top()).toBe(before);
  await sim.release();
});
