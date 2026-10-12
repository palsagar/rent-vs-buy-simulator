import { test, expect } from '@playwright/test';

/**
 * The "What could change the answer?" chart: the summary sentence above
 * it, the shared Buy - Rent axis with its tie line, the grouping, and the
 * tested values printed at the bar ends.
 *
 * Scenarios are US defaults with one share-link override each:
 *   - defaults:          a toss-up (buying wins in 46% of futures);
 *   - monthlyRent=1800:  renting ahead, two bars cross to buying;
 *   - monthlyRent=2000:  renting ahead, four bars cross to buying;
 *   - monthlyRent=3200:  buying ahead, no bar crosses.
 */

async function load(page, query = '') {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto(`/${query}`);
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout: 20_000 },
  );
}

/** Category names in the order a reader sees them, top to bottom. */
function rowsTopToBottom(page) {
  return page.evaluate(() =>
    [...document.getElementById('tornado-chart').layout.yaxis.categoryarray].reverse(),
  );
}

test.describe('the summary sentence', () => {
  test('a toss-up says so instead of naming bars', async ({ page }) => {
    await load(page);
    await expect(page.locator('#tornado-summary')).toHaveText(
      'The answer is too close to call, so small changes can tip it either way.',
    );
  });

  test('names each bar that flips the answer, with its tested value', async ({ page }) => {
    await load(page, '?monthlyRent=1800');
    await expect(page.locator('#tornado-summary')).toHaveText(
      /^Two of these could flip the answer to buying on their own: equity growth at \d+\.\d% instead of 7\.0%, or property appreciation at \d+\.\d% instead of 3\.0%\.$/,
    );
  });

  test('names only the three widest when more bars flip it', async ({ page }) => {
    await load(page, '?monthlyRent=2000');
    await expect(page.locator('#tornado-summary')).toHaveText(
      /^Four of these could flip the answer to buying on their own\. The biggest are [^,]+ at .+ instead of .+, [^,]+ at .+ instead of .+, and [^,]+ at .+ instead of .+\.$/,
    );
  });

  test('says when no single change flips the answer', async ({ page }) => {
    await load(page, '?monthlyRent=3200');
    await expect(page.locator('#tornado-summary')).toHaveText(
      'No single change here flips the answer. Buying stays ahead in every test.',
    );
  });
});

test('the sentence goes when a failed run drops the toss-up from the headline', async ({ page }) => {
  await load(page);
  await expect(page.locator('#tornado-summary')).toContainText('too close to call');
  await page.route('**/api/monte-carlo', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) }),
  );
  const input = page.locator('#core-inputs .slider-row', { hasText: 'Home price' }).locator('input');
  await input.fill('1295000');
  await input.evaluate((el) => el.dispatchEvent(new Event('input', { bubbles: true })));
  await expect(page.locator('#verdict-line')).toContainText('Renting leaves you');
  await expect(page.locator('#tornado-summary')).toHaveText('');
  await expect(page.locator('#tornado-summary')).toBeHidden();
});

