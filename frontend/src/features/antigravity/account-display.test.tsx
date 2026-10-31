import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { renderProvidersList } from "@/features/accounts/test-utils";
import { renderDashboardAccounts } from "@/features/dashboard/test-utils";
import { AntigravityAccountSchema } from "./api";
import { AntigravityQuota } from "./account-display";
import { AntigravityAccountControls } from "./account-controls";
import { antigravityStatus, bindingWindow } from "./display-values";
import { createAntigravityAccount, createAntigravityWindow } from "./test-fixtures";

const NOW = Date.parse("2026-10-29T12:00:00Z");

describe("antigravityStatus", () => {
  it("orders operator states before quota", () => {
    const account = createAntigravityAccount();
    expect(antigravityStatus(account, NOW)).toBe("active");
    expect(antigravityStatus({ ...account, isEnabled: false, hold: "banned" }, NOW)).toBe("paused");
    expect(antigravityStatus({ ...account, hold: "banned" }, NOW)).toBe("deactivated");
    expect(antigravityStatus({ ...account, credentialStatus: "reauth_required" }, NOW)).toBe("reauth_required");
  });

  it("stays active while any quota family can serve", () => {
    const account = createAntigravityAccount({
      windows: [
        createAntigravityWindow({ family: "gemini", window: "weekly", usedPercent: 100, exhausted: true }),
        createAntigravityWindow({ family: "claude", window: "weekly", usedPercent: 50 }),
      ],
    });
    expect(antigravityStatus(account, NOW)).toBe("active");
  });

  it("distinguishes drained weekly quota from short blocks", () => {
    const weekly = createAntigravityAccount({
      windows: [
        createAntigravityWindow({ family: "gemini", window: "weekly", usedPercent: 100, exhausted: true }),
        createAntigravityWindow({ family: "claude", window: "weekly", usedPercent: 100, exhausted: true }),
      ],
    });
    expect(antigravityStatus(weekly, NOW)).toBe("quota_exceeded");
    const short = createAntigravityAccount({
      windows: [
        createAntigravityWindow({ family: "gemini", window: "five_hour", usedPercent: 100, exhausted: true }),
        createAntigravityWindow({ family: "claude", window: "weekly", usedPercent: 100, exhausted: true }),
      ],
    });
    expect(antigravityStatus(short, NOW)).toBe("rate_limited");
  });

  it("honours active cooldowns only", () => {
    const account = createAntigravityAccount({
      windows: [createAntigravityWindow({ family: "gemini", window: "weekly", usedPercent: 20 })],
    });
    const cooled = (until: string, scope: string) => ({
      ...account,
      cooldowns: [{ scope, until, reason: "quota_exhausted" }],
    });
    expect(antigravityStatus(cooled("2026-10-29T13:00:00Z", "family:gemini"), NOW)).toBe("rate_limited");
    expect(antigravityStatus(cooled("2026-10-29T11:00:00Z", "family:gemini"), NOW)).toBe("active");
    expect(antigravityStatus(cooled("2026-10-29T13:00:00Z", "account"), NOW)).toBe("rate_limited");
  });
});

describe("Antigravity account display", () => {
  it("parses the dashboard response shape", () => {
    const parsed = AntigravityAccountSchema.parse({
      ...createAntigravityAccount(),
      state: {
        subscription: {
          current_tier: { id: "standard-tier", name: null },
          paid_tier: { id: "g1-pro-tier", name: "Pro" },
          credits: [],
          observed_at: "2026-10-29T10:00:00Z",
        },
        catalog: [
          {
            id: "gemini-3.5-pro",
            display_name: "Gemini 3.5 Pro",
            tiers: { low: "gemini-3.5-pro-low", high: "gemini-3.5-pro-high" },
            model_enums: {},
            api_provider: null,
            quota_family: "gemini",
            context_window: 1048576,
            max_output_tokens: 65536,
            supports_images: true,
            supports_thinking: true,
            model_quota: {},
          },
        ],
        default_model: "gemini-3.5-pro",
        all_models: false,
        selections: ["gemini-3.5-pro"],
        metadata: { quota: { updated_at: "2026-10-29T10:00:00Z", error: null, retry_at: null } },
        verification: null,
      },
    });
    expect(parsed.state.catalog[0]?.tiers).toEqual({ low: "gemini-3.5-pro-low", high: "gemini-3.5-pro-high" });
  });

  it("shows every window of every family in the account quota", () => {
    const account = createAntigravityAccount();
    expect(bindingWindow(account, "claude")?.window).toBe("five_hour");
    expect(bindingWindow(account, "gemini")?.window).toBe("weekly");
    const view = render(<AntigravityQuota account={account} />);
    for (const label of ["Gemini 5h", "Gemini Weekly", "Claude & GPT 5h", "Claude & GPT Weekly"])
      expect(view.container).toHaveTextContent(label);
  });

  it("renders a dashboard card with provider and plan", () => {
    renderDashboardAccounts({ antigravityAccounts: [createAntigravityAccount({ planType: "ultra_5x" })] });
    const card = screen.getByTestId("dashboard-account-card");
    expect(card).toHaveTextContent("Antigravity");
    expect(card.querySelector(".plan-badge")).toHaveTextContent("Ultra 5×");
  });

  it("lists accounts on the Providers page and dashboard", () => {
    const account = createAntigravityAccount({ name: "Google One" });
    const view = renderProvidersList({ antigravityAccounts: [account] });
    const listRow = screen.getByTestId("provider-account-row");
    expect(within(listRow).getByRole("link", { name: "Google One" })).toHaveAttribute("href", "/providers/" + account.id);
    expect(listRow).toHaveTextContent("Claude & GPT · 5h");
    expect(listRow).toHaveTextContent("Gemini · Weekly");
    view.unmount();
    renderDashboardAccounts({ antigravityAccounts: [account] }, { view: "list" });
    const row = screen.getByTestId("dashboard-account-row");
    expect(within(row).getByRole("link", { name: "Google One" })).toHaveAttribute("href", "/providers/" + account.id);
    expect(row).toHaveTextContent("Gemini");
    expect(row).toHaveTextContent("Claude");
    expect(row).toHaveTextContent("Pro");
  });

  it("explains a hold and offers to clear it", () => {
    const account = createAntigravityAccount({ hold: "banned", holdReason: "Account disabled by Google" });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <AntigravityAccountControls account={account} readOnly={false} onCreated={vi.fn()}>
            {({ detail }) => detail}
          </AntigravityAccountControls>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByText("Google suspended this account")).toBeVisible();
    expect(screen.getByText("Account disabled by Google")).toBeVisible();
    expect(screen.getByRole("button", { name: /Clear hold/ })).toBeEnabled();
  });
});
