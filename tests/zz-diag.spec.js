import { test } from '@playwright/test';

test.use({ viewport: { width: 390, height: 664 }, hasTouch: true, isMobile: true });

test('diag tap', async ({ page }) => {
  await page.addInitScript(() => {
    try { localStorage.setItem('rvb.tour.v1', 'done'); } catch (e) {}
  });
  await page.goto('/');
  await page.waitForFunction(
    () => document.getElementById('verdict-confidence').textContent.length > 0,
    null,
    { timeout: 20_000 },
  );
  await page.evaluate(() => {
    window.__log = [];
    const el = document.getElementById('decision-chart');
    for (const t of ['touchstart', 'touchend', 'pointerdown', 'pointerup', 'pointermove', 'mousemove', 'mousedown', 'mouseup', 'click', 'mouseout', 'mouseleave', 'pointerleave', 'pointercancel', 'touchcancel']) {
      document.addEventListener(t, (e) => window.__log.push(`${t}@${e.clientX ?? ''},${e.clientY ?? ''} ${e.target.className?.baseVal ?? e.target.className}`), true);
    }
    el.on?.('plotly_hover', () => window.__log.push('plotly_hover'));
    el.on?.('plotly_unhover', () => window.__log.push('plotly_unhover'));
    el.scrollIntoView({ block: 'center' });
  });
  const box = await page.locator('#decision-chart').boundingBox();
  const x = box.x + box.width * 0.4;
  const y = box.y + box.height / 2;
  console.log('DIAG box', JSON.stringify(box), 'tap', x, y);
  console.log('DIAG elementFromPoint', await page.evaluate(([x, y]) => {
    const e = document.elementFromPoint(x, y);
    return `${e.tagName} ${e.className?.baseVal ?? e.className}`;
  }, [x, y]));
  await page.touchscreen.tap(x, y);
  for (const ms of [50, 200, 500, 1000]) {
    await page.waitForTimeout(ms);
    console.log('DIAG after', ms, await page.evaluate(() => document.querySelector('#decision-chart .hoverlayer').innerHTML.length));
  }
  console.log('DIAG log', JSON.stringify(await page.evaluate(() => window.__log)));
  // Does a plain mouse move hover?
  await page.mouse.move(x, y);
  await page.mouse.move(x + 3, y);
  await page.waitForTimeout(300);
  console.log('DIAG mouse hover len', await page.evaluate(() => document.querySelector('#decision-chart .hoverlayer').innerHTML.length));
  console.log('DIAG log2', JSON.stringify(await page.evaluate(() => window.__log.slice(-6))));
});
