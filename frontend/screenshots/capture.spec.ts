import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page, type Route } from "@playwright/test";

import {
  accounts,
  accountTrends,
  apiKeys,
  authSession,
  createRequestLogsResponse,
  filterOptions,
  models,
  overview,
  requestLogs,
  resetCreditSnapshots,
  settings,
  upstreamProxyAdmin,
  unauthenticatedSession,
} from "./fixtures";
import { createOpenRouterAccount } from "../src/features/openrouter/test-fixtures";
import type { ClaudeAccount } from "../src/features/claude/api";
import {
  createAccountSummary,
  createConversationDetails,
  createConversationEntry,
  createConversationsResponse,
  createModelSource,
} from "../src/test/mocks/factories";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = path.resolve(__dirname, "../../docs/screenshots");
const SCREENSHOT_PORT = process.env.SCREENSHOT_PORT ?? "4173";
const BASE_URL = process.env.SCREENSHOT_BASE_URL ?? `http://localhost:${SCREENSHOT_PORT}`;
const THEME_KEY = "codex-lb-theme";
const SETTLE_MS = 1500;

test("dashboard provider cards share sizing and anatomy", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const native = [
    createAccountSummary({
      accountId: "native-alias",
      displayName: "Codex alias with email",
      email: "alias@example.com",
      availableResetCredits: 3,
    }),
    createAccountSummary({
      accountId: "native-plain",
      displayName: "plain@example.com",
      email: "plain@example.com",
    }),
    createAccountSummary({
      accountId: "native-actions",
      displayName: "Codex requiring recovery",
      status: "deactivated",
      availableResetCredits: 2,
    }),
  ];
  const openrouter = [
    createOpenRouterAccount({ id: "router-ready", name: "OpenRouter" }),
    createOpenRouterAccount({
      id: "router-stale",
      name: "OpenRouter stale balance",
    }),
  ];
  openrouter[1].state.key_error = "Monitoring failed";
  const claude: ClaudeAccount = {
    id: "claude-two",
    name: "Claude quotas",
    isEnabled: true,
    maxConcurrency: null,
    routingPolicy: "normal",
    credentialStatus: "ready",
    expiresAt: "2026-10-01T12:00:00Z",
    state: {
      all_models: true,
      reasoning_restrictions: {},
      selections: [],
      catalog: [],
      catalog_updated_at: null,
      catalog_error: null,
      usage_updated_at: null,
      usage_error: null,
    },
    quota: {
      observedAt: null,
      models: [],
      windows: [
        {
          name: "five_hour",
          utilization: null,
          resetsAt: null,
          freshness: "unknown",
          exhausted: false,
        },
        {
          name: "seven_day",
          utilization: 104,
          resetsAt: "2026-10-03T12:00:00Z",
          freshness: "stale",
          exhausted: false,
        },
      ],
    },
  };
  const claudeAccounts = [
    claude,
    {
      ...claude,
      id: "claude-weekly",
      name: "Claude weekly only",
      quota: { ...claude.quota, windows: [claude.quota.windows[1]] },
    },
  ];
  await interceptApi(page, authSession, native);
  await page.route("**/health/ready", (route) =>
    fulfill(route, { status: "ok" }),
  );
  await page.route("**/api/dashboard/overview**", (route) =>
    fulfill(route, { ...overview, accounts: native }),
  );
  await page.route("**/api/openrouter-accounts", (route) =>
    fulfill(route, { accounts: openrouter }),
  );
  await page.route("**/api/claude-accounts", (route) =>
    fulfill(route, { accounts: claudeAccounts }),
  );
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const theme of ["light", "dark"] as const) {
    await applyTheme(page, theme);
    await page.goto(BASE_URL);
    const grid = page.getByTestId("dashboard-account-cards");
    await expect(grid.locator(".card-hover")).toHaveCount(7);
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      const bounds = await grid.evaluate((element) =>
        Array.from(element.children).map((wrapper) => {
          const card = wrapper.querySelector<HTMLElement>(".card-hover")!;
          const rect = card.getBoundingClientRect();
          const body = card.querySelector<HTMLElement>(
            '[data-slot="account-card-body"]',
          )!;
          const footer = card.querySelector<HTMLElement>(
            '[data-slot="account-card-actions"]',
          )!;
          return {
            height: rect.height,
            width: rect.width,
            top: rect.top,
            bodyOffset: body.getBoundingClientRect().top - rect.top,
            footerInset: rect.bottom - footer.getBoundingClientRect().bottom,
            contained: Array.from(
              card.querySelectorAll<HTMLElement>("p, button, a, [data-slot]"),
            ).every((child) => {
              const r = child.getBoundingClientRect();
              return (
                r.left >= rect.left - 1 &&
                r.right <= rect.right + 1 &&
                r.top >= rect.top &&
                r.bottom <= rect.bottom + 1
              );
            }),
          };
        }),
      );
      expect(bounds.every((card) => card.contained)).toBe(true);
      expect(
        Math.max(...bounds.map((card) => card.width)) -
          Math.min(...bounds.map((card) => card.width)),
      ).toBeLessThan(1);
      expect(
        Math.max(...bounds.map((card) => card.bodyOffset)) -
          Math.min(...bounds.map((card) => card.bodyOffset)),
      ).toBeLessThan(1);
      expect(
        Math.max(...bounds.map((card) => card.footerInset)) -
          Math.min(...bounds.map((card) => card.footerInset)),
      ).toBeLessThan(1);
      const heightDifference =
        Math.max(...bounds.map((card) => card.height)) -
        Math.min(...bounds.map((card) => card.height));
      if (width >= 640) expect(heightDifference).toBeLessThan(1);
      else expect(heightDifference).toBeGreaterThan(20);
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= window.innerWidth,
          ),
        )
        .toBe(true);
      for (const provider of ["codex", "claude"]) {
        const card = grid.getByTestId(`${provider}-account-card`).first();
        expect(
          await card
            .locator('[data-slot="account-card-body"] > div')
            .first()
            .evaluate(
              (el) =>
                getComputedStyle(el).gridTemplateColumns.split(" ").length,
            ),
        ).toBe(2);
      }
      if (width === 1440)
        await grid.screenshot({
          path: testInfo.outputPath(`provider-cards-${theme}-desktop.png`),
          animations: "disabled",
          style: "header, footer { visibility: hidden !important; }",
        });
      if (width === 390) {
        await grid
          .getByTestId("claude-account-card")
          .first()
          .screenshot({
            path: testInfo.outputPath(`provider-cards-${theme}-mobile.png`),
            animations: "disabled",
            style: "header, footer { visibility: hidden !important; }",
          });
      }
    }
  }
  expect(errors).toEqual([]);
});

