import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [["github"], ["html", { open: "never" }]]
    : "list",
  timeout: 30_000,
  expect: {
    // Slightly looser pixel tolerance to absorb cross-OS font rendering jitter.
    toHaveScreenshot: { maxDiffPixelRatio: 0.02 },
  },
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  webServer: [
    {
      // Static fixture server — serves dashboard/e2e/fixtures/house_finance.json
      command: "npx --yes serve -l 4173 e2e/fixtures",
      port: 4173,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      // Production Next build pointed at the fixture URL.
      command: "next build && next start -p 3000",
      port: 3000,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
      env: {
        HOUSE_FINANCE_DATA_URL: "http://localhost:4173/house_finance.json",
      },
    },
  ],
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["iPhone 13"] } },
  ],
});
