import { test, expect } from '@playwright/test';

/**
 * The "What could change the answer?" chart: the summary sentence above
 * it, the shared Buy - Rent axis with its tie line, the grouping, and the
 * tested values printed at the bar ends.
 *
 * Scenarios are US defaults with one share-link override each:
 *   - defaults:          a toss-up (buying wins in 54% of futures);
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

// Labels that start near an edge of the chart: in the first two, every
// input that can sit at a slider limit sits at one, and your verdict lies
// close to one edge; in the third, a marked bar end lies close to the
// right edge.
const EDGE_CASES = [
  {
    name: 'your verdict is near the left edge',
    query: '?propertyPrice=2000000&downPaymentPct=50&mortgageRateAnnual=10&propertyAppreciationAnnual=0&equityGrowthAnnual=15&monthlyRent=500&horizonYears=40&rentInflationRate=0&propertyTaxRate=5',
    limitLabels: 7,
  },
  {
    name: 'your verdict is near the right edge',
    query: '?propertyPrice=2000000&monthlyRent=10000&mortgageRateAnnual=1&propertyAppreciationAnnual=10&rentInflationRate=0.1&equityGrowthAnnual=15&propertyTaxRate=0&horizonYears=40&downPaymentPct=5',
    limitLabels: 7,
  },
  {
    name: 'a marked bar end is near the right edge',
    query: '?propertyAppreciationAnnual=9.5&equityGrowthAnnual=0&horizonYears=40',
    limitLabels: 0,
  },
];

/**
 * The chart's limit labels and bar-end labels, and the text of every
 * annotation or bar-end label that does not fit inside the chart.
 */
function labelsOutside(page) {
  return page.evaluate(() => {
    const el = document.getElementById('tornado-chart');
    const box = el.getBoundingClientRect();
    const labels = [...el.querySelectorAll('.annotation'), ...el.querySelectorAll('text.bartext')];
    return {
      limitLabels: el.layout.annotations.filter((a) => a.name === 'limit-label').length,
      endLabels: el.querySelectorAll('text.bartext').length,
      outside: labels.flatMap((t) => {
        const r = t.getBoundingClientRect();
        const inside = r.left >= box.left && r.right <= box.right && r.top >= box.top && r.bottom <= box.bottom;
        return inside ? [] : [t.textContent];
      }),
    };
  });
}

/**
 * Pairs of chart labels whose boxes overlap: bar ends, limit labels, row
 * names on a phone, and the labels above the plot.
 */
function overlappingLabels(page) {
  return page.evaluate(() => {
    const el = document.getElementById('tornado-chart');
    const labels = [...el.querySelectorAll('text.bartext'), ...el.querySelectorAll('.annotation')]
      .map((t) => ({ text: t.textContent, r: t.getBoundingClientRect() }));
    return labels.flatMap((a, i) => labels.slice(i + 1).flatMap((b) =>
      a.r.left < b.r.right && b.r.left < a.r.right && a.r.top < b.r.bottom && b.r.top < a.r.bottom
        ? [`${a.text} × ${b.text}`]
        : []));
  });
}