test("Codex and OpenRouter shared model controls", async ({ page }, testInfo) => {
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  const native = { ...accounts[0], alias: "Codex Research" };
  let nativeModels = {
    allModels: true, selectedModels: ["gpt-6-astra"], reasoningRestrictions: {},
    catalog: [
      { model: "gpt-6-astra", displayName: "GPT-6 Astra", contextWindow: 272000, supportsTools: true, supportsVision: true, supportsReasoning: true, available: true, reasoningLevels: ["none", "low", "medium", "high", "max"], defaultReasoningLevel: "medium" },
      { model: "gpt-6-sol", displayName: "GPT-6 Sol", contextWindow: 272000, supportsTools: true, supportsVision: true, supportsReasoning: true, available: true, reasoningLevels: ["low", "medium", "high", "max"], defaultReasoningLevel: "low" },
    ],
  };
  const provider = createOpenRouterAccount({ name: "OpenRouter Research" });
  provider.state.catalog = [{ id: "vendor/coder", name: "Coder", context_length: 1000000, image: null,
    pricing: { prompt: 0.0000005, input_cache_read: 0.00000005, completion: 0.000002 }, supported_parameters: ["tools", "reasoning"],
    architecture: { input_modalities: ["text", "image"], output_modalities: ["text"] },
    top_provider: { context_length: 1000000, max_completion_tokens: 64000 }, reasoning: null }];
  provider.state.selections = [{ model: "vendor/coder", contextWindow: 262144, maxOutputTokens: null, displayName: null }];
  await interceptApi(page, authSession, [native]);
  await page.route("**/health/ready", route => fulfill(route, { status: "ok" }));
  await page.route(`**/api/accounts/${native.accountId}/models`, async (route) => {
    if (route.request().method() === "PUT") nativeModels = { ...nativeModels, ...route.request().postDataJSON() };
    return fulfill(route, nativeModels);
  });
  await page.route("**/api/openrouter-accounts**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname.endsWith("/trends")) return fulfill(route, { series: [{ key: "requests", label: "Requests", colorIndex: 0, dashed: false,
      points: [{ t: "2026-09-29T10:00:00Z", v: 5 }, { t: "2026-09-29T11:00:00Z", v: 10 }] }] });
    if (route.request().method() === "PATCH") {
      const body = route.request().postDataJSON();
      if (body.allModels !== undefined) provider.state.all_models = body.allModels;
      if (body.routingPolicy !== undefined) provider.routingPolicy = body.routingPolicy;
      if (body.selections !== undefined) provider.state.selections = body.selections;
      if (body.reasoningRestrictions !== undefined) provider.state.reasoning_restrictions = body.reasoningRestrictions;
      return fulfill(route, provider);
    }
    return fulfill(route, { accounts: [provider] });
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await applyTheme(page, "light");
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const [id, label, expectedAll] of [[native.accountId, "codex", true], [provider.id, "openrouter", false]] as const) {
      await page.goto(`${BASE_URL}/accounts?selected=${id}`);
      await expect(page.getByRole("switch", { name: /All models/ })).toHaveCount(0);
      if (label === "openrouter") {
        const curve = page.locator('[aria-label="OpenRouter activity"] .recharts-area-curve');
        await expect(curve).toHaveCount(1);
        expect(await curve.getAttribute("d")).not.toContain("NaN");
      } else {
        await expect(page.locator(".recharts-area-curve").first()).toBeVisible();
        for (const curve of await page.locator(".recharts-area-curve").all()) {
          expect(await curve.getAttribute("d")).not.toContain("NaN");
        }
      }
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`${label}-detail-${width}.png`), fullPage: true, animations: "disabled" });
      await page.getByRole("button", { name: label === "codex" ? "Models (All)" : "Models (1)", exact: true }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await expect(page.getByRole("switch", { name: /All models/ })).toBeChecked({ checked: expectedAll });
      await page.screenshot({ path: testInfo.outputPath(`${label}-models-${width}.png`), animations: "disabled" });
      await page.getByRole("button", { name: "Cancel", exact: true }).click();
    }
  }
  await page.goto(`${BASE_URL}/accounts?selected=${native.accountId}`);
  await page.getByRole("button", { name: "Models (All)", exact: true }).click();
  await page.getByRole("switch", { name: /All models/ }).click();
  await page.getByRole("button", { name: "Save 1 model", exact: true }).click();
  await expect(page.getByRole("button", { name: "Models (1)", exact: true })).toBeVisible();
  expect(nativeModels.selectedModels).toEqual(["gpt-6-astra"]);
  await page.getByRole("button", { name: "Models (1)", exact: true }).click();
  await page.getByRole("switch", { name: /All models/ }).click();
  await page.getByRole("button", { name: "Save 1 model", exact: true }).click();
  await expect(page.getByRole("button", { name: "Models (All)", exact: true })).toBeVisible();
  expect(browserErrors).toEqual([]);
});

