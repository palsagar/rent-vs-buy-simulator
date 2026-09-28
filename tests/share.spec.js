import { test, expect } from '@playwright/test';

/** Sharing a scenario, and what a shared link shows in a chat app. */

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

test('Share hands the current scenario to the native share sheet', async ({ page }) => {
  await load(page);
  await page.evaluate(() => {
    Object.defineProperty(navigator, 'share', {
      configurable: true,
      value: async (data) => { window.__shared = data; },
    });
    // Freeze the address bar: the shared link must come from the config,
    // not from a URL write that may still be pending.
    history.replaceState = () => {};
    const price = document.querySelector('#core-inputs input[type=range]');
    price.value = 750000;
    price.dispatchEvent(new Event('input'));
  });
  await page.click('#share-btn');
  const shared = await page.evaluate(() => window.__shared);
  expect(shared.title).toBe('Rent or buy?');
  expect(new URL(shared.url).searchParams.get('propertyPrice')).toBe('750000');
});

test('the shared link carries a typed price, not the slider position it snapped to', async ({ page }) => {
  await load(page);
  await page.evaluate(() => {
    Object.defineProperty(navigator, 'share', {
      configurable: true,
      value: async (data) => { window.__shared = data; },
    });
    history.replaceState = () => {};
  });
  await page.locator('#core-inputs .slider-value').first().click();
  const field = page.locator('#core-inputs .slider-typed').first();
  await field.fill('437,000');
  await field.press('Enter');
  await page.click('#share-btn');
  const shared = await page.evaluate(() => window.__shared);
  expect(new URL(shared.url).searchParams.get('propertyPrice')).toBe('437000');
});

test('without a share sheet, Share copies the link', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await load(page);
  await page.evaluate(() => {
    Object.defineProperty(navigator, 'share', { configurable: true, value: undefined });
  });
  await page.click('#share-btn');
  await expect(page.locator('#share-btn')).toHaveText('Link copied');
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toBe(new URL('/?r=us&v=2', page.url()).href);
});

test('cancelling the share sheet does nothing further', async ({ page }) => {
  await load(page);
  await page.evaluate(() => {
    window.__copies = 0;
    Object.defineProperty(navigator, 'share', {
      configurable: true,
      value: async () => { throw new DOMException('Share canceled', 'AbortError'); },
    });
    navigator.clipboard.writeText = async () => { window.__copies += 1; };
  });
  await page.click('#share-btn');
  // Let the click handler's promise chain settle before looking.
  await page.evaluate(() => new Promise((resolve) => setTimeout(resolve, 50)));
  expect(await page.evaluate(() => window.__copies)).toBe(0);
  await expect(page.locator('#share-btn')).toHaveText('Share this scenario');
});

test('when the share sheet fails, Share copies the link instead', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await load(page);
  await page.evaluate(() => {
    Object.defineProperty(navigator, 'share', {
      configurable: true,
      value: async () => { throw new DOMException('Not allowed', 'NotAllowedError'); },
    });
  });
  await page.click('#share-btn');
  await expect(page.locator('#share-btn')).toHaveText('Link copied');
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toBe(new URL('/?r=us&v=2', page.url()).href);
});

test('a second copy keeps Link copied for its own two seconds', async ({ page }) => {
  await page.clock.install();
  await load(page);
  await page.evaluate(() => {
    window.__copies = 0;
    Object.defineProperty(navigator, 'share', { configurable: true, value: undefined });
    navigator.clipboard.writeText = async () => { window.__copies += 1; };
  });
  const btn = page.locator('#share-btn');
  await btn.click();
  await expect(btn).toHaveText('Link copied');
  await page.clock.runFor(1500);
  await btn.click();
  await expect.poll(() => page.evaluate(() => window.__copies)).toBe(2);
  // Past the first click's two seconds, inside the second click's.
  await page.clock.runFor(1000);
  await expect(btn).toHaveText('Link copied');
  await page.clock.runFor(1500);
  await expect(btn).toHaveText('Share this scenario');
});

test('the page has a description and link-preview tags', async ({ page }) => {
  await page.goto('/');
  for (const sel of [
    'meta[name="description"]',
    'meta[property="og:title"]',
    'meta[property="og:description"]',
    'meta[property="og:image"]',
    'meta[name="twitter:card"]',
  ]) {
    await expect(page.locator(sel)).toHaveAttribute('content', /.+/);
  }
});

// Guard: the image already exists; this keeps the og:image path honest.
test('the og:image path is served by the app', async ({ request }) => {
  const res = await request.get('/screenshots/verdict.png');
  expect(res.ok()).toBe(true);
});

test('Plotly loads with defer so it does not block the first paint', async ({ page }) => {
  await page.goto('/');
  expect(await page.evaluate(() => document.querySelector('script[src*="plotly"]').defer)).toBe(true);
});
