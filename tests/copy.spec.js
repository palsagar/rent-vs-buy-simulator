import { test, expect } from '@playwright/test';

/** Text people read: plain language, and touch-friendly verbs. */

test('the welcome subtitle is plain language', async ({ page }) => {
  await page.goto('/'); // no tour flag, so the welcome shows
  await expect(page.locator('.welcome-hero-sub')).toHaveText(
    'Find out whether buying or renting leaves you wealthier',
  );
});

test('the Guide defines Net Value with exit costs and taxes', async ({ page }) => {
  await page.goto('/');
  const body = page.locator('#guide-b-netvalue');
  await expect(body).toContainText("Net Value = what you'd walk away with − everything you paid in");
  await expect(body).toContainText('selling costs');
  await expect(body).toContainText('any tax savings from deducting mortgage interest and levies');
  await expect(body).toContainText('the larger of the rent and the cost of owning');
  await expect(body).not.toContainText('Asset Value − Total Outflows');
});

test('no text tells a phone user to hover or click', async ({ page }) => {
  await page.goto('/');
  const texts = await page.evaluate(async () => {
    const { STEPS } = await import('./js/tour.js');
    const cards = [...document.querySelectorAll('.card-sub')].map((el) => el.textContent);
    return [...STEPS.map((s) => s.body), ...cards].join('\n');
  });
  expect(texts).not.toMatch(/\bhover\b(?! (over )?or tap)/i);
  expect(texts).not.toMatch(/(?<!tap or )\bclick\b/i);
});