test("Claude automatic models and shared account presentation", async ({ page }, testInfo) => {
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  const account: ClaudeAccount = {
    id: "claude-preview", name: "Claude Research", isEnabled: true,
    maxConcurrency: null, routingPolicy: "burn_first", credentialStatus: "ready",
    expiresAt: "2026-10-01T12:00:00Z",
    state: {
      all_models: false,
      reasoning_restrictions: {},
      selections: [{ model: "claude-opus-5" }],
      catalog: [
        { id: "claude-opus-5", display_name: "Claude Opus 5", max_input_tokens: 1000000, max_tokens: 128000, reasoning_levels: ["low", "medium", "high", "max"], default_reasoning_level: "high" },
        { id: "claude-haiku-4-5", display_name: "Claude Haiku 4.5", max_input_tokens: 200000, max_tokens: 64000, reasoning_levels: ["low", "medium", "high", "max"], default_reasoning_level: "medium" },
        { id: "unknown", display_name: "Model awaiting metadata", max_input_tokens: null, max_tokens: null, reasoning_levels: [], default_reasoning_level: null },
      ],
      catalog_updated_at: "2026-09-29T08:00:00Z", catalog_error: null,
      usage_updated_at: "2026-09-29T08:00:00Z", usage_error: null,
    },
    quota: { observedAt: "2026-09-29T08:00:00Z", models: [], windows: [
      { name: "five_hour", utilization: 24, resetsAt: "2026-09-29T13:00:00Z", freshness: "fresh", exhausted: false },
      { name: "seven_day", utilization: 62, resetsAt: "2026-10-03T12:00:00Z", freshness: "stale", exhausted: false },
    ] },
  };
  await interceptApi(page, authSession, accounts.slice(0, 1));
  await page.route("**/api/dashboard/overview**", route => fulfill(route, { ...overview, accounts: accounts.slice(0, 1) }));
  await page.route("**/health/ready", route => fulfill(route, { status: "ok" }));
  await page.route("**/api/claude-accounts**", (route) => {
    const p = new URL(route.request().url()).pathname;
    if (p === "/api/claude-accounts") return fulfill(route, { accounts: [account] });
    if (p.endsWith("/version")) return fulfill(route, {
      effectiveVersion: "2.1.283", discoveredVersion: "2.1.283", pinnedVersion: null,
      lastCheckedAt: null, lastChangedAt: null, error: null,
    });
    if (p.endsWith("/trends")) return fulfill(route, { series: [
      { key: "five_hour", label: "5-hour", points: [
        { t: "2026-09-29T08:00:00Z", v: 92 }, { t: "2026-09-29T09:00:00Z", v: 76 },
        { t: "2026-09-29T10:00:00Z", v: null }, { t: "2026-09-29T11:00:00Z", v: 68 }, { t: "2026-09-29T12:00:00Z", v: 60 },
      ], dashed: false, colorIndex: 0 },
      { key: "seven_day", label: "Weekly", points: [
        { t: "2026-09-29T08:00:00Z", v: 54 }, { t: "2026-09-29T09:00:00Z", v: 50 },
        { t: "2026-09-29T10:00:00Z", v: null }, { t: "2026-09-29T11:00:00Z", v: 42 }, { t: "2026-09-29T12:00:00Z", v: 38 },
      ], dashed: false, colorIndex: 1 },
      { key: "weekly_plan", label: "Weekly plan", dashed: true, colorIndex: 1, points: [
        { t: "2026-09-29T08:30:00Z", v: 76.19 }, { t: "2026-09-29T12:00:00Z", v: 61.90 },
      ] },
    ] });
    return route.abort();
  });
  await applyTheme(page, "light");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(`${BASE_URL}/accounts?selected=claude-preview`);
  await expect(page.getByRole("combobox", { name: "Routing policy" })).toBeVisible();
  await expect(page.getByRole("switch", { name: /All models/ })).toHaveCount(0);
  await expect(page.locator('[aria-label="Claude quota history"] .recharts-surface')).toBeVisible();
  await expect(page.getByText("Weekly plan", { exact: true })).toBeVisible();
  await expect(page.getByText(/Weekly Opus/)).toHaveCount(0);
  const curves = page.locator('[aria-label="Claude quota history"] .recharts-area-curve');
  await expect(curves).toHaveCount(2);
  for (const curve of await curves.all()) {
    expect((await curve.getAttribute("d"))!.match(/M/g)).toHaveLength(2);
    expect(await curve.getAttribute("d")).not.toContain("NaN");
  }
  await page.screenshot({ path: testInfo.outputPath("claude-detail-desktop.png"), fullPage: true, animations: "disabled" });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("claude-detail-mobile.png"), fullPage: true, animations: "disabled" });
  await page.getByRole("button", { name: "Models (1)", exact: true }).click();
  await expect(page.getByRole("switch", { name: /All models/ })).not.toBeChecked();
  await expect(page.getByText(/1M context.*128K maximum output.*64K default output/i)).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "Model awaiting metadata — Unavailable" })).toBeDisabled();
  await page.screenshot({ path: testInfo.outputPath("claude-models-mobile.png"), animations: "disabled" });
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole("button", { name: "Models (1)", exact: true }).click();
  await page.screenshot({ path: testInfo.outputPath("claude-models-desktop.png"), animations: "disabled" });
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.goto(BASE_URL);
  await expect(page.getByTestId("claude-account-card")).toBeVisible();
  await page.getByTestId("claude-account-card").scrollIntoViewIfNeeded();
  await page.getByTestId("claude-account-card").screenshot({ path: testInfo.outputPath("claude-dashboard.png"), animations: "disabled" });
  await page.getByRole("radio", { name: /List/i }).click();
  const rows = page.getByTestId("dashboard-account-list");
  await expect(rows.getByText("Claude Research")).toBeVisible();
  await rows.screenshot({ path: testInfo.outputPath("claude-dashboard-list.png"), animations: "disabled" });
  expect(browserErrors).toEqual([]);
});

// CSS injected before page load to skip all animations/transitions instantly.
const DISABLE_ANIMATIONS_CSS = `
*, *::before, *::after {
  animation-duration: 0s !important;
  animation-delay: 0s !important;
  transition-duration: 0s !important;
  transition-delay: 0s !important;
}
`;

type Theme = "light" | "dark";
type SessionOverride = typeof authSession | typeof unauthenticatedSession;

