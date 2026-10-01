import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AccountCards } from "@/features/dashboard/components/account-cards";
import { AccountList as DashboardList } from "@/features/dashboard/components/account-list";
import { AccountList } from "@/features/accounts/components/account-list";
import { usePrivacyStore } from "@/hooks/use-privacy";
import {
  ClaudeAccountCard,
  ClaudeListItem,
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
  maxConcurrency: null,
  routingPolicy: "normal",
  id: "claude-test",
  name: "Private Claude",
  isEnabled: true,
  credentialStatus: "ready",
  expiresAt: "2026-09-25T20:00:00Z",
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
  it.each([
    ["free", "Free"], ["pro", "Pro"], ["max", "Max"],
    ["max_5x", "Max 5×"], ["max_20x", "Max 20×"],
    ["team", "Team"], ["enterprise", "Enterprise"], ["unknown", "Unknown plan"],
  ] as const)("shows %s in cards, account lists and dashboard plan cells", (planType, label) => {
    const selected = { ...account, planType };
    const view = render(<MemoryRouter><ClaudeAccountCard account={selected} /></MemoryRouter>);
    expect(screen.getByText(label, { exact: true })).toBeVisible();
    view.rerender(<ClaudeListItem account={selected} selected onSelect={vi.fn()} />);
    expect(screen.getByText(label, { exact: true })).toBeVisible();
    view.rerender(<MemoryRouter><DashboardList accounts={[]} claudeAccounts={[selected]} /></MemoryRouter>);
    expect(screen.getByText(label, { exact: true })).toBeVisible();
  });

  it("searches Claude accounts by the displayed subscription label", async () => {
    render(<AccountList accounts={[]} claudeAccounts={[
      { ...account, planType: "max_20x" },
      { ...account, id: "other", name: "Other Claude", planType: "pro" },
    ]} selectedAccountId={account.id} onSelect={vi.fn()} onOpenImport={vi.fn()} onOpenOauth={vi.fn()} />);
    await userEvent.type(screen.getByPlaceholderText("Search accounts..."), "Max 20×");
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
    const failed = { ...account, planType: "max_5x" as const,
      state: { ...account.state, subscription_error: "Claude /api/claude_cli/bootstrap returned HTTP 429" },
    };
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}>
      <ClaudeAccountControls account={failed} readOnly onCreated={vi.fn()}>{({ detail }) => detail}</ClaudeAccountControls>
    </QueryClientProvider>);
    expect(screen.getByText("Max 5×")).toHaveAttribute("title", "Last known subscription; metadata refresh failed");
    expect(screen.getByText("Max 5×").parentElement).toHaveTextContent("Claude | Max 5×");
    expect(screen.queryByText(/Claude OAuth/)).not.toBeInTheDocument();
    expect(screen.getByText(failed.state.subscription_error)).toHaveAttribute("role", "alert");
    expect(screen.queryByRole("combobox", { name: /subscription|plan/i })).not.toBeInTheDocument();
  });

  it("uses two card quota columns without changing the list and detail layout", () => {
    const view = render(<ClaudeQuota account={account} variant="card" />);
    expect(view.container.firstElementChild).toHaveClass("grid-cols-2");
    expect(view.container.firstElementChild).not.toHaveClass("sm:grid-cols-2");
    view.rerender(<ClaudeQuota account={{ ...account, quota: { ...account.quota, windows: [account.quota.windows[1]] } }} variant="card" />);
    expect(view.container.firstElementChild).toHaveClass("grid-cols-1");
    view.rerender(<ClaudeQuota account={account} />);
    expect(view.container.firstElementChild).toHaveClass("grid-cols-1", "sm:grid-cols-2");
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
    view.rerender(
      <MemoryRouter>
        <ClaudeListItem account={automatic} selected onSelect={vi.fn()} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Claude.*All models/)).toBeVisible();
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
    render(
      <ClaudeQuota
        account={{
          ...account,
          quota: {
            ...account.quota,
            windows: [
              {
                ...account.quota.windows[0],
                utilization: 104,
                freshness: "fresh",
                exhausted: true,
              },
            ],
          },
        }}
      />,
    );
    expect(screen.getByText("104% used")).toBeInTheDocument();
    expect(screen.getByTestId("mini-quota-track-5h")).toHaveAttribute(
      "value",
      "0",
    );
    expect(screen.getByTestId("mini-quota-track-5h-fill")).toHaveStyle({
      width: "0%",
    });
  });
  it("requires explicit refresh ownership consent before enrollment", async () => {
    const client = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={client}>
        <ClaudeAccountControls
          account={null}
          readOnly={false}
          onCreated={vi.fn()}
        >
          {({ onAdd }) => <button onClick={onAdd}>Add Claude</button>}
        </ClaudeAccountControls>
      </QueryClientProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Add Claude" }));
    await userEvent.type(screen.getByLabelText("Account name"), "Research");
    expect(
      screen.getByRole("button", { name: "Sign in with Claude" }),
    ).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox"));
    expect(
      screen.getByRole("button", { name: "Sign in with Claude" }),
    ).toBeEnabled();
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
      <QueryClientProvider client={client}>
        <ClaudeAccountControls
          account={account}
          readOnly={false}
          onCreated={vi.fn()}
        >
          {({ detail }) => detail}
        </ClaudeAccountControls>
      </QueryClientProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Pause" }));
    expect(changes).toEqual([{ isEnabled: false }]);
    await userEvent.click(
      screen.getByRole("combobox", { name: "Routing policy" }),
    );
    await userEvent.click(screen.getByRole("option", { name: "Burn first" }));
    expect(changes).toEqual([
      { isEnabled: false },
      { routingPolicy: "burn_first" },
    ]);
    view.rerender(
      <QueryClientProvider client={client}>
        <ClaudeAccountControls account={account} readOnly onCreated={vi.fn()}>
          {({ detail }) => detail}
        </ClaudeAccountControls>
      </QueryClientProvider>,
    );
    expect(
      screen.getByRole("combobox", { name: "Routing policy" }),
    ).toBeDisabled();
    for (const name of [
      "Pause",
      "Reconnect",
      "Refresh",
      "Models (0)",
      "Delete Claude account",
    ])
      expect(screen.getByRole("button", { name })).toBeDisabled();
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
      <QueryClientProvider client={client}>
        <ClaudeAccountControls
          account={account}
          readOnly={false}
          onCreated={vi.fn()}
        >
          {({ detail }) => detail}
        </ClaudeAccountControls>
      </QueryClientProvider>,
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
  it("uses the Codex list quota preference", () => {
    useAccountQuotaDisplayStore.setState({ quotaDisplay: "weekly" });
    render(<ClaudeQuota account={account} />);
    expect(screen.queryByText("5h")).not.toBeInTheDocument();
    expect(screen.getByText("Weekly")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
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
    expect(
      screen.getByText(/1M context.*128K maximum output.*64K default output/i),
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
    render(<ClaudeQuota account={account} />);
    expect(screen.getByText("Unknown")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
    expect(screen.getByText("· stale")).toBeInTheDocument();
    expect(screen.getByTestId("mini-quota-track-5h")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
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
        "/accounts?selected=claude-test",
      );
    },
  );
  it("keeps the routing policy off the dashboard card but in the Accounts list", () => {
    const { unmount } = render(
      <MemoryRouter>
        <AccountCards accounts={[]} claudeAccounts={[account]} />
      </MemoryRouter>,
    );
    expect(screen.queryByText("Normal")).not.toBeInTheDocument();
    unmount();
    render(
      <AccountList
        accounts={[]}
        claudeAccounts={[account]}
        selectedAccountId={account.id}
        onSelect={vi.fn()}
        onOpenImport={vi.fn()}
        onOpenOauth={vi.fn()}
        onClaude={vi.fn()}
      />,
    );
    expect(screen.getByText("Normal")).toBeInTheDocument();
  });
  it("uses shared privacy and read-only controls", () => {
    usePrivacyStore.setState({ blurred: true });
    render(
      <AccountList
        accounts={[]}
        claudeAccounts={[account]}
        selectedAccountId={account.id}
        onSelect={vi.fn()}
        onOpenImport={vi.fn()}
        onOpenOauth={vi.fn()}
        onClaude={vi.fn()}
        readOnly
      />,
    );
    expect(screen.getByText(account.name)).toHaveClass("privacy-blur");
    expect(screen.getByRole("button", { name: /Add account/i })).toBeDisabled();
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
