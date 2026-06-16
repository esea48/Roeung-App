import { defineConfig } from '@playwright/test';

const baseURL = process.env.SMOKE_WEB_BASE_URL || 'http://localhost:5173';
const chromePath =
  process.env.SMOKE_CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

export default defineConfig({
  testDir: './e2e',
  timeout: 15 * 60 * 1000,
  expect: {
    timeout: 30_000,
  },
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    launchOptions: {
      executablePath: chromePath,
    },
  },
});