test("API comparison trends across metrics and modes on desktop and mobile", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await interceptApi(page);
  await page.route("**/health/ready", (route) => fulfill(route, { status: "ok" }));
  const names = ["Production", "Development", "Research", "Automation", "Mobile", "Test", "Unpriced provider"];
  const keys = names.map((name, index) => ({ ...apiKeys[index % apiKeys.length], id: `compare-${index}`, name }));
  let trendRequests = 0;
  await page.route("**/api/api-keys/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/api-keys/") return fulfill(route, keys);
    if (path !== "/api/api-keys/trends") return route.fallback();
    trendRequests++;
    return fulfill(route, {
      since: "2026-09-23T00:00:00Z", until: "2026-09-30T00:00:00Z",
      series: keys.map((key, index) => {
        const points = Array.from({ length: 168 }, (_, hour) => {
          const date = new Date(Date.UTC(2026, 8, 23, hour));
          const activity = Math.max(0, Math.sin((hour + index * 3) / 4)) * (1 + hour / 168);
          return { t: date.toISOString(), v: index === 6 ? 0 : Number((activity * (7 - index) / 8).toFixed(4)),
            pricedRequests: index === 6 ? 0 : 5, unpricedRequests: index === 6 ? 5 : 0,
            unmeteredRequests: 0, coverageUnknown: false };
        });
        return { keyId: key.id, name: key.name, isDeleted: false, cost: points,
          tokens: points.map((point, hour) => ({ ...point, v: Math.round((index + 1) * (1 + Math.sin(hour / 4)) * 1800) })) };
      }),
    });
  });
  await applyTheme(page, "light");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(BASE_URL);
  await page.getByRole("link", { name: "APIs", exact: true }).click();
  const panel = page.getByTestId("api-keys-comparison-trend");
  await expect(panel.getByRole("heading", { name: "Usage Trend by API Key (7d)" })).toBeVisible();
  await expect(panel.locator(".recharts-area-curve")).toHaveCount(6);
  const legend = panel.getByRole("group", { name: "Visible API keys" });
  await expect(legend.getByRole("button", { name: "Other", exact: true })).toBeVisible();
  await expect(legend.getByRole("button", { name: "Production", exact: true })).toBeVisible();
  await panel.locator("..").screenshot({ path: testInfo.outputPath("api-trends-overview-desktop.png"), animations: "disabled" });
  const plot = panel.locator(".recharts-surface");
  const bounds = (await plot.boundingBox())!;
  await plot.hover({ position: { x: bounds.width * 0.7, y: bounds.height * 0.5 } });
  await expect(panel.locator('[role="tooltip"]')).toContainText("Some costs are unknown; displayed amounts include recorded costs only.");
  await page.mouse.move(0, 0);
  await panel.getByRole("button", { name: "Cumulative", exact: true }).click();
  await expect(panel.locator(".recharts-line-curve")).toHaveCount(6);
  for (const curve of await panel.locator(".recharts-line-curve").all()) {
    expect(await curve.getAttribute("d")).not.toContain("NaN");
  }
  await panel.screenshot({ path: testInfo.outputPath("api-trends-cumulative-cost.png"), animations: "disabled" });
  await panel.getByRole("button", { name: "Tokens", exact: true }).click();
  await expect(legend.getByRole("button", { name: "Unpriced provider", exact: true })).toBeVisible();
  await expect(legend.getByRole("button", { name: "Production", exact: true })).toHaveCount(0);
  await legend.getByRole("button", { name: "Research", exact: true }).click();
  await expect(panel.locator(".recharts-line-curve")).toHaveCount(5);
  await panel.getByRole("button", { name: "Per hour", exact: true }).click();
  await expect(panel.locator(".recharts-area-curve")).toHaveCount(5);
  await expect(legend.getByRole("button", { name: "Research", exact: true })).toHaveAttribute("aria-pressed", "false");
  await legend.getByRole("button", { name: "Research", exact: true }).click();
  await expect(panel.locator(".recharts-area-curve")).toHaveCount(6);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await panel.evaluate((element) => element.scrollIntoView({ block: "center", behavior: "instant" }));
  await panel.screenshot({ path: testInfo.outputPath("api-trends-hourly-tokens-mobile.png"), animations: "disabled" });
  await panel.getByRole("button", { name: "Cost", exact: true }).click();
  await panel.getByRole("button", { name: "Cumulative", exact: true }).click();
  await panel.evaluate((element) => element.scrollIntoView({ block: "center", behavior: "instant" }));
  await panel.screenshot({ path: testInfo.outputPath("api-trends-cumulative-cost-mobile.png"), animations: "disabled" });
  expect(trendRequests).toBe(1);
  expect(errors).toEqual([]);
});

test("API lifetime cost bars and compact labels on desktop and mobile", async ({ page }, testInfo) => {
  await interceptApi(page);
  await page.route("**/api/api-keys/**", (route) => {
    if (new URL(route.request().url()).pathname !== "/api/api-keys/") return route.fallback();
    return fulfill(route, [{
      ...apiKeys[0],
      usageSummary: {
        requestCount: 426943, totalTokens: 80000, cachedInputTokens: 12000,
        totalCostUsd: 44248.05, pricedRequests: 422859, unpricedRequests: 99,
        unmeteredRequests: 3985, coverageUnknown: false,
      },
    }, {
      ...apiKeys[1],
      usageSummary: {
        requestCount: 10000, totalTokens: 40000, cachedInputTokens: 6000,
        totalCostUsd: 14749.35, pricedRequests: 10000, unpricedRequests: 0,
        unmeteredRequests: 0, coverageUnknown: false,
      },
    }]);
  });
  await applyTheme(page, "light");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(BASE_URL);
  await page.getByRole("link", { name: "APIs", exact: true }).click();
  const panel = page.getByTestId("api-keys-overview-cost-panel");
  await expect(panel.getByText("$44,248.05 · 75%", { exact: true })).toBeVisible();
  await expect(panel.getByText("$14,749.35 · 25%", { exact: true })).toBeVisible();
  await expect(panel.getByText("Share of recorded estimated cost", { exact: true })).toBeVisible();
  await expect(panel).not.toContainText(/known|incomplete|priced|unmetered/);
  for (const [name, width, height] of [["desktop", 1440, 900], ["mobile", 390, 844]] as const) {
    await page.setViewportSize({ width, height });
    await panel.evaluate((element) => element.scrollIntoView({ block: "center" }));
    await expect(panel.getByText("$44,248.05 · 75%", { exact: true })).toBeVisible();
    await expect(panel.getByRole("meter", { name: "Production" })).toBeVisible();
    await expect(panel.getByRole("meter", { name: "Development" })).toBeVisible();
    await expect.poll(() => panel.getByRole("meter", { name: "Production" }).evaluate(
      (element) => Math.round(element.firstElementChild!.getBoundingClientRect().width / element.getBoundingClientRect().width * 100),
    )).toBe(75);
    await expect.poll(() => panel.getByRole("meter", { name: "Development" }).evaluate(
      (element) => Math.round(element.firstElementChild!.getBoundingClientRect().width / element.getBoundingClientRect().width * 100),
    )).toBe(25);
    await expect.poll(() => panel.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
    await panel.screenshot({ path: testInfo.outputPath(`api-cost-${name}.png`), animations: "disabled" });
  }
});

// ── Route interception ──

function fulfill(route: Route, data: unknown) {
  return route.fulfill({
    contentType: "application/json",
    body: JSON.stringify(data),
  });
}

async function interceptApi(
  page: Page,
  session: SessionOverride = authSession,
  accountList = accounts,
) {
  await page.route("**/api/**", (route) => {
    const url = new URL(route.request().url());
    const p = url.pathname;

    if (p === "/api/dashboard-auth/session") return fulfill(route, session);
    if (p === "/api/dashboard/overview") return fulfill(route, overview);
    if (p === "/api/request-logs/options") return fulfill(route, filterOptions);
    if (p === "/api/request-logs") {
      const limit = Math.max(1, Number(url.searchParams.get("limit") ?? 50));
      const offset = Math.max(0, Number(url.searchParams.get("offset") ?? 0));
      const slice = requestLogs.slice(offset, offset + limit);
      return fulfill(route, createRequestLogsResponse(slice, requestLogs.length, offset + limit < requestLogs.length));
    }
    if (p === "/api/conversations") {
      return fulfill(
        route,
        createConversationsResponse([createConversationEntry({ conversationId: "conv_abc" })], 1, false),
      );
    }
    if (p === "/api/conversations/conv_abc") {
      return fulfill(route, createConversationDetails({ conversationId: "conv_abc" }));
    }
    if (p === "/api/accounts") return fulfill(route, { accounts: accountList });
    if (p === "/api/openrouter-accounts") return fulfill(route, { accounts: [] });
    if (p === "/api/claude-accounts") return fulfill(route, { accounts: [] });
    const trendsMatch = p.match(/^\/api\/accounts\/([^/]+)\/trends$/);
    if (trendsMatch) {
      const trends = accountTrends[trendsMatch[1]];
      if (trends) return fulfill(route, trends);
      return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ error: { code: "account_not_found", message: "Account not found" } }) });
    }
    if (p === "/api/settings") return fulfill(route, settings);
    if (p === "/api/settings/upstream-proxy") return fulfill(route, upstreamProxyAdmin);
    const usageResetCreditsMatch = p.match(/^\/api\/accounts\/([^/]+)\/usage-reset-credits$/);
    if (usageResetCreditsMatch) {
      const accountId = decodeURIComponent(usageResetCreditsMatch[1]);
      const snapshot = resetCreditSnapshots[accountId];
      return fulfill(route, {
        accountId,
        rateLimitResetCredits: { availableCount: snapshot?.availableCount ?? 0 },
      });
    }
    const resetCreditsMatch = p.match(/^\/api\/accounts\/([^/]+)\/rate-limit-reset-credits$/);
    if (resetCreditsMatch) {
      return fulfill(route, resetCreditSnapshots[decodeURIComponent(resetCreditsMatch[1])] ?? null);
    }
    if (p === "/api/models") return fulfill(route, { models });
    if (p === "/api/api-keys" || p === "/api/api-keys/") return fulfill(route, apiKeys);
    if (p === "/api/api-keys/trends") return fulfill(route, { since: "2026-09-23T00:00:00Z", until: "2026-09-30T00:00:00Z", series: [] });

    return route.abort();
  });

  await page.route("**/health", (route) => fulfill(route, { status: "ok" }));
}

