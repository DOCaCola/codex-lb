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

test("settings — dark", async ({ page }) => {
  await capture(page, { file: "settings-dark.jpg", theme: "dark", route: "/settings", fullPage: true });
});

for (const width of [1440, 390]) {
  test(`claude unified accounts — ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await applyTheme(page, "light");
    await interceptApi(page);
    const account = {
      id: "src_claude_demo", name: "Research Claude", isEnabled: true, credentialStatus: "ready", expiresAt: "2026-09-26T12:00:00Z",
      state: { selections: [{ model: "claude-opus-5", contextWindow: 200000, maxOutputTokens: 8192 }], catalog: [{ id: "claude-opus-5", display_name: "Claude Opus 5" }], catalog_updated_at: "2026-09-25T12:00:00Z", catalog_error: null, usage_updated_at: null, usage_error: null },
      quota: { observedAt: null, models: [], windows: [
        { name: "five_hour", utilization: 32, resetsAt: "2026-09-25T17:00:00Z", freshness: "fresh", exhausted: false },
        { name: "seven_day", utilization: null, resetsAt: null, freshness: "unknown", exhausted: false },
      ] },
    };
    await page.route("**/api/claude-accounts", route => fulfill(route, { accounts: [account] }));
    await page.route("**/api/claude-accounts/version", route => fulfill(route, { effectiveVersion: "2.1.282", discoveredVersion: "2.1.282", pinnedVersion: null, lastCheckedAt: null, lastChangedAt: null, error: null }));
    await page.goto(`${BASE_URL}/accounts?selected=src_claude_demo`);
    await expect(page.getByRole("heading", { name: "Research Claude", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Pause", exact: true })).toBeVisible();
    await page.screenshot({ animations: "disabled", fullPage: true, path: test.info().outputPath(`claude-accounts-${width}.png`) });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await page.getByRole("button", { name: "Reconnect", exact: true }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.screenshot({ animations: "disabled", path: test.info().outputPath(`claude-reconnect-${width}.png`) });
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
      id: "src_openrouter_demo", name: "Research", isEnabled: true, hasManagementKey: true,
      state: {
        catalog_updated_at: "2026-09-25T12:00:00Z", catalog_error: null,
        key_updated_at: "2026-09-25T12:00:00Z", key_error: null,
        credits_updated_at: "2026-09-25T12:00:00Z", credits_error: null,
        credits: {total_credits: 100, total_usage: 24.50},
        key: {limit: 50, limit_remaining: 42.25, limit_reset: "monthly", usage: 7.75,
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
    await page.getByRole("button", {name: "Models (1)", exact: true}).click();
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
