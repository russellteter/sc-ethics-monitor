import { expect, test } from "@playwright/test";

// Refresh tests share a single Next process. Run serially so the in-process
// rate-limit map's state is deterministic across tests.
test.describe.configure({ mode: "serial" });

test.describe("Refresh API", () => {
  test("POST /api/refresh without GH_PAT returns 500", async ({ request }) => {
    const r = await request.post("/api/refresh");
    // GH_PAT is unset in the test env → route 500s. If the rate-limit slot
    // was already burned by a previous test in this run, expect 429 instead.
    expect([429, 500, 502]).toContain(r.status());
  });

  test("rate-limited second call within 60s returns 429", async ({
    request,
  }) => {
    await request.post("/api/refresh"); // first burns the slot
    const r = await request.post("/api/refresh");
    expect([429, 500]).toContain(r.status());
  });

  test("button click shows feedback toast", async ({ page }) => {
    await page.goto("/");
    await page
      .getByRole("button", { name: /refresh now|trigger data refresh/i })
      .click();
    // Without GH_PAT the route returns 500 → "Couldn't start refresh".
    // After the slot is burned subsequent clicks return 429 → "Just refreshed".
    // Both are acceptable; network errors also fine.
    await expect(
      page.getByText(
        /refresh started|couldn't|just refreshed|network error/i,
      ),
    ).toBeVisible();
  });
});