// ── Theme ──

async function applyTheme(page: Page, theme: Theme) {
  await page.addInitScript(
    ({ key, value }: { key: string; value: string }) => {
      window.localStorage.setItem(key, value);
    },
    { key: THEME_KEY, value: theme },
  );
}

// ── Capture helper ──

async function capture(
  page: Page,
  opts: {
    file: string;
    theme: Theme;
    route: string;
    fullPage?: boolean;
    session?: SessionOverride;
    waitFor?: string;
    beforeScreenshot?: (page: Page) => Promise<void>;
  },
) {
  await applyTheme(page, opts.theme);
  await interceptApi(page, opts.session);

  // Trigger prefers-reduced-motion so the existing CSS media query kicks in.
  await page.emulateMedia({ reducedMotion: "reduce" });
  // Inject blanket CSS before page scripts run to kill CSS animations instantly.
  // (addInitScript survives navigation; addStyleTag on about:blank does not.)
  await page.addInitScript((css: string) => {
    const style = document.createElement("style");
    style.textContent = css;
    (document.head ?? document.documentElement).appendChild(style);
  }, DISABLE_ANIMATIONS_CSS);

  await page.goto(`${BASE_URL}${opts.route}`, { waitUntil: "networkidle" });

  if (opts.waitFor) {
    await page.waitForSelector(opts.waitFor, { timeout: 10_000 });
  }

  // Short settle for JS-driven rendering (Recharts SVG mutations etc.)
  await page.waitForTimeout(SETTLE_MS);

  if (opts.beforeScreenshot) {
    await opts.beforeScreenshot(page);
  }

  // For fullPage captures, un-fix the sticky footer so it flows at the document bottom
  // instead of floating at the original viewport boundary.
  if (opts.fullPage) {
    await page.evaluate(() => {
      const footer = document.querySelector("footer");
      if (footer) footer.style.position = "relative";
      // Remove the bottom padding that was reserving space for the fixed footer
      const layout = document.querySelector("main")?.parentElement;
      if (layout) layout.style.paddingBottom = "0";
    });
  }

  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, opts.file),
    type: "jpeg",
    quality: 90,
    fullPage: opts.fullPage ?? false,
  });
}

// ── Scenes ──

test("dashboard — light", async ({ page }) => {
  await capture(page, { file: "dashboard.jpg", theme: "light", route: "/dashboard" });
});

test("dashboard — dark", async ({ page }) => {
  await capture(page, { file: "dashboard-dark.jpg", theme: "dark", route: "/dashboard" });
});

test("dashboard conversations — desktop", async ({ page }) => {
  await capture(page, {
    file: "dashboard-conversations.jpg",
    theme: "light",
    route: "/dashboard?view=conversations",
    waitFor: '[data-slot="table"]',
  });
});

test("dashboard conversations — narrow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await capture(page, {
    file: "dashboard-conversations-narrow.jpg",
    theme: "light",
    route: "/dashboard?view=conversations",
    waitFor: '[data-slot="table"]',
  });
});

test("dashboard conversation details dialog", async ({ page }) => {
  await capture(page, {
    file: "dashboard-conversation-details.jpg",
    theme: "light",
    route: "/dashboard?view=conversations",
    waitFor: '[data-slot="table"]',
    beforeScreenshot: async (currentPage) => {
      await currentPage.getByRole("button", { name: /view details/i }).click();
      await currentPage.getByRole("dialog").waitFor();
      await currentPage.getByTestId("conversation-details-information").waitFor();
    },
  });
});

test("accounts — light", async ({ page }) => {
  await capture(page, { file: "accounts.jpg", theme: "light", route: "/accounts" });
});

test("accounts — dark", async ({ page }) => {
  await capture(page, { file: "accounts-dark.jpg", theme: "dark", route: "/accounts" });
});

