import { expect, test, type Locator, type Page } from "@playwright/test";

import { AuthSessionSchema } from "../src/features/auth/schemas";
import { DashboardProjectionsSchema } from "../src/features/dashboard/schemas";
import { createOpenRouterAccount } from "../src/features/openrouter/test-fixtures";
import { ClaudeAccountSchema } from "../src/features/claude/api";
import {
  createAccountSummary,
  createDashboardAuthSession,
  createDashboardOverview,
  createDashboardProjections,
  createDashboardSettings,
  createRequestLogEntry,
  createRequestLogFilterOptions,
  createRequestLogsResponse,
  createTelemetryConsent,
} from "../src/test/mocks/factories";

const REQUIRED_API_PATHS = [
  "/api/dashboard-auth/session",
  "/api/dashboard/overview",
  "/api/dashboard/projections",
  "/api/request-logs/options",
  "/api/request-logs",
  "/api/settings/telemetry",
] as const;

async function installMobileContainmentFixtures(page: Page, accounts = [
    createAccountSummary({
      accountId: "acc_primary",
      email: "primary-operator@northstar",
      displayName: "primary-operator@northstar",
      usage: { primaryRemainingPercent: 82, secondaryRemainingPercent: 67 },
    }),
    createAccountSummary({
      accountId: "acc_secondary",
      email: "secondary-operator@northstar",
      displayName: "secondary-operator@northstar",
      usage: { primaryRemainingPercent: 45, secondaryRemainingPercent: 12 },
    }),
  ]): Promise<void> {
  const fixtures: Record<string, unknown> = {
    "/api/dashboard-auth/session": createDashboardAuthSession({ authenticated: true, passwordRequired: true }),
    "/api/dashboard/overview": createDashboardOverview({ accounts }),
    "/api/dashboard/projections": createDashboardProjections(),
    "/api/request-logs/options": createRequestLogFilterOptions({ accountIds: accounts.map((account) => account.accountId) }),
    "/api/request-logs": createRequestLogsResponse([createRequestLogEntry({ accountId: "acc_primary", requestId: "req_mobile_containment" })], 1, false),
    "/api/settings/telemetry": createTelemetryConsent({ state: "enabled", source: "persisted", active: true }),
    "/api/settings": createDashboardSettings(),
    "/api/settings/quota-reset-webhook": { enabled: false, kinds: ["scheduled", "unexpected"],
      urlConfigured: false, signingSecretConfigured: false, pending: 0, lastDelivery: null },
    "/api/settings/quota-reset-webhook/destination": { url: null },
    "/api/accounts": { accounts },
  };

  await page.route("**/api/**", async (route) => {
    const payload = fixtures[new URL(route.request().url()).pathname];
    if (payload === undefined) {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "not_found", message: "Not found" } }),
      });
      return;
    }
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(payload) });
  });
}

async function acceptTelemetryConsent(page: Page, consentDialog: Locator): Promise<void> {
  const consentDecision = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/api/settings/telemetry" && response.request().method() === "PUT",
  );
  await consentDialog.getByRole("button", { name: "Keep enabled" }).click();
  expect((await consentDecision).ok()).toBe(true);
  await expect(consentDialog).toBeHidden();
}

