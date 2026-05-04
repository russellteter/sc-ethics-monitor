import { expect, test } from "@playwright/test";

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /SC House Dem Finance/i }),
    ).toBeVisible();
  });

  test("renders header with last refreshed timestamp", async ({ page }) => {
    await expect(page.getByText(/Last refreshed/i)).toBeVisible();
  });

  test("stats strip shows 6 tracked / 5 filed / 1 not filed", async ({
    page,
  }) => {
    // Scope to each card by its label so digits like "1" can't bleed in
    // from district numbers, sort indicators, or other text nodes.
    const trackedCard = page
      .locator("div")
      .filter({ hasText: /^Tracked\s*6\s*Dem House candidates$/ });
    await expect(trackedCard.first()).toBeVisible();

    const filedCard = page
      .locator("div")
      .filter({ hasText: /^Filed\s*5\s*Q1 reports submitted$/ });
    await expect(filedCard.first()).toBeVisible();

    const notFiledCard = page
      .locator("div")
      .filter({ hasText: /^Not filed\s*1\s*missing Q1 disclosure$/ });
    await expect(notFiledCard.first()).toBeVisible();
  });

  test("table renders all 6 candidates", async ({ page }) => {
    const rows = page.locator("tbody tr");
    await expect(rows).toHaveCount(6);
    // Scope name lookups to the table body — "Marvin Pendarvis" also
    // appears in the StatsStrip "Top COH" sub-line.
    const tbody = page.locator("tbody");
    await expect(tbody.getByText("Marvin Pendarvis")).toBeVisible();
    await expect(tbody.getByText("Heather Bauer")).toBeVisible();
    await expect(tbody.getByText("Roger Kirby")).toBeVisible();
  });

  test("table sorted by COH desc by default — Pendarvis first", async ({
    page,
  }) => {
    const firstRow = page.locator("tbody tr").first();
    await expect(firstRow).toContainText("Marvin Pendarvis");
    await expect(firstRow).toContainText("$112,400");
  });

  test("clicking District column header sorts ascending — D-41 first", async ({
    page,
  }) => {
    await page
      .locator("thead th")
      .filter({ hasText: /^District/i })
      .click();
    const firstRow = page.locator("tbody tr").first();
    await expect(firstRow).toContainText("D-41");
    await expect(firstRow).toContainText("Annie McDaniel");
  });

  test("search filters rows live to a single match", async ({ page }) => {
    await page.getByLabel("Search candidates").fill("bauer");
    await expect(page.locator("tbody tr")).toHaveCount(1);
    await expect(page.getByText("Heather Bauer")).toBeVisible();
  });

  test("filter pill 'Not filed' shows only Kirby", async ({ page }) => {
    await page.getByRole("button", { name: /^Not filed$/i }).click();
    await expect(page.locator("tbody tr")).toHaveCount(1);
    await expect(page.getByText("Roger Kirby")).toBeVisible();
  });

  test("filter pill 'COH ≥ $50K' shows three", async ({ page }) => {
    await page.getByRole("button", { name: /COH ≥ \$50K/i }).click();
    await expect(page.locator("tbody tr")).toHaveCount(3);
  });

  test("clicking a row opens drawer with three financial numbers", async ({
    page,
  }) => {
    await page.getByText("Heather Bauer").click();
    const drawer = page.getByRole("dialog");
    await expect(drawer).toBeVisible();
    await expect(drawer.getByText("Period raised")).toBeVisible();
    await expect(drawer.getByText("Total raised")).toBeVisible();
    await expect(drawer.getByText("Cash on hand")).toBeVisible();
    await expect(drawer.getByText("$32,807")).toBeVisible();
    await expect(drawer.getByText("$89,371")).toBeVisible();
    await expect(drawer.getByText("$68,449")).toBeVisible();
  });

  test("Escape key closes the drawer", async ({ page }) => {
    await page.getByText("Heather Bauer").click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).not.toBeVisible();
  });

  test("not_filed candidate drawer shows empty-state message", async ({
    page,
  }) => {
    await page.getByText("Roger Kirby").click();
    const drawer = page.getByRole("dialog");
    await expect(drawer).toBeVisible();
    await expect(drawer.getByText(/no quarterly disclosure/i)).toBeVisible();
  });

  test("Ethics report link is external + has rel=noreferrer", async ({
    page,
  }) => {
    await page.getByText("Heather Bauer").click();
    const link = page.getByRole("link", { name: /view on ethicsfiling/i });
    await expect(link).toHaveAttribute("target", "_blank");
    await expect(link).toHaveAttribute("rel", /noreferrer/);
  });

  test("keyboard: focus first row + Enter opens drawer", async ({ page }) => {
    await page.locator("tbody tr").first().focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("clicking COH header twice toggles to ascending order", async ({
    page,
  }) => {
    // Starts desc by default. First click on the active column flips to asc.
    await page
      .locator("thead th")
      .filter({ hasText: /Cash on hand/i })
      .click();
    const firstRow = page.locator("tbody tr").first();
    // Roger Kirby has no report (-Infinity in sort), then Brawley $31,200, etc.
    // With asc, missing values sort first.
    await expect(firstRow).toContainText("Roger Kirby");
  });
});

test.describe("Dashboard - visual", () => {
  // One baseline only. Mobile reflows are covered by interaction tests above.
  test.skip(
    ({ browserName }, testInfo) => testInfo.project.name !== "chromium",
    "visual baseline pinned to chromium",
  );

  test("visual snapshot — main dashboard view", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    // Wait for webfont (Syne) so the first run's pixels match subsequent runs.
    await page.evaluate(() => document.fonts.ready);
    await expect(page).toHaveScreenshot("dashboard-main.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.02,
      // Mask the live timestamp so day-to-day runs don't diff.
      mask: [page.getByText(/Last refreshed/i)],
    });
  });
});