test.describe('the chart', () => {
  test('has a plain-language title and no colour key to decode', async ({ page }) => {
    await load(page);
    const card = page.locator('#tornado-chart').locator('xpath=..');
    await expect(card).toContainText('What could change the answer?');
    await expect(card).not.toContainText('Purple');
    await expect(card).not.toContainText('stress-test');
  });

  test('$0 is the tie, on screen, with your verdict marked', async ({ page }) => {
    await load(page, '?monthlyRent=3200'); // buying ahead by ~$153k
    const { range, base, yourResult, labels } = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      const line = el.layout.shapes.find((s) => s.type === 'line' && s.name === 'you-are-here');
      return {
        range: el._fullLayout.xaxis.range,
        base: el.data[0].base,
        yourResult: line && line.x0,
        labels: el.layout.annotations.map((a) => a.text),
      };
    });
    expect(range[0]).toBeLessThan(0);
    expect(range[1]).toBeGreaterThan(0);
    expect(base).toBeGreaterThan(100_000);
    expect(yourResult).toBeCloseTo(base, 0);
    expect(labels).toContain('You are here');
    expect(labels.some((t) => t.includes('Renting ahead'))).toBe(true);
    expect(labels.some((t) => t.includes('Buying ahead'))).toBe(true);
  });

  test('bars use the input panel names, guesses about the future first', async ({ page }) => {
    await load(page);
    expect(await rowsTopToBottom(page)).toEqual([
      'Guesses about the future',
      'Equity growth (CAGR)',
      'Property appreciation',
      'Rent inflation',
      'Your numbers',
      'Monthly rent',
      'Home price',
      'Mortgage rate',
      'Property levy (% of value per year)',
      'Down payment',
    ]);
  });

  test('each bar end shows the value it tested', async ({ page }) => {
    await load(page);
    const ends = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      const row = el.data[0].y.indexOf('Home price');
      return el.data.map((t) => t.text[row]);
    });
    expect(ends.sort()).toEqual(['$400k', '$600k']);
  });

  test('a side clamped at a slider limit says which limit', async ({ page }) => {
    await load(page, '?downPaymentPct=47'); // +5 points would be 52%; the slider stops at 50%
    const sides = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      const row = el.data[0].y.indexOf('Down payment');
      return el.data.map((t) => ({ text: t.text[row], hover: t.customdata[row] }));
    });
    expect(sides[0].text).toBe('42%');
    expect(sides[0].hover).not.toContain('slider');
    expect(sides[1].text).toBe('50% (max)');
    expect(sides[1].hover).toMatch(
      /^Down payment at 50% instead of 47% \(the slider maximum\)<br>(Buying|Renting) ahead by /,
    );
  });

  test('no end label is marked when no test reaches a limit', async ({ page }) => {
    await load(page);
    const texts = await page.evaluate(() =>
      document.getElementById('tornado-chart').data.flatMap((t) => t.text),
    );
    expect(texts.filter((t) => /\((min|max)\)/.test(t))).toEqual([]);
  });

  test('a side stopped at its slider limit draws nothing', async ({ page }) => {
    await load(page, '?downPaymentPct=50'); // the slider maximum: it can only go down
    const sides = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      const row = el.data[0].y.indexOf('Down payment');
      return el.data.map((t) => ({ x: t.x[row], text: t.text[row], hover: t.customdata[row] }));
    });
    expect(sides[0].text).toBe('45%');
    expect(sides[1]).toEqual({ x: null, text: '', hover: '' });
  });

  test('both sides of a bar share one neutral colour', async ({ page }) => {
    await load(page);
    const colors = await page.evaluate(() =>
      document.getElementById('tornado-chart').data.map((t) => t.marker.color),
    );
    expect(new Set(colors).size).toBe(1);
    expect(colors[0]).not.toBe('#58a6ff');
    expect(colors[0]).not.toBe('#f0883e');
  });

  test('the hover reads as a sentence', async ({ page }) => {
    await load(page, '?monthlyRent=3200');
    const hover = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      const row = el.data[0].y.indexOf('Home price');
      return el.data.map((t) => t.customdata[row]);
    });
    for (const line of hover) {
      expect(line).toMatch(/^Home price at \$\d+k instead of \$500k<br>(Buying|Renting) ahead by /);
    }
  });

  test('a note explains how the test values are chosen', async ({ page }) => {
    await load(page);
    const note = page.locator('#tornado-note');
    await expect(note.locator('summary')).toHaveText('How are the test values chosen?');
    await note.locator('summary').click();
    await expect(note).toContainText('one number at a time');
  });
});

test.describe('on a phone', () => {
  test.use({ viewport: { width: 390, height: 664 } });

  test('bars get most of the chart width', async ({ page }) => {
    await load(page);
    const share = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      return el._fullLayout._size.w / el.clientWidth;
    });
    expect(share).toBeGreaterThan(0.75);
  });

  test('every row label, group headings included, is shown above its row', async ({ page }) => {
    await load(page);
    const { labels, rows } = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      return {
        labels: el.layout.annotations.filter((a) => a.name === 'row-label').map((a) => a.y),
        rows: el.layout.yaxis.categoryarray,
      };
    });
    expect([...labels].sort()).toEqual([...rows].sort());
  });

  test('the tested values at the bar ends stay inside the chart', async ({ page }) => {
    await load(page);
    const out = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      const box = el.getBoundingClientRect();
      const labels = [...el.querySelectorAll('text.bartext')].map((t) => t.getBoundingClientRect());
      return {
        count: labels.length,
        outside: labels.filter((r) => r.left < box.left || r.right > box.right).length,
      };
    });
    expect(out.count).toBe(16); // two ends on each of the 8 bars
    expect(out.outside).toBe(0);
  });
});