for (const width of [320, 390, 1440]) {
  for (const theme of ["light", "dark"] as const) {
    test(`provider branding and readable models ${theme} ${width}`, async ({ page }, testInfo) => {
      await page.emulateMedia({ reducedMotion: "reduce", colorScheme: theme });
      await page.addInitScript((value) => localStorage.setItem("codex-lb-theme", value), theme);
      await page.setViewportSize({ width, height: 1000 });
      const native = createAccountSummary({ accountId: "brand-native", displayName: "Codex account with a long operator alias" });
      const openrouter = createOpenRouterAccount({ id: "brand-router", name: "OpenRouter account with a long operator alias" });
      const claude = ClaudeAccountSchema.parse({
        id: "brand-claude", name: "Claude account with a long operator alias",
        planType: "pro", maxConcurrency: null, routingPolicy: "normal", isEnabled: true,
        credentialStatus: "ready", expiresAt: "2027-01-01T00:00:00Z",
        state: { all_models: true, reasoning_restrictions: {}, selections: [], catalog: [],
          catalog_updated_at: null, catalog_error: null, usage_updated_at: null, usage_error: null,
          subscription: null, subscription_updated_at: null, subscription_error: null },
        quota: { observedAt: null, models: [], windows: [
          { name: "five_hour", utilization: 20, resetsAt: "2026-10-02T00:00:00Z", freshness: "fresh", exhausted: false },
          { name: "seven_day", utilization: 40, resetsAt: "2026-10-07T00:00:00Z", freshness: "fresh", exhausted: false },
        ] },
      });
      await installMobileContainmentFixtures(page, [native]);
      await page.route("**/api/claude-accounts", (route) => route.fulfill({ json: { accounts: [claude] } }));
      await page.route("**/api/openrouter-accounts", (route) => route.fulfill({ json: { accounts: [openrouter] } }));
      await page.route("**/api/models", (route) => route.fulfill({ json: { models: [
        { id: "gpt-6-astra", name: "GPT 6 Astra" },
        { id: "openrouter/z-ai/glm-5.3-flash", name: "Z.ai: GLM 5.3 Flash" },
      ] } }));
      await page.route(/\/api\/request-logs(?:\?|$)/, (route) => route.fulfill({ json: createRequestLogsResponse([
        createRequestLogEntry({ requestId: "brand-native", accountId: native.accountId, model: "gpt-6-astra", modelSourceKind: null, reasoningEffort: "medium", actualServiceTier: "default" }),
        createRequestLogEntry({ requestId: "brand-router", accountId: null, modelSourceId: openrouter.id, modelSourceKind: "openrouter", modelSourceName: openrouter.name, model: "openrouter/z-ai/glm-5.3-flash", reasoningEffort: "high", actualServiceTier: "priority" }),
        createRequestLogEntry({ requestId: "brand-claude", accountId: null, modelSourceId: claude.id, modelSourceKind: "claude", modelSourceName: claude.name, model: "anthropic/claude-haiku-4-5-20251001", reasoningEffort: "high" }),
      ], 3, false) }));
      await page.goto("/dashboard");
      const cards = page.getByTestId("dashboard-account-cards");
      for (const provider of ["codex", "claude", "openrouter"] as const) {
        const assetPath = `/images/providers/${provider === "codex" ? "openai" : provider}.svg`;
        const asset = await page.request.get(assetPath);
        expect(asset.ok()).toBe(true);
        const svg = await asset.text();
        expect(svg).toContain("#000");
        expect(svg).not.toMatch(/<(?:script|text|image|foreignObject|use|style)\b|onload|onclick|href=/);
        const mark = cards.locator(`img[data-provider="${provider}"]`);
        await expect(mark).toBeVisible();
        await expect(mark).toHaveAttribute("src", assetPath);
        await expect.poll(() => mark.evaluate((image) => (image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
        await expect(mark).toHaveCSS("width", "16px");
        await expect(mark).toHaveCSS("filter", theme === "dark" ? "invert(1)" : "none");
      }
      const table = page.getByRole("table").first();
      const nativeLabel = table.getByTitle("gpt-6-astra", { exact: true });
      await expect(nativeLabel).toHaveText("GPT 6 Astra medium");
      await expect(nativeLabel.getByText("medium", { exact: true })).toHaveClass("text-muted-foreground");
      await expect(nativeLabel.getByText("medium", { exact: true })).toHaveCSS("color", await table.getByText("Unknown", { exact: true }).first().evaluate((element) => getComputedStyle(element).color));
      await expect(table.getByTitle("openrouter/z-ai/glm-5.3-flash", { exact: true })).toHaveText("Z.ai: GLM 5.3 Flash high · priority");
      await expect(table.getByTitle("anthropic/claude-haiku-4-5-20251001", { exact: true })).toHaveText("Claude Haiku 4.5 high");
      await expect(table.locator("tbody img[data-provider]")).toHaveCount(3);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`provider-dashboard-${theme}-${width}.png`), fullPage: true });
      await page.getByRole("radio", { name: "View accounts as list" }).click();
      await expect(page.getByTestId("dashboard-account-list").locator("img[data-provider]")).toHaveCount(3);
      for (const [provider, id, name] of [
        ["codex", native.accountId, native.displayName],
        ["claude", claude.id, claude.name],
        ["openrouter", openrouter.id, openrouter.name],
      ]) {
        await page.goto(`/accounts?selected=${id}`);
        const heading = page.getByRole("heading", { name, exact: true });
        await expect(heading.locator(`img[data-provider="${provider}"]`)).toBeVisible();
        await expect(page.locator(`button[aria-pressed] img[data-provider="${provider}"]`)).toHaveCount(1);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
        await page.screenshot({ path: testInfo.outputPath(`provider-accounts-${provider}-${theme}-${width}.png`), fullPage: true });
      }
    });
  }

  test(`weekly consumer costs and concise account subtitles ${width}`, async ({ page }, testInfo) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width, height: 1000 });
    const accounts = [createAccountSummary({ displayName: "Codex account" })];
    await installMobileContainmentFixtures(page, accounts);
    const pace = {
      totalFullCredits: 1000, totalActualRemainingCredits: 600, totalExpectedRemainingCredits: 600,
      actualUsedPercent: 40, scheduledUsedPercent: 40, deltaPercent: 0, scheduleGapCredits: 0,
      overPlanCredits: 0, projectedShortfallCredits: 0, pauseForBreakEvenHours: null,
      paceMultiplier: null, throttleToPercent: null, reduceByPercent: null,
      proAccountEquivalentToCoverOverPlan: null, proAccountsToCoverOverPlan: null,
      projectedDepletionHours: 60, projectedMinimumRemainingCredits: 0,
      forecastBurnRateCreditsPerHour: 10, scheduledBurnRateCreditsPerHour: 10,
      status: "on_track" as const, accountCount: 1, staleAccountCount: 0, inactiveAccountCount: 0,
      confidence: "high" as const, runwayStatus: "safe" as const,
      headroomPercent: 60, headroomCredits: 600, burnRateRecentCreditsPerHour: 10,
      depletionEtaHours: 60, nextReliefInHours: 26, nextReliefCredits: 400, resetEvents: [],
      topApiKeys: [
        { apiKeyId: "paid", name: "Long consumer name for a production automation", requests: 12500,
          billableTokens: 18000000, cachedTokens: 0, dominantModel: "anthropic/claude-opus-5-5",
          costCoverage: { knownCostUsd: 44248.05, pricedRequests: 12499, unpricedRequests: 1,
            unmeteredRequests: 0, coverageUnknown: false } },
        { apiKeyId: "free", name: "Free consumer", requests: 25, billableTokens: 10000,
          cachedTokens: 0, dominantModel: "openrouter/qwen/free",
          costCoverage: { knownCostUsd: 0, pricedRequests: 25, unpricedRequests: 0,
            unmeteredRequests: 0, coverageUnknown: false } },
        { apiKeyId: "unknown", name: "Unknown consumer", requests: 10, billableTokens: 1000,
          cachedTokens: 0, dominantModel: "unknown-model",
          costCoverage: { knownCostUsd: 0, pricedRequests: 0, unpricedRequests: 10,
            unmeteredRequests: 0, coverageUnknown: false } },
      ],
    };
    await page.route(/\/api\/dashboard\/overview(?:\?|$)/, (route) =>
      route.fulfill({ json: createDashboardOverview({ accounts, weeklyCreditPace: pace }) }));
    await page.route(/\/api\/dashboard\/projections(?:\?|$)/, (route) =>
      route.fulfill({ json: createDashboardProjections({ weeklyCreditPace: pace }) }));
    await page.route("**/api/openrouter-accounts", (route) =>
      route.fulfill({ json: { accounts: [createOpenRouterAccount()] } }));
    await page.route("**/api/claude-accounts", (route) => route.fulfill({ json: { accounts: [{
      planType: "pro", routingPolicy: "normal", maxConcurrency: null,
      id: "claude-test", name: "Claude account", isEnabled: true, credentialStatus: "ready",
      expiresAt: "2027-01-01T00:00:00Z",
      state: { all_models: true, reasoning_restrictions: {}, selections: [], catalog: [], catalog_updated_at: null,
        subscription: null, subscription_updated_at: null, subscription_error: null,
        catalog_error: null, usage_updated_at: null, usage_error: null },
      quota: { observedAt: null, models: [], windows: [] },
    }] } }));
    await page.goto("/dashboard");
    const attribution = page.getByTestId("runway-attribution");
    await expect(attribution.getByText("Top consumers · last 2h", { exact: true })).toBeVisible();
    await expect(attribution.getByText("Est. API Cost", { exact: true })).toBeVisible();
    await expect(attribution.getByText("$44,248.05", { exact: true })).toBeVisible();
    await expect(attribution.getByText("$0.00", { exact: true })).toBeVisible();
    await expect(attribution.getByText("Unknown", { exact: true })).toBeVisible();
    await expect(attribution).not.toContainText("known · incomplete");
    for (const row of await attribution.locator("li").all()) {
      expect(await row.evaluate((el) => {
        const box = el.getBoundingClientRect();
        return Array.from(el.children).every((child) => {
          const bounds = child.getBoundingClientRect();
          return bounds.left >= box.left - 1 && bounds.right <= box.right + 1;
        });
      })).toBe(true);
    }
    const cards = page.getByTestId("dashboard-account-cards");
    await expect(cards.getByTestId("codex-account-card").getByText("Plus", { exact: true })).toBeVisible();
    await expect(cards.getByTestId("openrouter-account-card")).toContainText("OpenRouter · Paid");
    await expect(cards.getByTestId("claude-account-card")).toContainText("Claude · Pro");
    await expect(cards).not.toContainText("models selected");
    await expect(cards).not.toContainText("All models");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`weekly-consumer-costs-${width}.png`), fullPage: true });
  });
}

