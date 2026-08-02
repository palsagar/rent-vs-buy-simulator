import { test, expect } from '@playwright/test';

/**
 * Share-URL restoration and fetch-abort error-banner hygiene (G1).
 *
 * Opening a deep share URL in a fresh tab must restore the config silently and
 * render the verdict — and a mid-flight request that is superseded/aborted must
 * never surface its abort as the "Reload" error banner. A genuinely failed
 * request still shows the banner.
 */

const DEEP_FR_QUERY =
  '?propertyPrice=290000&mortgageRateAnnual=3.45&monthlyRent=812' +
  '&mortgageTermYears=25&closingCostBuyerPct=6.958&propertyTaxRate=0' +
  '&annualHomeInsurance=220&annualMaintenancePct=0&annualPropertyLevy=1220' +
  '&annualMaintenanceAmount=1300&closingCostBuyerAmount=1300' +
  '&interestDeductionEnabled=false&marginalTaxRatePct=0&levyDeductionCap=0' +
  '&saleCgRegime=fully_exempt&saleCgExemptAmount=0&saleCgExemptAfterYears=30' +
  '&saleCgRatePct=36.2&portfolioCgRatePct=31.4&r=fr&v=2';

// The default config the app starts from on a bare '/', whose simulate result
// is cached by init on our first (real-network) load.
const DEFAULT_PRICE = '500000';

async function seedTourDone(page) {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
}

async function waitForApp(page) {
  await page.waitForFunction(() => window.__rvb?.tour, null, { timeout: 20_000 });
}

async function waitForInputs(page) {
  await page.waitForFunction(
    () => document.querySelectorAll('#core-inputs input').length > 0,
    null,
    { timeout: 20_000 },
  );
}

async function waitForVerdict(page) {
  await page.waitForFunction(
    () => (document.querySelector('#verdict-hero')?.textContent ?? '').trim().length > 0,
    null,
    { timeout: 20_000 },
  );
}

async function bannerVisible(page) {
  return page
    .locator('#error-banner')
    .evaluate((el) => el.classList.contains('visible'))
    .catch(() => false);
}

/** Move the first core slider (home price) by one step and dispatch input. */
async function bumpPrice(page) {
  await page.evaluate(() => {
    const input = document.querySelector('#core-inputs input');
    const step = Number(input.step || 1);
    input.value = String(Math.min(Number(input.max), Number(input.value) + step));
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

/** Set the first core slider (home price) to an exact value and dispatch input. */
async function setPrice(page, value) {
  const priceRow = page.locator('#core-inputs .slider-row', { hasText: 'Home price' });
  const input = priceRow.locator('input');
  await input.fill(value);
  await input.evaluate((el) => el.dispatchEvent(new Event('input', { bubbles: true })));
}

test('a deep FR share URL restores silently and renders the verdict', async ({ page }) => {
  await seedTourDone(page);
  await page.goto(DEEP_FR_QUERY);
  await waitForApp(page);
  await waitForVerdict(page);

  // No error banner on a clean first load.
  await expect(page.locator('#error-banner')).not.toHaveClass(/visible/);

  // Region + advanced params were honored (FR currency, non-default price).
  expect(await page.locator('#verdict-hero').textContent()).toContain('€');
});

test('a superseded request never surfaces its abort as the error banner', async ({ page }) => {
  // Slow /api/simulate so the initial request is still in flight when the
  // input changes, producing a superseding (aborted) request mid-load.
  await page.route('**/api/simulate', async (route) => {
    await new Promise((r) => setTimeout(r, 1200));
    route.continue();
  });
  await seedTourDone(page);
  await page.goto('/');
  await waitForApp(page);
  await waitForInputs(page);

  await bumpPrice(page); // supersedes the in-flight simulate

  // Sample the banner across the debounce + abort window; it must stay hidden.
  for (let i = 0; i < 6; i++) {
    await page.waitForTimeout(400);
    expect(await bannerVisible(page)).toBe(false);
  }

  // The superseding request renders results; the banner stays gone.
  await waitForVerdict(page);
  expect(await bannerVisible(page)).toBe(false);
  await expect(page.locator('#error-banner')).not.toHaveClass(/visible/);
});

test('an aborted-while-current request (cache-hit supersede) still shows no banner', async ({ page }) => {
  // Pins G1's root cause: an abort that rejects as a non-AbortError (Chromium's
  // "Failed to fetch" connection teardown) while the request is still the
  // "current" one used to leak into the banner. Seed the default config's
  // simulate result into the cache with a real load, then make aborted fetches
  // reject as TypeError so the leak reproduces the old guard.
  await seedTourDone(page);
  await page.goto('/');
  await waitForApp(page);
  await waitForVerdict(page); // default config is now cached

  // Swap fetch so simulate/monte-carlo stay pending until aborted and then
  // reject with a non-AbortError TypeError — the abort-induced teardown error
  // class the old `err.name !== "AbortError"` guard failed to recognize.
  await page.evaluate(() => {
    const orig = window.fetch.bind(window);
    window.fetch = (url, opts = {}) => {
      if (/\/api\/(simulate|monte-carlo)/.test(String(url))) {
        return new Promise((resolve, reject) => {
          const signal = opts.signal;
          const fail = () => {
            const e = new TypeError('Failed to fetch');
            e.name = 'TypeError';
            reject(e);
          };
          if (signal?.aborted) return fail();
          signal?.addEventListener('abort', fail, { once: true });
        });
      }
      return orig(url, opts);
    };
  });

  // Change to an un-cached price -> a simulate is now in flight (pending mock).
  await setPrice(page, '550000');
  await page.waitForTimeout(400); // debounced simulate(550000) fired

  // Change back to the cached default: the superseding runSimulate hits the
  // cache, aborts the in-flight request, and returns early — leaving that
  // request's controller still "current". Its abort must NOT show a banner.
  await setPrice(page, DEFAULT_PRICE);
  await page.waitForTimeout(800); // cache-hit supersede ran, request aborted

  await page.waitForTimeout(1500);
  expect(await bannerVisible(page)).toBe(false);
  await expect(page.locator('#error-banner')).not.toHaveClass(/visible/);
});
