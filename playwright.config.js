import { defineConfig } from '@playwright/test';

// Dedicated ports: 8323 and 8324 keep clear of dev servers and the sibling apps' 8321.
export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  // CI only: fail the build on a stray test.only, retry once to absorb a CDN
  // (Plotly) or runner-speed blip, and write an HTML report for the artifact
  // upload. Locally the html reporter would open a server, so keep it off.
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [['list'], ['github'], ['html', { open: 'never' }]]
    : 'list',
  use: {
    baseURL: 'http://127.0.0.1:8323',
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: 'uv run uvicorn simulator.server:app --port 8323',
      url: 'http://127.0.0.1:8323/api/health',
      reuseExistingServer: false,
      timeout: 60_000,
      // Force the analytics contract under test: env-less = inert, even if the
      // operator's shell exports real UMAMI_* values.
      env: {
        UMAMI_DOMAIN: '',
        UMAMI_ID: '',
      },
    },
    {
      // A second server with analytics on, for the real-tracker tests in
      // analytics.spec.js. The Umami origin is fake: those tests answer its
      // script.js and /api/send requests themselves, so nothing leaves the
      // machine.
      command: 'uv run uvicorn simulator.server:app --port 8324',
      url: 'http://127.0.0.1:8324/api/health',
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        UMAMI_DOMAIN: 'https://umami.test',
        UMAMI_ID: '123e4567-e89b-42d3-a456-426614174000',
      },
    },
  ],
});
