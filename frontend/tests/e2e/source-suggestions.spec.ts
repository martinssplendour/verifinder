import { expect, test } from "@playwright/test";

const account = {
  authenticated: false,
  email: null,
  entitlements: {
    tier: "free",
    ask: { allowed: true, reset_at: null, word_limit: 20 },
    planner: { allowed: true, reset_at: null, word_limit: null },
    report_download: { allowed: false, reset_at: null, word_limit: null },
    watchlists: { allowed: false, reset_at: null, word_limit: null },
  },
  billing_configured: true,
  coin_billing_configured: true,
  coin_balance: 0,
  has_billing_account: false,
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/account/me", (route) => route.fulfill({ json: account }));
});

test("shows separate source suggestions and opens the selected source record", async ({ page }) => {
  await page.route("**/api/search/suggestions?*", (route) => route.fulfill({
    json: {
      query: "Acme",
      results: [{
        company_number: "00000001",
        company_name: "ACME LTD",
        status: "active",
        location: "London",
        company_type: "ltd",
        data_mode: "live",
      }],
      total: 1,
      data_mode: "live",
      message: null,
    },
  }));
  await page.route("**/api/sponsors/suggestions?*", (route) => route.fulfill({
    json: {
      query: "Acme",
      results: [{
        id: "sponsor-1",
        organisation_name: "Acme Care Ltd",
        town_city: "Bristol",
        county: null,
        rating: "A rating",
        routes: ["Skilled Worker"],
        source: {},
      }],
      total: 1,
      dataset_version: "2026-08-22",
      message: null,
    },
  }));

  await page.goto("/");
  await page.getByLabel("Company or sponsor source record").fill("Acme");

  await expect(page.getByText("Companies House suggestions")).toBeVisible();
  await expect(page.getByText("Stored sponsor-list suggestions")).toBeVisible();
  await expect(page.getByText("They do not join or verify records across sources.")).toBeVisible();

  await page.getByRole("option", { name: /ACME LTD/ }).click();
  await expect(page).toHaveURL(/\/company\/00000001$/);
});

test("keeps decision tools high on mobile and expands drawer labels", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  const launchers = page.locator(".decision-launchers");
  const box = await launchers.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.y / 844).toBeGreaterThanOrEqual(0.19);
  expect(box!.y / 844).toBeLessThanOrEqual(0.21);

  await page.getByLabel("Open navigation").click();
  const drawer = page.locator(".mobile-nav-panel");
  await expect(drawer.getByRole("button", { name: "Ask VeriFinder" })).toBeVisible();
  await expect(drawer.getByRole("button", { name: "Build a decision plan" })).toBeVisible();
});