test("accounts list keeps many rows in an internal scroll region", async ({ page }) => {
  const manyAccounts = Array.from({ length: 40 }, (_, index) =>
    createAccountSummary({
      accountId: `acc_overflow_${index}`,
      email: `overflow-${index}@example.com`,
      displayName: `Overflow Account ${index}`,
      planType: "plus",
      status: "active",
    }),
  );

  await applyTheme(page, "light");
  await interceptApi(page, authSession, manyAccounts);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript((css: string) => {
    const style = document.createElement("style");
    style.textContent = css;
    (document.head ?? document.documentElement).appendChild(style);
  }, DISABLE_ANIMATIONS_CSS);
  await page.setViewportSize({ width: 1440, height: 1200 });
  await page.goto(`${BASE_URL}/accounts`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="account-list-scroll-region"]', { timeout: 10_000 });

  const scrollRegion = page.getByTestId("account-list-scroll-region");
  const listCard = page.getByTestId("accounts-list-card");
  const addAccountButton = page.getByRole("button", { name: "Add account" });
  const statusBar = page.locator("footer");

  await expect(addAccountButton).toBeVisible();
  const initialDimensions = await scrollRegion.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));
  expect(initialDimensions.clientHeight).toBeGreaterThan(512);
  expect(initialDimensions.scrollHeight).toBeGreaterThan(initialDimensions.clientHeight);
  const listCardBox = await listCard.boundingBox();
  const scrollRegionBox = await scrollRegion.boundingBox();
  const statusBarBox = await statusBar.boundingBox();
  if (!listCardBox || !scrollRegionBox || !statusBarBox) {
    throw new Error("Accounts list card, scroll region, or status bar is not measurable");
  }
  const bottomGap = listCardBox.y + listCardBox.height - (scrollRegionBox.y + scrollRegionBox.height);
  expect(bottomGap).toBeLessThanOrEqual(18);
  expect(scrollRegionBox.y + scrollRegionBox.height).toBeLessThanOrEqual(statusBarBox.y - 8);
  expect(await scrollRegion.evaluate((element) => element.scrollTop)).toBe(0);

  const reachedBottom = await scrollRegion.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
    const lastRow = element.lastElementChild;
    if (!lastRow) {
      return { scrollTop: element.scrollTop, lastRowVisible: false };
    }
    const rowRect = lastRow.getBoundingClientRect();
    const regionRect = element.getBoundingClientRect();
    return {
      scrollTop: element.scrollTop,
      lastRowVisible: rowRect.top >= regionRect.top && rowRect.bottom <= regionRect.bottom,
    };
  });
  expect(reachedBottom.scrollTop).toBeGreaterThan(0);
  expect(reachedBottom.lastRowVisible).toBe(true);
  await expect(addAccountButton).toBeVisible();

  await scrollRegion.evaluate((element) => {
    element.scrollTop = 0;
  });
  await page.getByRole("button", { name: "Need help?" }).click();
  await expect(page.getByText("Windows OAuth Help")).toBeVisible();

  const helpOpenDimensions = await scrollRegion.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));
  expect(helpOpenDimensions.clientHeight).toBeLessThan(initialDimensions.clientHeight);
  expect(helpOpenDimensions.scrollHeight).toBeGreaterThan(helpOpenDimensions.clientHeight);

  const helpOpenScrollRegionBox = await scrollRegion.boundingBox();
  const helpOpenStatusBarBox = await statusBar.boundingBox();
  if (!helpOpenScrollRegionBox || !helpOpenStatusBarBox) {
    throw new Error("Help-open account scroll region or status bar is not measurable");
  }
  expect(helpOpenScrollRegionBox.y + helpOpenScrollRegionBox.height).toBeLessThanOrEqual(
    helpOpenStatusBarBox.y - 8,
  );
  await expect(page.getByRole("button", { name: "Need help?" })).toBeVisible();
  await expect(addAccountButton).toBeVisible();

  const helpOpenReachedBottom = await scrollRegion.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
    const lastRow = element.lastElementChild;
    if (!lastRow) {
      return { scrollTop: element.scrollTop, lastRowVisible: false };
    }
    const rowRect = lastRow.getBoundingClientRect();
    const regionRect = element.getBoundingClientRect();
    return {
      scrollTop: element.scrollTop,
      lastRowVisible: rowRect.top >= regionRect.top && rowRect.bottom <= regionRect.bottom,
    };
  });
  expect(helpOpenReachedBottom.scrollTop).toBeGreaterThan(0);
  expect(helpOpenReachedBottom.lastRowVisible).toBe(true);
});

test("accounts list card ends after the final row when all accounts fit", async ({ page }) => {
  await applyTheme(page, "light");
  await interceptApi(page, authSession, accounts.slice(0, 4));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript((css: string) => {
    const style = document.createElement("style");
    style.textContent = css;
    (document.head ?? document.documentElement).appendChild(style);
  }, DISABLE_ANIMATIONS_CSS);
  await page.setViewportSize({ width: 1440, height: 1200 });
  await page.goto(`${BASE_URL}/accounts`, { waitUntil: "networkidle" });

  const scrollRegion = page.getByTestId("account-list-scroll-region");
  const listCard = page.getByTestId("accounts-list-card");
  const dimensions = await scrollRegion.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));
  expect(dimensions.scrollHeight).toBeLessThanOrEqual(dimensions.clientHeight);

  const listCardBox = await listCard.boundingBox();
  const scrollRegionBox = await scrollRegion.boundingBox();
  if (!listCardBox || !scrollRegionBox) {
    throw new Error("Accounts list card or scroll region is not measurable");
  }
  const bottomGap =
    listCardBox.y + listCardBox.height -
    (scrollRegionBox.y + scrollRegionBox.height);
  expect(bottomGap).toBeLessThanOrEqual(18);
  await expect(page.getByRole("button", { name: "Add account" })).toBeVisible();
});

test("settings — light", async ({ page }) => {
  await capture(page, { file: "settings.jpg", theme: "light", route: "/settings", fullPage: true });
});

