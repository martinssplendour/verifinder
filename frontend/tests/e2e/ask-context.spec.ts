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

const source = {
  id: "worker-sponsors",
  organisation: "UK Visas and Immigration",
  dataset: "Register of licensed sponsors: workers",
  official_url: "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers",
  retrieved_at: "2026-08-22T12:00:00Z",
  published_at: null,
  version: "2026-08-22",
  health: "healthy",
};

test("keeps server conversation context and offers a verified job-search alternative", async ({ page }) => {
  const askBodies: Record<string, unknown>[] = [];
  let askCount = 0;

  await page.route("**/api/account/me", (route) => route.fulfill({ json: account }));
  await page.route("**/api/intelligence/ask", async (route) => {
    askCount += 1;
    askBodies.push(route.request().postDataJSON());
    if (askCount === 1) {
      await route.fulfill({
        json: {
          question: "Top 10 tech jobs in Sheffield",
          conversation_id: "11111111-1111-1111-1111-111111111111",
          context_turns_used: 0,
          interpretation: {
            intent: "job_search",
            subject: "technology",
            location: "Sheffield",
            industry: "technology",
            sponsorship_route: null,
            limit: 10,
            assumptions: ["Live vacancies are not connected."],
          },
          headline: "Live job listings are not connected yet",
          summary: "I understood this as a request for technology vacancies in Sheffield, but I need a verified vacancies source to rank current openings.",
          results: [],
          total: 0,
          limitations: ["VeriFinder does not currently ingest a live jobs or vacancies feed."],
          suggested_questions: ["Show me technology organisations with worker sponsorship in Sheffield"],
          ai_mode: "deterministic",
          generated_at: "2026-08-22T12:00:00Z",
        },
      });
      return;
    }
    await route.fulfill({
      json: {
        question: "Show me technology organisations with worker sponsorship in Sheffield",
        conversation_id: "11111111-1111-1111-1111-111111111111",
        context_turns_used: 1,
        interpretation: {
          intent: "sponsor_discovery",
          subject: null,
          location: "Sheffield",
          industry: "technology",
          sponsorship_route: null,
          limit: 10,
          assumptions: ["The previous answer was used as context."],
        },
        headline: "1 licensed worker sponsor in Sheffield",
        summary: "One organisation matched the location and technology-name filters.",
        results: [{
          rank: 1,
          id: "sponsor-1",
          result_type: "worker_sponsor",
          title: "Sheffield Digital Systems Ltd",
          subtitle: "Licensed worker sponsor",
          href: "/sponsor/sponsor-1",
          facts: [{ kind: "verified_fact", label: "Sponsor rating", value: "A" }],
          why_it_matches: ["Register location matches Sheffield"],
          source,
        }],
        total: 1,
        limitations: ["A sponsor licence does not prove a current vacancy."],
        suggested_questions: [],
        ai_mode: "deterministic",
        generated_at: "2026-08-22T12:01:00Z",
      },
    });
  });

  await page.goto("/ask");
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();
  await page.getByLabel("What do you need to know?").fill("Top 10 tech jobs in Sheffield");
  await page.locator(".ask-composer").getByRole("button", { name: "Ask", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Live job listings are not connected yet" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Show me technology organisations/ })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Live job listings are not connected yet" })).toBeVisible();
  await page.getByRole("button", { name: /Show me technology organisations/ }).click();

  await expect(page.getByRole("heading", { name: "1 licensed worker sponsor in Sheffield" })).toBeVisible();
  await expect(page.getByText("Used 1 earlier answer, including result records")).toBeVisible();
  expect(askBodies[1].conversation_id).toBe("11111111-1111-1111-1111-111111111111");
});
