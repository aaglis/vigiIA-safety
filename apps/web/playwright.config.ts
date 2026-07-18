import { defineConfig, devices } from '@playwright/test'

declare const process: { env: Record<string, string | undefined> }

const e2ePort = Number(process.env.E2E_PORT ?? 5174)
const e2eBaseURL = `http://127.0.0.1:${e2ePort}`
const e2eWebServerCommand = process.env.E2E_WEB_SERVER_COMMAND ?? `npm run dev -- --host 127.0.0.1 --port ${e2ePort}`

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: {
    timeout: 8_000,
  },
  fullyParallel: false,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: e2eBaseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: e2eWebServerCommand,
    url: e2eBaseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    env: {
      VITE_API_BASE_URL: '/api/v1',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