for (const width of [390, 1440]) {
  test(`request operation labels reuse model-cell layout ${width}`, async ({ page }, testInfo) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width, height: 1000 });
    await installMobileContainmentFixtures(page);
    await page.route(/\/api\/request-logs(?:\?|$)/, async (route) => {
      const requests = [
        createRequestLogEntry({ accountId: "acc_primary", requestId: "search", model: "", requestOperation: "web_search", tokens: null, costUsd: null }),
        createRequestLogEntry({ accountId: "acc_primary", requestId: "warm", requestOperation: "responses", requestKind: "warmup" }),
        createRequestLogEntry({ accountId: "acc_primary", requestId: "image", model: "gpt-image-2", requestOperation: "image_edit" }),
        createRequestLogEntry({ accountId: "acc_primary", requestId: "count", requestOperation: "count_tokens", requestKind: "count_tokens" }),
        createRequestLogEntry({ accountId: "acc_primary", requestId: "legacy", requestOperation: null }),
      ];
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(createRequestLogsResponse(requests, 5, false)) });
    });
    await page.goto("/dashboard");
    const table = page.getByRole("table").first();
    await expect(table.getByText("Web search", { exact: true })).toBeVisible();
    await expect(table.getByText("Responses · Warmup", { exact: true })).toBeVisible();
    await expect(table.getByText("Image edit", { exact: true })).toBeVisible();
    await expect(table.getByText("Token count", { exact: true })).toBeVisible();
    await expect(table.getByText("Unknown", { exact: true })).toBeVisible();
    await expect(table.getByRole("columnheader")).toHaveCount(12);
    await expect(table.getByRole("columnheader", { name: "Type" })).toHaveCount(0);
    await table.scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath(`operation-labels-${width}.png`), fullPage: true });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(overflow).toBe(false);
  });

  test(`Luna Reserve reuses Spark quota bars ${width}`, async ({ page }, testInfo) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width, height: 1000 });
    await installMobileContainmentFixtures(page, [createAccountSummary({
      accountId: "reserve-account", displayName: "Reserve account",
      additionalQuotas: [
        { limitName: "codex_spark", meteredFeature: "codex_bengalfox",
          displayLabel: "GPT-5.3-Codex-Spark", routingPolicy: "inherit",
          primaryWindow: { usedPercent: 35, windowMinutes: 300, resetAt: null }, secondaryWindow: null },
        { limitName: "gpt-reserve", meteredFeature: "base_model_inference",
          displayLabel: "Luna Reserve", routingPolicy: null, availability: "available",
          primaryWindow: { usedPercent: 25, windowMinutes: 300, resetAt: null },
          secondaryWindow: { usedPercent: 60, windowMinutes: 10080, resetAt: null } },
      ],
    })]);
    await page.goto("/accounts?selected=reserve-account");
    await expect(page.getByText("Luna Reserve", { exact: true })).toBeVisible();
    await expect(page.getByText("25% used", { exact: true })).toBeVisible();
    await expect(page.getByText("60% used", { exact: true })).toBeVisible();
    const reserve = page.getByText("Luna Reserve", { exact: true }).locator("../..");
    const spark = page.getByText("GPT-5.3-Codex-Spark", { exact: true }).locator("../..");
    expect(await reserve.getAttribute("class")).toBe(await spark.getAttribute("class"));
    const windows = reserve.getByTestId("additional-quota-windows");
    expect(await windows.evaluate((el) => getComputedStyle(el).gridTemplateColumns.split(" ").length))
      .toBe(width >= 640 ? 2 : 1);
    await expect(reserve.getByText("Weekly", { exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`reserve-bars-${width}.png`), fullPage: true });
  });
}

