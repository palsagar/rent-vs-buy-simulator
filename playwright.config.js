import { defineConfig } from '@playwright/test';

// Dedicated port: 8323 keeps clear of dev servers and the sibling apps' 8321.
export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:8323',
  },
  webServer: {
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
});
