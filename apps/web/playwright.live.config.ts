import { defineConfig, devices } from '@playwright/test'

declare const process: { env: Record<string, string | undefined> }

// Suíte que roda contra o stack REAL do compose (api + web + mediamtx), sem mock:
//   docker compose --profile cv up -d && npx playwright test -c playwright.live.config.ts
export default defineConfig({
  testDir: './tests-live',
  timeout: 60_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  reporter: [['list']],
  use: {
    baseURL: process.env.LIVE_BASE_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'chromium',
      testIgnore: /auth\.setup\.ts/,
      use: { ...devices['Desktop Chrome'], storageState: 'tests-live/.auth/live.json' },
      dependencies: ['setup'],
    },
  ],
})
