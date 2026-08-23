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
  await page.getByLabel("Search company and sponsor records").fill("Acme");

  await expect(page.getByText("Companies House suggestions")).toBeVisible();
  await expect(page.getByText("Stored sponsor-list suggestions")).toBeVisible();
  await expect(page.getByText(/Suggestions help you choose/)).toHaveCount(0);

  await expect(page.getByRole("option", { name: /ACME LTD/ })).toHaveAttribute("href", "/company/00000001");
});

test("positions decision tools 20 percent from the bottom and expands drawer labels", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  const launchers = page.locator(".decision-launchers");
  const box = await launchers.boundingBox();
  expect(box).not.toBeNull();
  const bottomOffset = (844 - box!.y - box!.height) / 844;
  expect(bottomOffset).toBeGreaterThanOrEqual(0.19);
  expect(bottomOffset).toBeLessThanOrEqual(0.21);

  await page.getByLabel("Open navigation").click();
  const drawer = page.locator(".mobile-nav-panel");
  await expect(drawer.getByRole("button", { name: "Ask VeriFinder" })).toBeVisible();
  await expect(drawer.getByRole("button", { name: "Build a decision plan" })).toBeVisible();
});

test("provides suggestions on both dedicated search pages", async ({ page }) => {
  await page.route("**/api/search/suggestions?*", (route) => route.fulfill({
    json: {
      query: "Acme",
      results: [{ company_number: "00000001", company_name: "ACME LTD", status: "active", location: "London", company_type: "ltd", data_mode: "live" }],
      total: 1,
      data_mode: "live",
      message: null,
    },
  }));
  await page.route("**/api/sponsors/suggestions?*", (route) => route.fulfill({
    json: {
      query: "Acme",
      results: [{ id: "sponsor-1", organisation_name: "Acme Care Ltd", town_city: "Bristol", county: null, rating: "A rating", routes: ["Skilled Worker"], source: {} }],
      total: 1,
      dataset_version: "2026-08-22",
      message: null,
    },
  }));

  await page.goto("/companies");
  await page.getByLabel("Search Companies House").fill("Acme");
  await expect(page.getByText("Companies House suggestions")).toBeVisible();
  await expect(page.getByText("Stored sponsor-list suggestions")).toHaveCount(0);

  await page.goto("/sponsors");
  await page.getByLabel("Search the sponsor register").fill("Acme");
  await expect(page.getByText("Stored sponsor-list suggestions")).toBeVisible();
  await expect(page.getByText("Companies House suggestions")).toHaveCount(0);
});

test("homepage search results include records found in either source", async ({ page }) => {
  await page.route("**/api/search?q=*", (route) => route.fulfill({
    json: {
      query: "ACME LTD",
      results: [{ company_number: "00000001", company_name: "ACME LTD", status: "active", location: "London", company_type: "ltd", data_mode: "live" }],
      total: 1,
      data_mode: "live",
      message: null,
    },
  }));
  await page.route("**/api/sponsors/search?q=*", (route) => route.fulfill({
    json: {
      query: "ACME LTD",
      results: [{ id: "sponsor-1", organisation_name: "ACME LTD", town_city: "London", county: null, rating: "A rating", routes: ["Skilled Worker"], source: {} }],
      total: 1,
      dataset_version: "2026-08-22",
      message: null,
    },
  }));

  await page.goto("/search?q=ACME%20LTD");
  await expect(page.getByRole("heading", { name: "Companies House", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sponsor register", exact: true })).toBeVisible();
  await expect(page.locator(".result-card").getByRole("heading", { name: "ACME LTD" })).toHaveCount(2);
});
