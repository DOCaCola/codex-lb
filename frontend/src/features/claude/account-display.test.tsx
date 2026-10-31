import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AccountCards } from "@/features/dashboard/components/account-cards";
import { AccountList as DashboardList } from "@/features/dashboard/components/account-list";
import { renderProvidersList } from "@/features/accounts/test-utils";
import { usePrivacyStore } from "@/hooks/use-privacy";
import {
  ClaudeAccountCard,
  ClaudeQuota,
} from "./account-display";
import { claudeStatus } from "./display-values";
import type { ClaudeAccount } from "./api";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { ClaudeAccountControls } from "./account-controls";
import { ModelSelection } from "./model-selection";
import { useAccountQuotaDisplayStore } from "@/hooks/use-account-quota-display";
import { createAccountSummary } from "@/test/mocks/factories";
import { createOpenRouterAccount } from "@/features/openrouter/test-fixtures";

const account: ClaudeAccount = {
  planType: "pro",
  quotaWeights: { fiveHour: 1, weekly: 1 },
  maxConcurrency: null,
  routingPolicy: "normal",
  id: "claude-test",
  name: "Private Claude",
  accountEmail: "doca@example.com",
  organizationName: "DOCa Org",
  isEnabled: true,
  credentialStatus: "ready",
  expiresAt: "2026-09-25T20:00:00Z",
  extraUsageEnabled: false,
  state: {
    subscription: null,
    subscription_updated_at: null,
    subscription_error: null,
    all_models: false,
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
        utilization: 40,
        resetsAt: null,
        freshness: "stale",
        exhausted: false,
      },
    ],
  },
};
afterEach(() => {
  usePrivacyStore.setState({ blurred: false });
  useAccountQuotaDisplayStore.setState({ quotaDisplay: "both" });
});
describe("Claude shared account surfaces", () => {
  it.each([false, true])("warns about billed extra usage only when the account enables it (%s)", (extraUsageEnabled) => {
    const selected = { ...account, extraUsageEnabled };
    render(<MemoryRouter><ClaudeAccountCard account={selected} /></MemoryRouter>);
    renderProvidersList({ claudeAccounts: [selected] });
    const badges = screen.queryAllByText("Extra usage");
    expect(badges).toHaveLength(extraUsageEnabled ? 2 : 0);
    for (const badge of badges) expect(badge.closest("[title]")).toHaveAttribute("title", expect.stringContaining("billed"));
  });

  it.each([
    ["free", "Free"], ["pro", "Pro"], ["max", "Max"],
    ["ultra", "Ultra"],
    ["team", "Team"], ["enterprise", "Enterprise"], ["unknown", "Unknown plan"],
  ] as const)("shows %s in cards, the Providers table and dashboard plan cells", (planType, label) => {
    const selected = { ...account, planType };
    const view = render(<MemoryRouter><ClaudeAccountCard account={selected} /></MemoryRouter>);
    expect(screen.getByText(label, { exact: true })).toBeVisible();
    view.unmount();
    const list = renderProvidersList({ claudeAccounts: [selected] });
    expect(screen.getByText(label, { exact: true })).toBeVisible();
    list.unmount();
    render(<MemoryRouter><DashboardList accounts={[]} claudeAccounts={[selected]} /></MemoryRouter>);
    expect(screen.getByText(label, { exact: true })).toBeVisible();
  });

  it("searches Claude accounts by the displayed subscription label", async () => {
    renderProvidersList({ claudeAccounts: [
      { ...account, planType: "ultra" },
      { ...account, id: "other", name: "Other Claude", planType: "pro" },
    ] });
    await userEvent.type(screen.getByPlaceholderText("Search accounts..."), "Ultra");
    expect(screen.getByText(account.name)).toBeVisible();
    expect(screen.queryByText("Other Claude")).not.toBeInTheDocument();
  });

  it("sorts dashboard Claude rows by detected plan instead of provider name", () => {
    render(<MemoryRouter><DashboardList accounts={[]} claudeAccounts={[
      { ...account, id: "aaa", name: "A account", planType: "pro" },
      { ...account, id: "zzz", name: "Z account", planType: "free" },
    ]} /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: /^Plan/ }));
    let rows = screen.getAllByTestId("account-list-row");
    expect(within(rows[0]).getByText("Free")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /^Plan/ }));
    rows = screen.getAllByTestId("account-list-row");
    expect(within(rows[0]).getByText("Pro")).toBeVisible();
  });

  it("shows retained plan diagnostics in account details without offering a plan editor", () => {
    const failed = { ...account, planType: "max" as const,
      state: { ...account.state, subscription_error: "Claude /api/claude_cli/bootstrap returned HTTP 429" },
    };
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MemoryRouter>
      <ClaudeAccountControls account={failed} readOnly onCreated={vi.fn()}>{({ detail }) => detail}</ClaudeAccountControls>
    </MemoryRouter></QueryClientProvider>);
    expect(screen.getByText("Max", { exact: true })).toHaveAttribute("title", "Last known subscription; metadata refresh failed");
    expect(screen.getByRole("heading", { level: 2, name: "Usage" })).toBeInTheDocument();
    expect(screen.queryByText(/Claude OAuth/)).not.toBeInTheDocument();
    expect(screen.getByText(failed.state.subscription_error)).toHaveAttribute("role", "alert");
    expect(screen.queryByRole("combobox", { name: /subscription|plan/i })).not.toBeInTheDocument();
  });

  it("uses two card quota columns and responsive detail columns", () => {
    const view = render(<ClaudeQuota account={account} />);
    expect(view.container.firstElementChild).toHaveClass("grid-cols-2");
    expect(view.container.firstElementChild).not.toHaveClass("sm:grid-cols-2");
    view.rerender(<ClaudeQuota account={{ ...account, quota: { ...account.quota, windows: [account.quota.windows[1]] } }} />);
    expect(view.container.firstElementChild).toHaveClass("grid-cols-1");
    view.rerender(<ClaudeQuota account={account} detailed />);
    expect(view.container.firstElementChild).toHaveClass("grid-cols-1", "sm:grid-cols-2");
  });

  it("keeps model selection details out of dashboard card subtitles", () => {
    const automatic = {
      ...account,
      state: { ...account.state, all_models: true },
    };
    const view = render(
      <MemoryRouter>
        <ClaudeAccountCard account={automatic} />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("claude-account-card")).toHaveTextContent("Claude · Pro");
    expect(screen.queryByText(/All models/)).not.toBeInTheDocument();
    view.unmount();
    renderProvidersList({ claudeAccounts: [automatic] });
    expect(within(screen.getByTestId("provider-account-row")).getByText("All models")).toBeInTheDocument();
  });
  it("renders only returned quota windows, including genuine unknown or stale scoped observations", () => {
    const { rerender } = render(<ClaudeQuota account={account} detailed />);
    expect(screen.queryByText("Weekly Opus remaining")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Weekly Sonnet remaining"),
    ).not.toBeInTheDocument();
    rerender(
      <ClaudeQuota
        account={{
          ...account,
          quota: {
            ...account.quota,
            windows: [
              ...account.quota.windows,
              {
                name: "seven_day_opus",
                utilization: null,
                resetsAt: null,
                freshness: "unknown",
                exhausted: false,
              },
              {
                name: "seven_day_sonnet",
                utilization: 50,
                resetsAt: null,
                freshness: "stale",
                exhausted: false,
              },
            ],
          },
        }}
        detailed
      />,
    );
    expect(screen.getByText("Weekly Opus remaining")).toBeInTheDocument();
    expect(screen.getByText("Weekly Sonnet remaining")).toBeInTheDocument();
  });
  it("preserves usage overshoot while bounding the remaining bar", () => {
    const overshot: ClaudeAccount = {
      ...account,
      quota: {
        ...account.quota,
        windows: [{ ...account.quota.windows[0], utilization: 104, freshness: "fresh", exhausted: true }],
      },
    };
    const card = render(<ClaudeQuota account={overshot} />);
    expect(screen.getByText("104% used")).toBeInTheDocument();
    expect(card.container.querySelector("[style]")).toHaveStyle({ width: "0%" });
    card.unmount();
    renderProvidersList({ claudeAccounts: [overshot] });
    expect(within(screen.getByTestId("provider-account-row")).getByText("0%")).toBeInTheDocument();
  });
  it("requires explicit refresh ownership consent before enrollment", async () => {
    const client = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={client}><MemoryRouter>
        <ClaudeAccountControls
          account={null}
          readOnly={false}
          onCreated={vi.fn()}
        >
          {({ onSignIn }) => <button onClick={onSignIn}>Add Claude</button>}
        </ClaudeAccountControls>
      </MemoryRouter></QueryClientProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Add Claude" }));
    await userEvent.type(await screen.findByLabelText("Account name"), "Research");
    expect(
      screen.getByRole("button", { name: "Start sign-in" }),
    ).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox"));
    expect(
      screen.getByRole("button", { name: "Start sign-in" }),
    ).toBeEnabled();
  });
  describe("re-authentication", () => {
    const held = {
      error: {
        code: "claude_reconnect_organization_changed",
        message: "Confirm to replace the saved organization.",
        details: {
          pendingId: "pending-1",
          expiresAt: "2030-01-01T00:10:00Z",
          saved: { email: "doca@example.com", organization: "DOCa Org", plan: "max" },
          incoming: { email: "doca@example.com", organization: "DOCa Org (new)", plan: "pro" },
        },
      },
    };
    function renderDetail() {
      const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
      render(<QueryClientProvider client={client}><MemoryRouter>
        <ClaudeAccountControls account={account} readOnly={false} onCreated={vi.fn()}>
          {({ detail }) => detail}
        </ClaudeAccountControls>
      </MemoryRouter></QueryClientProvider>);
    }
    async function signInAgain() {
      await userEvent.click(screen.getByRole("button", { name: "Re-authenticate" }));
      await userEvent.click(await screen.findByRole("menuitem", { name: "Sign in again" }));
      const dialog = await screen.findByRole("dialog", { name: /Re-authenticate Private Claude/ });
      expect(within(dialog).getByText("doca@example.com")).toBeVisible();
      expect(within(dialog).queryByRole("checkbox", { name: /Replace the saved identity/ })).not.toBeInTheDocument();
      await userEvent.click(within(dialog).getByRole("checkbox", { name: /I will not use this refresh grant/ }));
      await userEvent.click(within(dialog).getByRole("button", { name: "Start sign-in" }));
      await userEvent.type(await screen.findByRole("textbox", { name: "Authorization code" }), "new-code");
      await userEvent.click(screen.getByRole("button", { name: "Submit" }));
    }

    it("completes a matching sign-in without a confirmation", async () => {
      const completions: unknown[] = [];
      server.use(
        http.post("/api/claude-accounts/oauth/start", () => HttpResponse.json({
          state: "test-state", authorizationUrl: "https://claude.ai/authorize", expiresAt: "2030-01-01T00:00:00Z",
        })),
        http.post("/api/claude-accounts/oauth/complete", async ({ request }) => {
          completions.push(await request.json());
          return HttpResponse.json(account);
        }),
      );
      renderDetail();
      await signInAgain();
      expect(await screen.findByText("Private Claude is connected.")).toBeVisible();
      expect(completions).toEqual([{ state: "test-state", code: "new-code" }]);
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    });

    it.each([true, false])("asks before replacing a differing identity (confirm: %s)", async (confirm) => {
      const calls: string[] = [];
      server.use(
        http.post("/api/claude-accounts/oauth/start", () => HttpResponse.json({
          state: "test-state", authorizationUrl: "https://claude.ai/authorize", expiresAt: "2030-01-01T00:00:00Z",
        })),
        http.post("/api/claude-accounts/oauth/complete", () => HttpResponse.json(held, { status: 409 })),
        http.post("/api/claude-accounts/claude-test/pending-reconnects/pending-1/confirm", () => {
          calls.push("confirm");
          return HttpResponse.json(account);
        }),
        http.delete("/api/claude-accounts/claude-test/pending-reconnects/pending-1", () => {
          calls.push("discard");
          return new HttpResponse(null, { status: 204 });
        }),
      );
      renderDetail();
      await signInAgain();
      const confirmation = await screen.findByRole("alertdialog", { name: /This sign-in differs from Private Claude/ });
      expect(within(confirmation).getByText("DOCa Org (new)").closest("td")).toHaveAttribute("data-differs");
      expect(within(confirmation).getAllByText("doca@example.com")[1]!.closest("td")).not.toHaveAttribute("data-differs");
      expect(within(confirmation).getByText("Pro").closest("td")).toHaveAttribute("data-differs");
      await userEvent.click(within(confirmation).getByRole("button", { name: confirm ? "Replace saved identity" : "Cancel" }));
      if (confirm) {
        expect(await screen.findByText("Private Claude is connected.")).toBeVisible();
        expect(calls).toEqual(["confirm"]);
      } else {
        expect(await screen.findByText(/The new sign-in was discarded/)).toBeVisible();
        expect(calls).toEqual(["discard"]);
      }
    });
  });
  it("pauses through the account API and blocks mutations for read-only users", async () => {
    const changes: unknown[] = [];
    server.use(
      http.get("/api/claude-accounts/version", () =>
        HttpResponse.json({
          effectiveVersion: "2.1.282",
          discoveredVersion: "2.1.282",
          pinnedVersion: null,
          lastCheckedAt: null,
          lastChangedAt: null,
          error: null,
        }),
      ),
      http.patch("/api/claude-accounts/claude-test", async ({ request }) => {
        changes.push(await request.json());
        return HttpResponse.json({ ...account, isEnabled: false });
      }),
    );
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const view = render(
      <QueryClientProvider client={client}><MemoryRouter>
        <ClaudeAccountControls
          account={account}
          readOnly={false}
          onCreated={vi.fn()}
        >
          {({ detail }) => detail}
        </ClaudeAccountControls>
      </MemoryRouter></QueryClientProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Pause" }));
    expect(changes).toEqual([{ isEnabled: false }]);
    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    await userEvent.click(
      screen.getByRole("combobox", { name: "Routing policy" }),
    );
    await userEvent.click(screen.getByRole("option", { name: "Burn first" }));
    expect(changes).toEqual([
      { isEnabled: false },
      { routingPolicy: "burn_first" },
    ]);
    view.rerender(
      <QueryClientProvider client={client}><MemoryRouter>
        <ClaudeAccountControls account={account} readOnly onCreated={vi.fn()}>
          {({ detail }) => detail}
        </ClaudeAccountControls>
      </MemoryRouter></QueryClientProvider>,
    );
    expect(
      screen.getByRole("combobox", { name: "Routing policy" }),
    ).toBeDisabled();
    for (const name of [
      "Pause",
      "Check limits",
      "Models (0)",
    ])
      expect(screen.getByRole("button", { name })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Overview" }));
    expect(screen.getByRole("button", { name: "Re-authenticate" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "More actions" }));
    expect(await screen.findByRole("menuitem", { name: "Delete account" })).toHaveAttribute("aria-disabled", "true");
  });
  it("renames the account inline through the account API", async () => {
    const changes: unknown[] = [];
    server.use(
      http.patch("/api/claude-accounts/claude-test", async ({ request }) => {
        const body = await request.json();
        changes.push(body);
        return HttpResponse.json({ ...account, name: "Team Claude" });
      }),
    );
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}><MemoryRouter>
        <ClaudeAccountControls
          account={account}
          readOnly={false}
          onCreated={vi.fn()}
        >
          {({ detail }) => detail}
        </ClaudeAccountControls>
      </MemoryRouter></QueryClientProvider>,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Rename account" }),
    );
    const input = screen.getByRole("textbox", { name: "Account name" });
    await userEvent.clear(input);
    await userEvent.type(input, "Team Claude");
    await userEvent.click(screen.getByRole("button", { name: "Save name" }));
    expect(changes).toEqual([{ name: "Team Claude" }]);
  });
  it("uses the Codex list quota preference in the Providers table", () => {
    renderProvidersList({ claudeAccounts: [account] }, {}, { quotaDisplay: "weekly" });
    const row = screen.getByTestId("provider-account-row");
    expect(within(row).queryByText("5h")).not.toBeInTheDocument();
    expect(within(row).getByText("Weekly")).toBeInTheDocument();
    expect(within(row).getByText("60%")).toBeInTheDocument();
  });
  it("shows automatic model limits and saves identifiers only", async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const discovered: ClaudeAccount = {
      ...account,
      state: {
        ...account.state,
        catalog: [
          {
            id: "claude-opus-5",
            display_name: "Opus",
            max_input_tokens: 1000000,
            max_tokens: 128000,
            reasoning_levels: ["low", "medium", "high", "max"],
            default_reasoning_level: "high",
          },
          {
            id: "unknown",
            display_name: "Unknown model",
            max_input_tokens: null,
            max_tokens: null,
            reasoning_levels: [],
            default_reasoning_level: null,
          },
        ],
      },
    };
    const view = render(
      <ModelSelection
        account={discovered}
        readOnly={false}
        onSave={save}
        onClose={vi.fn()}
      />,
    );
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
    // Context windows live in Settings → Model catalogue, not on the account.
    expect(screen.queryByText(/maximum output/i)).not.toBeInTheDocument();
    expect(
      screen.getByText(/Token limits unavailable/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("checkbox", { name: "Unknown model — Unavailable" }),
    ).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox", { name: "Opus" }));
    await userEvent.click(screen.getByRole("button", { name: "Save 1 model" }));
    expect(save).toHaveBeenCalledWith({
      selections: [{ model: "claude-opus-5" }],
      allModels: false,
      reasoningRestrictions: {},
    });
    view.rerender(
      <ModelSelection
        account={discovered}
        readOnly
        onSave={save}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByRole("checkbox", { name: "Opus" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save 1 model" })).toBeDisabled();
  });
  it("can remove a selected model with unavailable limits", async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    render(
      <ModelSelection
        account={{
          ...account,
          state: { ...account.state, selections: [{ model: "removed" }] },
        }}
        readOnly={false}
        onSave={save}
        onClose={vi.fn()}
      />,
    );
    const checkbox = screen.getByRole("checkbox", {
      name: "removed — Unavailable",
    });
    expect(checkbox).toBeEnabled();
    await userEvent.click(checkbox);
    await userEvent.click(
      screen.getByRole("button", { name: "Save 0 models" }),
    );
    expect(save).toHaveBeenCalledWith({
      selections: [],
      allModels: false,
      reasoningRestrictions: {},
    });
  });
  it("distinguishes unknown and stale observations", () => {
    const card = render(<ClaudeQuota account={account} />);
    expect(screen.getByText("Unknown")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
    expect(screen.getByText("· stale")).toBeInTheDocument();
    card.unmount();
    renderProvidersList({ claudeAccounts: [account] });
    const row = screen.getByTestId("provider-account-row");
    expect(within(row).getByText("--")).toBeInTheDocument();
    expect(within(row).getByText("stale")).toBeInTheDocument();
  });
  it("orders dashboard cards Codex, Claude, then OpenRouter", () => {
    render(
      <MemoryRouter>
        <AccountCards
          accounts={[createAccountSummary()]}
          claudeAccounts={[account]}
          openRouterAccounts={[createOpenRouterAccount()]}
        />
      </MemoryRouter>,
    );
    const cards = screen.getByTestId("dashboard-account-cards").children;
    expect(
      Array.from(cards, (card) => card.firstElementChild?.getAttribute("data-testid")),
    ).toEqual(["codex-account-card", "claude-account-card", "openrouter-account-card"]);
  });

  it.each([AccountCards, DashboardList])(
    "includes provider-only accounts in dashboard layouts",
    (Component) => {
      render(
        <MemoryRouter>
          <Component accounts={[]} claudeAccounts={[account]} />
        </MemoryRouter>,
      );
      expect(screen.getByText(account.name)).toBeInTheDocument();
      if (Component === DashboardList)
        expect(screen.getAllByTestId("account-list-quota-meter")).toHaveLength(
          2,
        );
      expect(screen.getByRole("link", { name: "Details" })).toHaveAttribute(
        "href",
        "/providers/claude-test",
      );
    },
  );
  it("keeps the routing policy off the dashboard card but in the Providers table", () => {
    const { unmount } = render(
      <MemoryRouter>
        <AccountCards accounts={[]} claudeAccounts={[account]} />
      </MemoryRouter>,
    );
    expect(screen.queryByText("Normal")).not.toBeInTheDocument();
    unmount();
    renderProvidersList({ claudeAccounts: [account] });
    expect(screen.getByText("Normal")).toBeInTheDocument();
  });
  it("uses shared privacy and read-only controls", () => {
    usePrivacyStore.setState({ blurred: true });
    renderProvidersList({ claudeAccounts: [account] }, { readOnly: true });
    expect(screen.getByText(account.name)).toHaveClass("privacy-blur");
    expect(screen.getByText(account.accountEmail!)).toHaveClass("privacy-blur");
    expect(screen.queryByRole("button", { name: "Add Claude account" })).not.toBeInTheDocument();
  });
  it("does not label exhausted or uncertain credentials active", () => {
    expect(claudeStatus({ ...account, credentialStatus: "uncertain" })).toBe(
      "reauth_required",
    );
    expect(claudeStatus({ ...account, isEnabled: false })).toBe("paused");
    const blocked = (drained: string) => ({
      ...account,
      quota: {
        ...account.quota,
        models: [{ model: "test", blocked: true, retryAt: null }],
        windows: account.quota.windows.map((window) => ({
          ...window,
          exhausted: window.name === drained,
        })),
      },
    });
    // Same distinction as Codex: 5-hour drain is rate limited, weekly is exceeded.
    expect(claudeStatus(blocked("five_hour"))).toBe("rate_limited");
    expect(claudeStatus(blocked("seven_day"))).toBe("quota_exceeded");
    expect(claudeStatus(blocked("none"))).toBe("rate_limited");
  });
});