for (const width of [1440, 390]) {
  test(`model source editor — ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await applyTheme(page, "light");
    await interceptApi(page);
    const source = createModelSource({ name: "Model gateway" });
    source.models[0] = { ...source.models[0], displayName: "Local Coder", inputPer1M: 0.5, cachedInputPer1M: 0.1, outputPer1M: 1.5 };
    source.models.push({ ...source.models[0], id: 2, model: "free-model", displayName: "Free Model", inputPer1M: 0, outputPer1M: 0 });
    await page.route("**/api/model-sources/", (route) => fulfill(route, { sources: [source] }));
    await page.goto(`${BASE_URL}/settings`);
    await page.getByRole("button", { name: "Show advanced settings" }).click();
    await page.getByRole("button", { name: "Edit Model gateway" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByRole("dialog").getByRole("button", { name: "Save", exact: true })).toBeVisible();
    const dialog = page.getByRole("dialog");
    const box = await dialog.boundingBox();
    expect(box!.width).toBeLessThanOrEqual(width);
    await page.screenshot({ animations: "disabled", path: path.join(SCREENSHOT_DIR, `model-source-editor-${width}.png`) });
    await page.getByTestId("model-source-edit-scroll-region").evaluate((element) => { element.scrollTop = element.scrollHeight; });
    await page.screenshot({ animations: "disabled", path: path.join(SCREENSHOT_DIR, `model-source-editor-${width}-bottom.png`) });
  });
}

test("provider request attribution", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await applyTheme(page, "light");
  await interceptApi(page);
  const request = { ...requestLogs[0], accountId: null, modelSourceId: "src-demo", modelSourceKind: "openrouter", modelSourceName: "OpenRouter personal", model: "openrouter/qwen/qwen3.8-27b:free", status: "error", errorCode: "429", errorMessage: "Provider returned error" };
  await page.route("**/api/request-logs?*", route => fulfill(route, createRequestLogsResponse([request], 1, false)));
  await page.route("**/api/request-logs/options*", route => fulfill(route, { ...filterOptions, accountIds: ["source:src-demo"], accountLabels: { "source:src-demo": "OpenRouter personal" } }));
  await page.goto(`${BASE_URL}/`);
  await expect(page.getByRole("cell", { name: "OpenRouter personal", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "View Details" }).click();
  await expect(page.getByRole("dialog").getByText("OpenRouter personal", { exact: true })).toBeVisible();
  await page.getByRole("dialog").screenshot({ animations: "disabled", path: test.info().outputPath("provider-request-details.png") });
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Accounts", exact: true }).click();
  await expect(page.getByRole("menuitemcheckbox", { name: "OpenRouter personal" })).toBeVisible();
  const filtered = page.waitForRequest(request => new URL(request.url()).pathname === "/api/request-logs" && new URL(request.url()).searchParams.get("accountId") === "source:src-demo");
  await page.getByRole("menuitemcheckbox", { name: "OpenRouter personal" }).click();
  await filtered;
});

for (const width of [1440, 390]) {
  test(`provider routing pools — ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await applyTheme(page, "light");
    await interceptApi(page);
    await page.route("**/api/settings", route => fulfill(route, {
      ...settings, routingStrategy: "single_account", singleAccountId: accounts[0].accountId,
      claudeSingleAccountId: "claude-routing",
    }));
    await page.route("**/api/claude-accounts", route => fulfill(route, { accounts: [{
      id: "claude-routing", name: "Claude research", isEnabled: true, credentialStatus: "ready",
      maxConcurrency: null, expiresAt: "2026-10-01T12:00:00Z",
      state: { all_models: false, selections: [], catalog: [], catalog_updated_at: null, catalog_error: null, usage_updated_at: null, usage_error: null },
      quota: { observedAt: null, windows: [], models: [] },
    }] }));
    await page.goto(`${BASE_URL}/settings`);
    await page.getByRole("button", { name: "Show advanced settings" }).click();
    const claude = page.getByRole("combobox", { name: "Selected Claude account" });
    await expect(claude).toHaveText("Claude research");
    await claude.scrollIntoViewIfNeeded();
    const openai = page.getByRole("combobox", { name: "Selected OpenAI account" });
    await expect(openai).toBeVisible();
    expect((await claude.boundingBox())!.width).toBeLessThan(width);
    await page.screenshot({ animations: "disabled", path: test.info().outputPath(`routing-pools-${width}.png`) });
  });
}

test("settings — dark", async ({ page }) => {
  await capture(page, { file: "settings-dark.jpg", theme: "dark", route: "/settings", fullPage: true });
});

