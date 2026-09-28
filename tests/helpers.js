/**
 * Tour helpers shared by the spec files that walk the real 12-step STEPS
 * script. Not a spec file, so Playwright does not collect it as a test.
 */

export async function waitForPills(page) {
  await page.waitForFunction(() => document.querySelectorAll('#region-pills .preset-btn').length > 0);
}

/** Start a tour with the real 12-step STEPS script. */
export async function startRealTour(page) {
  await waitForPills(page);
  await page.evaluate(async () => {
    const { Tour, STEPS } = await import('./js/tour.js');
    window.__testTour = new Tour({ steps: STEPS });
    window.__testTour.start();
  });
  // Clear the beforeEach seed so the test's own flag writes are what gets asserted.
  await page.evaluate(() => localStorage.removeItem('rvb.tour.v1'));
}

/** Perform the gesture the current do-it step asks for. */
export async function performCurrentAction(page) {
  const idx = await page.evaluate(() => window.__testTour.stepIndex);
  switch (idx) {
    case 1: // region pill click
      await page.locator('#region-pills .preset-btn').first().click();
      break;
    case 3: // outlook pill click
      await page.locator('#outlook-pills .preset-btn').first().click();
      break;
    case 4: { // core-inputs change
      await page.evaluate(() => {
        const input = document.querySelector('#core-inputs input');
        const step = Number(input.step || 1);
        input.value = String(Math.min(Number(input.max), Number(input.value) + step));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      });
      break;
    }
    default:
      throw new Error(`step ${idx} is not a do-it step`);
  }
  await page.waitForFunction((i) => window.__testTour.stepIndex === i + 1, idx);
}