/** What the chart was laid out for: the parts that depend on its width. */
function tornadoLayout(page) {
  return page.evaluate(() => {
    const el = document.getElementById('tornado-chart');
    return {
      width: el.clientWidth,
      drawnWidth: el._fullLayout.width,
      range: el.layout.xaxis.range,
      narrow: el.layout.yaxis.showticklabels === false,
      rowLabels: el.layout.annotations.filter((a) => a.name === 'row-label').length,
      rows: el.layout.yaxis.categoryarray.length,
    };
  });
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
      /^Two of these could flip the answer to buying on their own: property appreciation at \d+\.\d% instead of 3\.0%, or equity growth at \d+\.\d% instead of 7\.0%\.$/,
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
    await load(page, '?monthlyRent=3200'); // buying ahead by ~$178k
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
      'Property appreciation',
      'Equity growth (per year)',
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

  test('a bar whose two tests move the answer the same way prints both at its far end', async ({ page }) => {
    await load(page); // at 20% down, 15% adds mortgage insurance and 25% ties up more cash
    const sides = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      const row = el.data[0].y.indexOf('Down payment');
      return el.data.map((t) => ({ text: t.text[row], hover: t.customdata[row] }));
    });
    expect(sides.map((s) => s.text)).toEqual(['15% · 25%', '']);
    expect(sides[0].hover).toMatch(/^Down payment at 15% instead of 20%<br>/);
    expect(sides[1].hover).toMatch(/^Down payment at 25% instead of 20%<br>/);
  });

  test('the note says when one end lists both values', async ({ page }) => {
    await load(page);
    const note = page.locator('#tornado-note');
    await note.locator('summary').click();
    await expect(note).toContainText('its end lists both values');
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
      return el.data[1].customdata[el.data[1].y.indexOf('Equity growth (per year)')];
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
    // Buying is ahead in 67% of futures. +20% on the home price would be
    // $2.04M; the slider stops at $2.0M, and there renting is ahead. It is
    // the third-widest of four flips, so the summary still names it.
    await load(page, '?propertyPrice=1700000&monthlyRent=9000');
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

  for (const { name, query, limitLabels } of EDGE_CASES) {
    test(`every label stays inside the chart when ${name}`, async ({ page }) => {
      await load(page, query);
      const out = await labelsOutside(page);
      expect(out.limitLabels).toBe(limitLabels);
      expect(out.endLabels).toBeGreaterThan(0);
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
    // Two ends on each of 7 bars; the down payment's both cost buying, so
    // its far end prints both.
    expect(out.count).toBe(15);
    expect(out.outside).toBe(0);
  });
});

test.describe('no two labels overlap, and every label stays inside the chart', () => {
  const WIDTHS = [360, 390, 540, 1280];
  const CASES = [
    { name: 'on the default page', query: '' }, // down payment: both tests cost buying
    ...EDGE_CASES.map(({ name, query }) => ({ name: `when ${name}`, query })),
    { name: 'when buying is far ahead', query: '?monthlyRent=3200' },
  ];
  for (const width of WIDTHS) {
    for (const { name, query } of CASES) {
      test(`at ${width} px ${name}`, async ({ page }) => {
        await page.setViewportSize({ width, height: 800 });
        await load(page, query);
        expect(await overlappingLabels(page)).toEqual([]);
        expect((await labelsOutside(page)).outside).toEqual([]);
      });
    }
  }

  // Bars of zero length, from a result edited in flight: a test that
  // leaves your verdict exactly where it is.
  const ZERO_LENGTH = [
    {
      name: 'every lower test leaves your verdict where it is',
      query: '',
      edit: (t) => { t.low = t.low.map(() => t.base); },
    },
    {
      name: 'no test moves your verdict',
      query: '',
      edit: (t) => {
        t.low = t.low.map(() => t.base);
        t.high = t.high.map(() => t.base);
      },
    },
    {
      name: 'a side at its limit is beside one that leaves your verdict where it is',
      query: '?downPaymentPct=50',
      edit: (t) => { t.low[t.fields.indexOf('downPaymentPct')] = t.base; },
    },
  ];
  for (const width of [390, 1280]) {
    for (const { name, query, edit } of ZERO_LENGTH) {
      test(`at ${width} px when ${name}`, async ({ page }) => {
        await page.route('**/api/monte-carlo', async (route) => {
          const response = await route.fetch();
          const body = await response.json();
          edit(body.tornado);
          await route.fulfill({ response, json: body });
        });
        await page.setViewportSize({ width, height: 800 });
        await load(page, query);
        expect(await overlappingLabels(page)).toEqual([]);
        expect((await labelsOutside(page)).outside).toEqual([]);
      });
    }
  }
});

test.describe('after a width change', () => {
  // The link from #57: limit labels near the left edge.
  const ISSUE_QUERY = EDGE_CASES[0].query;
  const PHONE = { width: 390, height: 664 };
  const DESKTOP = { width: 1280, height: 800 };

  /** The phone layout, with every row labelled, drawn at the chart's width. */
  async function phoneLayoutAtItsWidth(page) {
    const { width, drawnWidth, narrow, rowLabels, rows } = await tornadoLayout(page);
    return narrow && rowLabels === rows && drawnWidth === width;
  }

  test('a chart drawn at 540 px is laid out again at 360 px (#57)', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await load(page, ISSUE_QUERY);
    const fresh = await tornadoLayout(page);

    await page.setViewportSize({ width: 540, height: 800 });
    await load(page, ISSUE_QUERY);
    expect((await tornadoLayout(page)).range).not.toEqual(fresh.range);

    // Record every finished draw from before the resize on.
    await page.evaluate(() => {
      window.__draws = [];
      const el = document.getElementById('tornado-chart');
      el.on('plotly_afterplot', () =>
        window.__draws.push({ range: el.layout.xaxis.range, drawnWidth: el._fullLayout.width }),
      );
    });
    await page.setViewportSize({ width: 360, height: 800 });
    await expect.poll(() => tornadoLayout(page)).toEqual(fresh);
    // Settled once a draw with the fresh layout has finished.
    await expect
      .poll(() => page.evaluate(() => window.__draws.at(-1)))
      .toEqual({ range: fresh.range, drawnWidth: fresh.drawnWidth });
    expect((await labelsOutside(page)).outside).toEqual([]);

    // Drawing does not change the width, so it does not draw again.
    await page.evaluate(() => { window.__draws = []; });
    await page.waitForTimeout(500);
    expect(await page.evaluate(() => window.__draws.length)).toBe(0);
  });

  test('a resize while a new result is pending does not draw the old one in the new currency', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await load(page);
    await page.locator('#region-pills .preset-btn', { hasText: 'UK' }).click();
    await expect(page.locator('#tornado-chart')).toContainText('£');
    // The next Monte Carlo result never arrives.
    await page.route('**/api/monte-carlo', () => {});
    await page.locator('#region-pills .preset-btn', { hasText: 'FR' }).click();
    await expect(page.locator('#verdict-line')).toContainText('€');

    await page.setViewportSize(PHONE);
    await page.waitForTimeout(500);
    // Not laid out again: the pending result is drawn at the new width when
    // it lands. (The axis ticks are Plotly's own and follow its resize.)
    expect((await tornadoLayout(page)).narrow).toBe(false);
    const labels = await page.evaluate(() =>
      [...document.querySelectorAll('#tornado-chart text.bartext, #tornado-chart .annotation')]
        .map((t) => t.textContent)
        .join(' '),
    );
    expect(labels).toContain('£');
    expect(labels).not.toContain('€');
  });

  test('a desktop chart takes the phone layout on a phone, and back', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await load(page, ISSUE_QUERY);
    expect(await tornadoLayout(page)).toMatchObject({ narrow: false, rowLabels: 0 });

    await page.setViewportSize(PHONE);
    await expect.poll(() => phoneLayoutAtItsWidth(page)).toBe(true);
    expect((await labelsOutside(page)).outside).toEqual([]);
    const share = await page.evaluate(() => {
      const el = document.getElementById('tornado-chart');
      return el._fullLayout._size.w / el.clientWidth;
    });
    expect(share).toBeGreaterThan(0.75);

    await page.setViewportSize(DESKTOP);
    await expect.poll(async () => {
      const { width, drawnWidth, narrow, rowLabels } = await tornadoLayout(page);
      return !narrow && rowLabels === 0 && drawnWidth === width;
    }).toBe(true);
  });

  test('no two labels overlap after a desktop chart narrows to 360 px', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await load(page);
    await page.setViewportSize({ width: 360, height: 800 });
    await expect.poll(() => phoneLayoutAtItsWidth(page)).toBe(true);
    expect(await overlappingLabels(page)).toEqual([]);
    expect((await labelsOutside(page)).outside).toEqual([]);
  });

  test('a chart hidden during the change is laid out when it shows', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await load(page, ISSUE_QUERY);
    await page.evaluate(() => { document.getElementById('tornado-chart').style.display = 'none'; });
    await page.setViewportSize(PHONE);
    await page.waitForTimeout(300);
    // A hidden chart has no width, so nothing is laid out for it.
    expect((await tornadoLayout(page)).narrow).toBe(false);

    await page.evaluate(() => { document.getElementById('tornado-chart').style.display = ''; });
    await expect.poll(() => phoneLayoutAtItsWidth(page)).toBe(true);
    expect((await labelsOutside(page)).outside).toEqual([]);
  });
});