for (const width of [1440, 390]) {
  test(`claude unified accounts — ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await applyTheme(page, "light");
    await interceptApi(page);
    const account = {
      id: "src_claude_demo", name: "Research Claude", isEnabled: true, maxConcurrency: null, routingPolicy: "normal", credentialStatus: "ready", expiresAt: "2026-09-26T12:00:00Z",
      state: { all_models: false, selections: [{ model: "claude-opus-5" }], catalog: [{ id: "claude-opus-5", display_name: "Claude Opus 5", max_input_tokens: 1000000, max_tokens: 128000 }], catalog_updated_at: "2026-09-25T12:00:00Z", catalog_error: null, usage_updated_at: null, usage_error: null },
      quota: { observedAt: null, models: [], windows: [
        { name: "five_hour", utilization: 32, resetsAt: "2026-09-25T17:00:00Z", freshness: "fresh", exhausted: false },
        { name: "seven_day", utilization: null, resetsAt: null, freshness: "unknown", exhausted: false },
      ] },
    };
    await page.route("**/api/claude-accounts", route => fulfill(route, { accounts: [account] }));
    await page.route("**/api/claude-accounts/version", route => fulfill(route, { effectiveVersion: "2.1.282", discoveredVersion: "2.1.282", pinnedVersion: null, lastCheckedAt: null, lastChangedAt: null, error: null }));
    await page.goto(`${BASE_URL}/accounts?selected=src_claude_demo`);
    await expect(page.getByRole("heading", { name: "Research Claude", exact: true })).toBeVisible();
    await expect(page.getByRole("spinbutton", { name: "Maximum concurrent requests" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Pause", exact: true })).toBeVisible();
    await page.screenshot({ animations: "disabled", fullPage: true, path: test.info().outputPath(`claude-accounts-${width}.png`) });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await page.getByRole("button", { name: "Reconnect", exact: true }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.screenshot({ animations: "disabled", path: test.info().outputPath(`claude-reconnect-${width}.png`) });
    await page.keyboard.press("Escape");
    await page.route("**/api/claude-accounts/src_claude_demo/reset-grants", route => fulfill(route, {
      status: { eligible: true, at_limit: true, ineligible_reason: null, cooldown_until: null, grants: [{
        id: "launch-grant", label: "Claude usage reset", resets_total: 1, resets_left: 1,
        starts_at: null, ends_at: "2026-10-22T16:00:00Z", clears: ["five_hour", "seven_day"],
        paused: false, usable_now: true, use_requires_limit: true,
      }] }, operations: [], error: null,
    }));
    await page.getByRole("button", { name: "Reset grants", exact: true }).click();
    await expect(page.getByRole("button", { name: "Redeem grant", exact: true })).toBeEnabled();
    await page.screenshot({ animations: "disabled", path: test.info().outputPath(`claude-reset-grants-${width}.png`) });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await page.getByRole("button", { name: "Redeem grant", exact: true }).click();
    await expect(page.getByRole("alertdialog")).toBeVisible();
    await page.screenshot({ animations: "disabled", path: test.info().outputPath(`claude-reset-confirm-${width}.png`) });
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await page.keyboard.press("Escape");
    await page.goto(`${BASE_URL}/`);
    await expect(page.getByTestId("claude-account-card")).toBeVisible();
    await page.getByTestId("claude-account-card").screenshot({ animations: "disabled", path: test.info().outputPath(`claude-dashboard-${width}.png`) });
  });
}

for (const width of [1440, 390]) {
  test(`openrouter accounts — ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await applyTheme(page, "light");
    await interceptApi(page);
    const account = {
      id: "src_openrouter_demo", name: "Research", isEnabled: true, hasManagementKey: true, routingPolicy: "normal",
      state: {
        all_models: false,
        catalog_updated_at: "2026-09-25T12:00:00Z", catalog_error: null,
        key_updated_at: "2026-09-25T12:00:00Z", key_error: null,
        credits_updated_at: "2026-09-25T12:00:00Z", credits_error: null,
        credits: {total_credits: 100, total_usage: 24.50},
        key: {limit: 50, limit_remaining: 42.25, limit_reset: "monthly", usage: 7.75, is_free_tier: false,
          usage_daily: 1.25, usage_weekly: 4.50, usage_monthly: 7.75,
          free_model_daily_requests: {used: 12, limit: 1000, remaining: 988}},
        selections: [{model: "vendor/coder", contextWindow: 262144, maxOutputTokens: null, displayName: null}],
        catalog: [{id: "vendor/coder", name: "Coder", context_length: 1000000, image: null,
          pricing: {prompt: 0.0000005, input_cache_read: 0.00000005, completion: 0.000002},
          supported_parameters: ["tools", "reasoning"],
          architecture: {input_modalities: ["text", "image"], output_modalities: ["text"]},
          top_provider: {context_length: 1000000, max_completion_tokens: 64000},
          reasoning: {mandatory: true, supported_efforts: ["low", "high", "max"], default_effort: "high"}}],
      },
    };
    await page.route("**/api/openrouter-accounts", route => fulfill(route, {accounts: [account]}));
    await page.goto(`${BASE_URL}/accounts?selected=src_openrouter_demo`);
    await expect(page.getByTestId("openrouter-account-detail")).toBeVisible();
    await page.getByTestId("account-list-scroll-region").getByRole("button", { name: /Research/ }).scrollIntoViewIfNeeded();
    await page.screenshot({animations: "disabled", path: path.join(SCREENSHOT_DIR, `openrouter-accounts-${width}.png`)});
    if (width < 640) {
      await page.getByTestId("openrouter-account-detail").scrollIntoViewIfNeeded();
      await page.screenshot({animations: "disabled", path: path.join(SCREENSHOT_DIR, `openrouter-account-detail-${width}.png`)});
    }
    await page.getByRole("button", {name: "Models (1)", exact: true}).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByLabel("Context cap for vendor/coder")).toHaveValue("262144");
    const box = await dialog.boundingBox();
    expect(box!.width).toBeLessThanOrEqual(width);
    await page.screenshot({animations: "disabled", path: path.join(SCREENSHOT_DIR, `openrouter-models-${width}.png`)});
    await page.keyboard.press("Escape");
    await page.goto(`${BASE_URL}/`);
    await expect(page.getByTestId("openrouter-account-card")).toBeVisible();
    await page.getByTestId("openrouter-account-card").scrollIntoViewIfNeeded();
    await page.screenshot({animations: "disabled", path: path.join(SCREENSHOT_DIR, `openrouter-dashboard-${width}.png`)});
    await page.getByRole("radio", {name: "View accounts as list"}).click();
    await expect(page.getByTestId("dashboard-account-list").getByText("Research", {exact: true})).toBeVisible();
    await page.getByTestId("account-list-row").filter({has: page.getByText("Research", {exact: true})}).scrollIntoViewIfNeeded();
    await page.screenshot({animations: "disabled", path: path.join(SCREENSHOT_DIR, `openrouter-dashboard-list-${width}.png`)});
  });
}

for (const width of [1440, 390]) {
  test(`openrouter image picker — ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await applyTheme(page, "light");
    await interceptApi(page);
    const account = createOpenRouterAccount();
    const id = "openai/gpt-image-2.5-sunburst";
    account.state.selections = [{model: id, contextWindow: 262144, maxOutputTokens: null, displayName: null}];
    account.state.catalog = [{
      id, name: "OpenAI: GPT Image 2.5 Sunburst", context_length: null,
      architecture: {input_modalities: ["text", "image"], output_modalities: ["image"]},
      pricing: {prompt: null, completion: null, input_cache_read: null}, supported_parameters: [],
      top_provider: {context_length: null, max_completion_tokens: null}, reasoning: null,
      image: {supports_streaming: true, endpoint_details: [{provider_name: "OpenAI", pricing: [
        {billable: "input_text", unit: "token", cost_usd: 0.000005, variant: null},
        {billable: "input_image", unit: "token", cost_usd: 0.000008, variant: null},
        {billable: "output_image", unit: "token", cost_usd: 0.00003, variant: null},
      ]}]},
    }];
    await page.route("**/api/openrouter-accounts", route => fulfill(route, {accounts: [account]}));
    await page.goto(`${BASE_URL}/accounts?selected=${account.id}`);
    await expect(page.getByRole("button", {name: "Models (0)", exact: true})).toBeVisible();
    await page.getByRole("button", {name: "Image models (1)", exact: true}).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText(/Public Images API only/)).toBeVisible();
    await expect(dialog.getByLabel(`Context cap for ${id}`)).toHaveCount(0);
    const box = await dialog.boundingBox();
    expect(box!.width).toBeLessThanOrEqual(width);
    await page.screenshot({animations: "disabled", path: test.info().outputPath("openrouter-images.png")});
    await dialog.getByRole("button", {name: "Capabilities", exact: true}).click();
    await page.getByRole("menuitemcheckbox", {name: "Image generation", exact: true}).click();
    await page.getByRole("menuitemcheckbox", {name: "Vision", exact: true}).click();
    await expect(page.getByRole("menuitemcheckbox", {name: "Vision", exact: true})).toBeChecked();
    await page.screenshot({animations: "disabled", path: test.info().outputPath("openrouter-capabilities.png")});
    await page.keyboard.press("Escape");
    await expect(dialog.getByText(/Public Images API only/)).toBeVisible();
  });
}

test("login", async ({ page }) => {
  await capture(page, {
    file: "login.jpg",
    theme: "light",
    route: "/",
    session: unauthenticatedSession,
    waitFor: 'input[type="password"]',
  });
});