for (const width of [390, 1440]) {
  for (const provider of ["openrouter", "claude"] as const) {
    test(`provider account trends ${provider} ${width}`, async ({ page }, testInfo) => {
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.setViewportSize({ width, height: 1000 });
      await installMobileContainmentFixtures(page, []);
      const account = provider === "openrouter" ? createOpenRouterAccount({ id: "provider-test" }) : {
        planType: "pro", maxConcurrency: null, routingPolicy: "normal",
        id: "provider-test", name: "Claude test", isEnabled: true, credentialStatus: "ready",
        expiresAt: "2027-01-01T00:00:00Z",
        state: { subscription: null, subscription_updated_at: null, subscription_error: null,
          all_models: false, reasoning_restrictions: {}, selections: [], catalog: [], catalog_updated_at: null, catalog_error: null,
          usage_updated_at: null, usage_error: null },
        quota: { observedAt: null, models: [], windows: [] },
      };
      await page.route(`**/api/${provider}-accounts`, (route) => route.fulfill({ json: { accounts: [account] } }));
      const series = (provider === "claude" ? ["5-hour", "Weekly"] : ["Requests"]).map((label, j) => ({
        key: `series${j}`, label, points: Array.from({ length: 168 }, (_, i) => ({
          t: new Date(Date.UTC(2026, 8, 19) + i * 3600000).toISOString(),
          v: provider === "claude" ? 100 - ((i + j * 15) % 100) : i % 12,
        })),
      }));
      await page.route(`**/api/${provider}-accounts/provider-test/trends`, (route) => route.fulfill({ json: { series } }));
      await page.goto("/accounts?selected=provider-test");
      await acceptTelemetryConsentIfShown(page);
      const chart = page.getByRole("region", { name: provider === "claude" ? "Claude quota history" : "OpenRouter activity" });
      await expect(chart).toBeVisible();
      await expect(chart.locator(".recharts-surface")).toBeVisible();
      await expect(chart.locator(".recharts-area-curve").first()).toBeVisible();
      await chart.evaluate((element) => element.scrollIntoView({ block: "center" }));
      const box = await chart.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.x + box!.width).toBeLessThanOrEqual(width + 1);
      await chart.screenshot({ path: testInfo.outputPath(`${provider}-${width}.png`) });
    });
  }
  test(`quota webhook settings containment ${width}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    await installMobileContainmentFixtures(page);
    await page.goto("/settings");
    await acceptTelemetryConsentIfShown(page);
    const card = page.getByRole("region", { name: "Quota reset webhook" });
    await card.scrollIntoViewIfNeeded();
    await expect(card).toBeVisible();
    await expect(card.getByRole("switch", { name: "Enable notifications" })).toBeEnabled();
    await expect(card.getByRole("button", { name: "Test delivery" })).toBeDisabled();
    await expect(card.getByLabel("HTTPS webhook URL")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await card.screenshot({ path: testInfo.outputPath(`quota-webhook-${width}.png`) });
  });
}

async function acceptTelemetryConsentIfShown(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle");
  const consentDialog = page.getByRole("dialog", { name: "Anonymous telemetry" });
  if (await consentDialog.isVisible()) {
    await acceptTelemetryConsent(page, consentDialog);
  }
}

async function openLongSettingsPage(page: Page, scrollTop: number): Promise<void> {
  await page.goto("/settings", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
  await acceptTelemetryConsentIfShown(page);

  const advancedTrigger = page.getByRole("button", { name: "Show advanced settings" });
  await advancedTrigger.click();
  await expect(page.getByRole("heading", { name: "Firewall", exact: true })).toBeVisible();

  await page.evaluate((top) => window.scrollTo({ top, behavior: "instant" }), scrollTop);
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(scrollTop);
}

// `page.setViewportSize` resolves when the resize is dispatched, not when the
// browser has finished reflowing for it. Reading geometry immediately after
// has caught the 1440x900 case mid-reflow, reporting a 1488px document
// scrollWidth that settles back to 1440 a frame later. Hold until the document
// width stops moving, with a frame cap so a page that never settles fails on
// its assertion instead of hanging.
async function resizeViewportAndSettle(page: Page, size: { width: number; height: number }): Promise<void> {
  await page.setViewportSize(size);
  await page.evaluate(
    () =>
      new Promise<void>((resolve) => {
        let lastWidth = -1;
        let stableFrames = 0;
        let observedFrames = 0;
        const measure = () => {
          const width = document.documentElement.scrollWidth;
          stableFrames = width === lastWidth ? stableFrames + 1 : 0;
          lastWidth = width;
          observedFrames += 1;
          if (stableFrames >= 3 || observedFrames >= 120) {
            resolve();
            return;
          }
          requestAnimationFrame(measure);
        };
        requestAnimationFrame(measure);
      }),
  );
}

test("the built dashboard accepts real backend responses", async ({ page }) => {
  const apiFailures: string[] = [];
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];

  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    pageErrors.push(error.message);
  });
  page.on("requestfailed", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/")) {
      apiFailures.push(`${request.method()} ${path}: ${request.failure()?.errorText ?? "request failed"}`);
    }
  });
  page.on("response", (response) => {
    const path = new URL(response.url()).pathname;
    if (!path.startsWith("/api/")) {
      return;
    }
    if (!response.ok()) {
      apiFailures.push(`${response.request().method()} ${path}: HTTP ${response.status()}`);
    }
  });

  // Intentionally do not register page.route handlers: every response must
  // come from the uvicorn/FastAPI process started by the smoke harness.
  const requiredResponsesPromise = Promise.all(
    REQUIRED_API_PATHS.map((requiredPath) =>
      page.waitForResponse((response) => new URL(response.url()).pathname === requiredPath),
    ),
  );
  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  const requiredResponses = await requiredResponsesPromise;

  for (const response of requiredResponses) {
    expect(response.ok(), `${response.request().method()} ${new URL(response.url()).pathname}`).toBe(true);
  }
  const sessionResponse = requiredResponses[0];
  AuthSessionSchema.parse(await sessionResponse.json());
  const projectionsResponse = requiredResponses.find(
    (response) => new URL(response.url()).pathname === "/api/dashboard/projections",
  );
  if (!projectionsResponse) {
    throw new Error("Dashboard projections response was not captured");
  }
  DashboardProjectionsSchema.parse(await projectionsResponse.json());

  // First run against an empty database resolves telemetry consent as
  // undecided/default, so the informed-consent dialog must appear before
  // anything else. Exercise it as a first-class scenario: verify the exact
  // transmitted envelope is rendered, then keep telemetry enabled to unblock
  // the dashboard underneath.
  const consentDialog = page.getByRole("dialog", { name: "Anonymous telemetry" });
  await expect(consentDialog).toBeVisible();
  await expect(consentDialog.getByText('"instance_id"').first()).toBeVisible();
  await acceptTelemetryConsent(page, consentDialog);

  await expect(page.getByRole("heading", { name: "Dashboard", exact: true })).toBeVisible();
  await expect(page.getByText("No accounts connected yet", { exact: true })).toBeVisible();
  await expect(page.getByText("No requests yet", { exact: true })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);

  await page.waitForLoadState("networkidle");
  expect(apiFailures).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

test("dashboard usage donuts stay within supported viewports", async ({ page }) => {
  const viewportCases = [
    { size: { width: 320, height: 568 }, donutColumns: 1 },
    { size: { width: 390, height: 844 }, donutColumns: 1 },
    { size: { width: 1440, height: 900 }, donutColumns: 2 },
  ] as const;

  await installMobileContainmentFixtures(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize(viewportCases[0].size);
  await page.goto("/dashboard", { waitUntil: "networkidle" });

  // Match only the two usage donut headings ("5-Hour Credits" / "Weekly
  // Credits"); the weekly runway card also carries a "Weekly credits pace"
  // h3 now that a null backend pace falls back to the local projection.
  const usageHeadings = page.getByRole("heading", { level: 3 }).filter({ hasText: /Credits$/ });
  await expect(usageHeadings).toHaveCount(2);
  const requestTable = page.getByRole("table").first();
  await expect(requestTable).toBeVisible();

  for (const viewportCase of viewportCases) {
    await resizeViewportAndSettle(page, viewportCase.size);

    const usageMetrics = await usageHeadings.evaluateAll((headings) =>
      headings.map((heading) => {
        const card = heading.parentElement?.parentElement;
        const row = heading.parentElement?.nextElementSibling;
        const chart = row?.querySelector("svg")?.parentElement;
        const legend = row?.querySelector('[data-testid="donut-legend-list"]');
        if (!card || !row || !chart || !legend) {
          throw new Error("Expected the rendered donut card structure");
        }
        const bounds = (element: Element) => {
          const box = element.getBoundingClientRect();
          return { left: box.left, right: box.right, width: box.width };
        };
        return {
          card: bounds(card),
          row: bounds(row),
          chart: bounds(chart),
          legend: bounds(legend),
          gridColumns: getComputedStyle(card.parentElement!).gridTemplateColumns.split(" ").filter(Boolean).length,
        };
      }),
    );
    const documentMetrics = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    const summaryRight = await page
      .getByTestId("dashboard-account-summary-line")
      .evaluate((element) => element.getBoundingClientRect().right);
    const tableMetrics = await requestTable.evaluate((table) => {
      const scroller = table.closest('[data-slot="table-container"]');
      if (!scroller) {
        throw new Error("Expected the request table's local scroller");
      }
      const box = scroller.getBoundingClientRect();
      return {
        tableScrollWidth: table.scrollWidth,
        scrollerClientWidth: scroller.clientWidth,
        scrollerLeft: box.left,
        scrollerRight: box.right,
        overflowX: getComputedStyle(scroller).overflowX,
      };
    });

    expect(documentMetrics.scrollWidth).toBeLessThanOrEqual(documentMetrics.clientWidth);
    expect(summaryRight).toBeLessThanOrEqual(documentMetrics.clientWidth);
    for (const metrics of usageMetrics) {
      expect(metrics.gridColumns).toBe(viewportCase.donutColumns);
      for (const bounds of [metrics.card, metrics.row, metrics.chart, metrics.legend]) {
        expect(bounds.left).toBeGreaterThanOrEqual(0);
        expect(bounds.right).toBeLessThanOrEqual(documentMetrics.clientWidth);
      }
    }
    expect(tableMetrics.overflowX).toBe("auto");
    expect(tableMetrics.tableScrollWidth).toBeGreaterThan(tableMetrics.scrollerClientWidth);
    expect(tableMetrics.scrollerLeft).toBeGreaterThanOrEqual(0);
    expect(tableMetrics.scrollerRight).toBeLessThanOrEqual(documentMetrics.clientWidth);
  }
});

test("desktop route navigation resets new pages without overriding query, history, or hash scrolling", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openLongSettingsPage(page, 1400);

  const settingsHeadingTop = await page
    .getByRole("heading", { name: "Settings", exact: true })
    .evaluate((heading) => heading.getBoundingClientRect().top);
  expect(settingsHeadingTop).toBeLessThan(0);

  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  const dashboardHeading = page.getByRole("heading", { name: "Dashboard", exact: true });
  await expect(dashboardHeading).toBeInViewport();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);

  await page.evaluate(() => {
    document.body.style.minHeight = "3000px";
    window.scrollTo({ top: 700, behavior: "instant" });
  });
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(700);
  await page.getByRole("button", { name: "Request Logs", exact: true }).click();
  const conversationsItem = page.getByRole("menuitemradio", { name: "Conversations", exact: true });
  await expect(conversationsItem).toBeVisible();
  const queryScrollTop = await page.evaluate(() => window.scrollY);
  expect(queryScrollTop).toBeGreaterThan(0);
  await conversationsItem.click();
  await expect(page).toHaveURL(/\/dashboard\?view=conversations$/);
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(queryScrollTop);

  await page.goBack();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(queryScrollTop);

  await page.goBack();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(1400);

  await page.goto("/firewall", { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(/\/settings\?advanced=1#firewall$/);
  const firewallHeading = page.getByRole("heading", { name: "Firewall", exact: true });
  await expect(firewallHeading).toBeInViewport();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
});

test("mobile top-level navigation opens the destination heading at the top", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openLongSettingsPage(page, 1400);

  await page.getByRole("button", { name: "Open menu" }).click();
  await page.getByRole("link", { name: "Dashboard", exact: true }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Dashboard", exact: true })).toBeInViewport();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
});

test("the API key create dialog stays inside supported viewports", async ({ page }) => {
  const viewportCases = [
    { size: { width: 320, height: 568 }, columns: 1 },
    { size: { width: 390, height: 844 }, columns: 1 },
    { size: { width: 1440, height: 900 }, columns: 2 },
  ] as const;

  await page.goto("/apis", { waitUntil: "networkidle" });

  const consentDialog = page.getByRole("dialog", { name: "Anonymous telemetry" });
  if (await consentDialog.isVisible()) {
    await consentDialog.getByRole("button", { name: "Keep enabled" }).click();
    await expect(consentDialog).toBeHidden();
  }

  await expect(page.getByRole("heading", { name: "APIs", exact: true })).toBeVisible();
  const openDialogButton = page.getByRole("button", { name: "Create API Key" });
  const dialog = page.getByRole("dialog", { name: "Create API key" });
  const title = dialog.getByRole("heading", { name: "Create API key" });
  const closeButton = dialog.getByRole("button", { name: "Close" });
  const createButton = dialog.getByRole("button", { name: "Create" });

  for (const viewportCase of viewportCases) {
    await page.setViewportSize(viewportCase.size);
    await openDialogButton.click();

    for (const element of [dialog, title, closeButton, createButton]) {
      const box = await element.boundingBox();
      expect(box).not.toBeNull();
      if (!box) {
        throw new Error("Expected dialog element to have a bounding box");
      }
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.y).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(viewportCase.size.width);
      expect(box.y + box.height).toBeLessThanOrEqual(viewportCase.size.height);
    }

    const scrollRegion = dialog.getByTestId("api-key-create-scroll-region");
    await expect(scrollRegion).toHaveCount(1);
    const initialScrollState = await scrollRegion.evaluate((element) => ({
      clientHeight: element.clientHeight,
      overflowY: getComputedStyle(element).overflowY,
      scrollHeight: element.scrollHeight,
    }));
    expect(initialScrollState.overflowY).toBe("auto");
    expect(initialScrollState.scrollHeight).toBeGreaterThan(initialScrollState.clientHeight);

    const columnCount = await scrollRegion.locator(":scope > div").evaluate((element) =>
      getComputedStyle(element).gridTemplateColumns.split(" ").filter(Boolean).length,
    );
    expect(columnCount).toBe(viewportCase.columns);

    const finalField = dialog.getByRole("spinbutton", { name: "Weekly cost limit ($)" });
    await finalField.scrollIntoViewIfNeeded();
    await expect(finalField).toBeInViewport();
    await expect(title).toBeInViewport();
    await expect(closeButton).toBeInViewport();
    await expect(createButton).toBeInViewport();
    if (viewportCase.columns === 1) {
      expect(await scrollRegion.evaluate((element) => element.scrollTop)).toBeGreaterThan(0);
    }

    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  }

  await page.setViewportSize(viewportCases[0].size);
  await openDialogButton.click();
  await expect(dialog).toBeVisible();
  await page.mouse.click(8, Math.floor(viewportCases[0].size.height / 2));
  await expect(dialog).toBeHidden();
});


test("deactivated account actions stay inside list cells and responsive cards", async ({ page }) => {
  const accounts = [
    createAccountSummary({ accountId: "acc_recover", displayName: "Recovery account", status: "deactivated", availableResetCredits: 1 }),
    createAccountSummary({ accountId: "acc_reauth", displayName: "Reauth account", status: "reauth_required" }),
    createAccountSummary({ accountId: "acc_paused", displayName: "Paused account", status: "paused" }),
  ];
  await installMobileContainmentFixtures(page, accounts);
  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  await page.getByRole("radio", { name: "View accounts as list" }).click();
  const row = page.getByTestId("account-list-row").filter({ hasText: "Recovery account" });
  await expect(row.getByRole("button", { name: "Resume Recovery account", exact: true })).toBeVisible();
  await expect(row.getByRole("button", { name: "Re-authenticate Recovery account", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Resume Reauth account", exact: true })).toHaveCount(0);
  const actions = row.locator(":scope > div").last();
  await expect.poll(() => actions.evaluate((el) => {
    const parent = el.getBoundingClientRect();
    return Array.from(el.querySelectorAll("button")).every((button) => {
      const box = button.getBoundingClientRect();
      return box.left >= parent.left - 1 && box.right <= parent.right + 1 && box.top >= parent.top - 1 && box.bottom <= parent.bottom + 1;
    });
  })).toBe(true);
  for (const width of [640, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.getByRole("radio", { name: "View accounts as cards" }).click();
    const card = page.getByTestId("dashboard-account-cards").locator(":scope > div").filter({ hasText: "Recovery account" });
    await expect(card.getByRole("button", { name: "Resume", exact: true })).toBeVisible();
    await expect(card.getByRole("button", { name: "Re-auth", exact: true })).toBeVisible();
    await expect.poll(() => card.evaluate((el) => {
      const box = el.getBoundingClientRect();
      return Array.from(el.querySelectorAll("button")).every((button) => {
        const action = button.getBoundingClientRect();
        return action.left >= box.left - 1 && action.right <= box.right + 1;
      });
    })).toBe(true);
  }
});

test("the model source dialogs stay inside supported viewports", async ({ page }) => {
  const viewportSizes = [
    { width: 320, height: 568 },
    { width: 390, height: 844 },
    { width: 1440, height: 900 },
  ] as const;

  await page.goto("/settings", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
  await acceptTelemetryConsentIfShown(page);

  await page.getByRole("button", { name: "Show advanced settings" }).click();
  await expect(page.getByRole("heading", { name: "Model sources", exact: true })).toBeVisible();

  const openDialogButton = page.getByRole("button", { name: "Add source" });
  const dialog = page.getByRole("dialog", { name: "Create model source" });
  const title = dialog.getByRole("heading", { name: "Create model source" });
  const closeButton = dialog.getByRole("button", { name: "Close" });
  const createButton = dialog.getByRole("button", { name: "Create" });

  for (const size of viewportSizes) {
    await page.setViewportSize(size);
    await openDialogButton.click();

    // Enabling Reasoning reveals the effort fields, which is what pushed the
    // form past the viewport: with the capability off the default form still
    // fits on a desktop viewport. The capability checkboxes are Radix buttons
    // with no accessible name, so drive the wrapping label instead. The draft
    // survives closing the dialog, so toggle only when it is actually off.
    const reasoningToggle = dialog.locator("label", { hasText: /^Reasoning$/ });
    const reasoningCheckbox = reasoningToggle.locator('[role="checkbox"]');
    if ((await reasoningCheckbox.getAttribute("data-state")) !== "checked") {
      await reasoningToggle.click();
    }
    await expect(reasoningCheckbox).toHaveAttribute("data-state", "checked");
    await expect(dialog.locator("#model-source-reasoning-efforts")).toBeVisible();

    // The regression this covers: the dialog rendered taller than the viewport
    // with no scroll container, so the submit button was unreachable. These are
    // retrying assertions on purpose — the dialog opens with a zoom/fade
    // animation and the Reasoning toggle relayouts it, so a single
    // boundingBox() read can catch mid-animation geometry.
    for (const element of [dialog, title, closeButton, createButton]) {
      await expect(element).toBeInViewport({ ratio: 1 });
    }

    await expect(dialog).toHaveCSS("overflow-y", "clip");

    const scrollRegion = dialog.getByTestId("model-source-create-scroll-region");
    await expect(scrollRegion).toHaveCount(1);
    await expect(scrollRegion).toHaveCSS("overflow-y", "auto");
    await expect
      .poll(async () =>
        scrollRegion.evaluate((element) => element.scrollHeight - element.clientHeight),
      )
      .toBeGreaterThan(0);

    // The numeric and capability inputs carry no accessible name, so prove
    // reachability through the scroller itself: the end of the content must be
    // scrollable into view.
    const scrolled = await scrollRegion.evaluate((element) => {
      element.scrollTop = element.scrollHeight;
      return {
        clientHeight: element.clientHeight,
        scrollHeight: element.scrollHeight,
        scrollTop: element.scrollTop,
      };
    });
    expect(scrolled.scrollTop).toBeGreaterThan(0);
    expect(scrolled.scrollTop + scrolled.clientHeight).toBeGreaterThanOrEqual(
      scrolled.scrollHeight - 1,
    );

    // Scrolling the body must not carry the header or footer out of view.
    await expect(title).toBeInViewport({ ratio: 1 });
    await expect(closeButton).toBeInViewport({ ratio: 1 });
    await expect(createButton).toBeInViewport({ ratio: 1 });

    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  }
});

test("the model source edit dialog keeps Save visible in compact viewports", async ({ page, request }) => {
  const created = await request.post("/api/model-sources/", {
    data: {
      name: "Viewport regression source",
      baseUrl: "http://127.0.0.1:9/v1",
      models: [{
        model: "viewport-regression-model",
        rawMetadataJson: JSON.stringify({ supports_reasoning: true, reasoning_efforts: ["low", "high"] }),
      }],
    },
  });
  expect(created.ok()).toBe(true);
  const source = await created.json() as { id: string };
  try {
    await page.goto("/settings", { waitUntil: "domcontentloaded" });
    await acceptTelemetryConsentIfShown(page);
    await page.getByRole("button", { name: "Show advanced settings" }).click();
    for (const size of [{ width: 320, height: 568 }, { width: 390, height: 844 }, { width: 1440, height: 900 }]) {
      await page.setViewportSize(size);
      await page.getByRole("button", { name: "Edit Viewport regression source model source", exact: true }).click();
      const dialog = page.getByRole("dialog", { name: "Edit model source" });
      const save = dialog.getByRole("button", { name: "Save", exact: true });
      const title = dialog.getByRole("heading", { name: "Edit model source" });
      const close = dialog.getByRole("button", { name: "Close" });
      await expect(dialog).toHaveCSS("overflow-y", "clip");
      const scroll = dialog.getByTestId("model-source-edit-scroll-region");
      await expect(scroll).toHaveCount(1);
      await expect(scroll).toHaveCSS("overflow-y", "auto");
      for (const control of [dialog, title, close, save]) await expect(control).toBeInViewport({ ratio: 1 });
      // Assert rendered spacing, so a missing utility fails this browser path.
      await expect.poll(() => scroll.evaluate((el) => {
        const first = el.children[0].getBoundingClientRect();
        const second = el.children[1].getBoundingClientRect();
        return second.top - first.bottom;
      })).toBeGreaterThanOrEqual(15);
      await expect.poll(() => scroll.evaluate((el) => el.scrollHeight - el.clientHeight)).toBeGreaterThan(0);
      await scroll.evaluate((el) => { el.scrollTop = el.scrollHeight; });
      await expect.poll(() => scroll.evaluate((el) => el.scrollHeight - el.clientHeight - el.scrollTop)).toBeLessThanOrEqual(1);
      for (const control of [title, close, save]) await expect(control).toBeInViewport({ ratio: 1 });
      await page.keyboard.press("Escape");
      await expect(dialog).toBeHidden();
    }
  } finally {
    expect((await request.delete(`/api/model-sources/${source.id}`)).ok()).toBe(true);
  }
});
