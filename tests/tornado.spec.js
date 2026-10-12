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
    expect(await page.evaluate(() =>
      document.getElementById('tornado-chart').layout.annotations.filter((a) => a.name === 'limit-label').length,
    )).toBe(0);
  });

  test('a side already at its slider limit is labelled at your verdict', async ({ page }) => {
    await load(page, '?downPaymentPct=50'); // the slider maximum: it can only go down
    const { sides, labels, base } = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      const row = el.data[0].y.indexOf('Down payment');
      return {
        sides: el.data.map((t) => ({ x: t.x[row], text: t.text[row], hover: t.customdata[row] })),
        labels: el.layout.annotations.filter((a) => a.name === 'limit-label'),
        base: el.data[0].base,
      };
    });
    expect(sides[0].text).toBe('45%');
    expect(sides[1]).toEqual({ x: null, text: '', hover: '' }); // still no bar
    expect(labels).toHaveLength(1);
    expect(labels[0]).toMatchObject({
      y: 'Down payment',
      x: base,
      text: '50% (max)',
      hovertext: "Down payment is already at its slider maximum, so it can't be tested higher.",
    });
    await expect(page.locator('#tornado-chart .annotation-text', { hasText: '50% (max)' })).toBeVisible();
  });

  test('a limit label hovers in the same style as the bars', async ({ page }) => {
    await load(page, '?downPaymentPct=50');
    const { label, bar } = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      return {
        label: el.layout.annotations.find((a) => a.name === 'limit-label').hoverlabel?.bgcolor,
        bar: el.data[0].marker.color,
      };
    });
    expect(label).toBe(bar);
  });

  test('a limit hover names the row as the summary does, without its bracketed qualifier', async ({ page }) => {
    await load(page, '?equityGrowthAnnual=13'); // the higher test stops at the 15% maximum
    const hover = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      return el.data[1].customdata[el.data[1].y.indexOf('Equity growth (CAGR)')];
    });
    expect(hover).toMatch(/^Equity growth at 15\.0% instead of 13\.0% \(the slider maximum\)<br>/);

    await load(page, '?propertyTaxRate=5'); // the slider maximum: it can only go down
    const labels = await page.evaluate(() =>
      document.getElementById('tornado-chart').layout.annotations.filter((a) => a.name === 'limit-label'),
    );
    expect(labels).toHaveLength(1);
    expect(labels[0].hovertext).toBe("Property levy is already at its slider maximum, so it can't be tested higher.");
  });

  test('a side already at its slider minimum says so', async ({ page }) => {
    await load(page, '?monthlyRent=500'); // the slider minimum: it can only go up
    const labels = await page.evaluate(() =>
      document.getElementById('tornado-chart').layout.annotations.filter((a) => a.name === 'limit-label'),
    );
    expect(labels).toHaveLength(1);
    expect(labels[0]).toMatchObject({
      y: 'Monthly rent',
      text: '$500 (min)',
      hovertext: "Monthly rent is already at its slider minimum, so it can't be tested lower.",
    });
  });

  test('the summary never carries a limit mark', async ({ page }) => {
    for (const query of ['?downPaymentPct=50', '?downPaymentPct=47', '?monthlyRent=500', '?propertyPrice=1900000']) {
      await load(page, query);
      await expect(page.locator('#tornado-summary')).not.toContainText(/\((min|max)\)/);
    }
  });

  test('a clamped side that flips the verdict is named without its mark', async ({ page }) => {
    // Buying is ahead in 68% of futures. +20% on the home price would be
    // $2.04M; the slider stops at $2.0M, and there renting is ahead.
    await load(page, '?propertyPrice=1700000&monthlyRent=9750');
    const summary = page.locator('#tornado-summary');
    await expect(summary).toContainText('could flip the answer to renting');
    await expect(summary).toContainText('home price at $2.0M instead of $1.7M');
    await expect(summary).not.toContainText(/\((min|max)\)/);
    const ends = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      const row = el.data[0].y.indexOf('Home price');
      return el.data.map((t) => t.text[row]);
    });
    expect(ends).toContain('$2.0M (max)');
  });

  test('the note says how a limit is marked', async ({ page }) => {
    await load(page);
    const note = page.locator('#tornado-note');
    await note.locator('summary').click();
    await expect(note).toContainText('A side that stops at a limit is marked (min) or (max).');
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

  test('a limit label stays inside the chart', async ({ page }) => {
    await load(page, '?downPaymentPct=50');
    const out = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      const box = el.getBoundingClientRect();
      const label = [...el.querySelectorAll('.annotation-text')].find((t) => t.textContent === '50% (max)');
      if (label === undefined) return { found: false, inside: false };
      const r = label.getBoundingClientRect();
      return { found: true, inside: r.left >= box.left && r.right <= box.right };
    });
    expect(out).toEqual({ found: true, inside: true });
  });

  // Every input that can sit at a slider limit sits at one, and your verdict
  // lies close to one edge of the chart, so each label starts near it.
  const EDGE_CASES = {
    left: '?propertyPrice=2000000&downPaymentPct=50&mortgageRateAnnual=10&propertyAppreciationAnnual=0&equityGrowthAnnual=15&monthlyRent=500&horizonYears=40&rentInflationRate=0&propertyTaxRate=5',
    right: '?propertyPrice=2000000&monthlyRent=10000&mortgageRateAnnual=1&propertyAppreciationAnnual=10&rentInflationRate=0.1&equityGrowthAnnual=15&propertyTaxRate=0&horizonYears=40&downPaymentPct=5',
  };
  for (const [edge, query] of Object.entries(EDGE_CASES)) {
    test(`limit labels, and the direction labels above them, stay inside the chart when your verdict is near the ${edge} edge`, async ({ page }) => {
      await load(page, query);
      const out = await page.evaluate(() => {
        const el = document.getElementById('tornado-chart');
        const box = el.getBoundingClientRect();
        const indices = el.layout.annotations.flatMap((a, i) =>
          a.name === 'limit-label' || /ahead/.test(a.text) ? [i] : [],
        );
        return {
          count: el.layout.annotations.filter((a) => a.name === 'limit-label').length,
          outside: indices.flatMap((i) => {
            const r = el.querySelector(`.annotation[data-index="${i}"]`).getBoundingClientRect();
            const inside = r.left >= box.left && r.right <= box.right && r.top >= box.top && r.bottom <= box.bottom;
            return inside ? [] : [el.layout.annotations[i].text];
          }),
        };
      });
      expect(out.count).toBeGreaterThan(2);
      expect(out.outside).toEqual([]);
    });
  }

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
