import { render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { ProvidersPage } from "@/features/accounts/components/providers-page";
import { useAuthStore } from "@/features/auth/hooks/use-auth";
import { useAccountQuotaDisplayStore } from "@/hooks/use-account-quota-display";
import { ADMIN_PERMISSIONS, createUpstreamProxyAdmin } from "@/test/mocks/factories";
import type { AccountSummary } from "@/features/accounts/schemas";
import { createOpenRouterAccount } from "@/features/openrouter/test-fixtures";
import { createClaudeAccount } from "@/features/claude/test-fixtures";

/** Renders the page at a path and waits until the provider queries have loaded. */
async function renderPage(path = "/providers") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/providers" element={<ProvidersPage />} />
          <Route path="/providers/:accountId" element={<ProvidersPage />} />
          <Route path="/providers/:accountId/settings" element={<ProvidersPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await screen.findByTestId(path === "/providers" ? "providers-list" : "provider-detail-layout");
  return view;
}

// Trends have their own query-provider integration coverage; these tests exercise
// the account page's selection and mutation controls.
vi.mock("@/features/accounts/components/provider-account-trends", () => ({
  ProviderAccountTrends: () => <div>Account trends</div>,
}));

const openRouterMocks = vi.hoisted(() => ({ accounts: [] as import("@/features/openrouter/api").OpenRouterAccount[] }));
vi.mock("@/features/openrouter/use-openrouter", () => ({
  useOpenRouterAccounts: () => ({ data: { accounts: openRouterMocks.accounts }, error: null, isLoading: false }),
  useOpenRouter: () => ({ create: idleMutation(), update: idleMutation(), refresh: idleMutation(), remove: idleMutation() }),
}));
const claudeMocks = vi.hoisted(() => ({ accounts: [] as import("@/features/claude/api").ClaudeAccount[] }));
vi.mock("@/features/claude/use-claude", () => ({
  useClaudeAccounts: () => ({ data: { accounts: claudeMocks.accounts }, error: null, isLoading: false }),
  useClaude: () => ({ enroll: idleMutation(), reconnect: idleMutation(), confirmReconnect: idleMutation(), discardReconnect: idleMutation(), start: idleMutation(), complete: idleMutation(), update: idleMutation(), refresh: idleMutation(), remove: idleMutation() }),
}));

vi.mock("@/features/accounts/hooks/use-accounts", () => ({
  useAccounts: vi.fn(),
  useAccountTrends: vi.fn(() => ({ data: null })),
  useAccountUsageResetCredits: vi.fn(() => ({
    data: { rateLimitResetCredits: { availableCount: 3 } },
    isFetching: false,
    error: null,
  })),
}));

vi.mock("@/features/accounts/hooks/use-oauth", () => ({
  useOauth: vi.fn(() => ({
    state: {
      status: "idle",
      method: null,
      authorizationUrl: null,
      callbackUrl: null,
      verificationUrl: null,
      userCode: null,
      deviceAuthId: null,
      intervalSeconds: null,
      expiresInSeconds: null,
      errorMessage: null,
    },
    start: vi.fn(),
    complete: vi.fn(),
    manualCallback: vi.fn(),
    reset: vi.fn(),
  })),
}));

vi.mock("@/features/settings/hooks/use-settings", () => ({
  useSettings: vi.fn(() => ({
    settingsQuery: {
      data: {
        showResetCreditBadges: true,
        showResetCreditExpiryBadge: true,
      },
      error: null,
    },
  })),
  useUpstreamProxyAdmin: vi.fn(() => ({
    upstreamProxyQuery: { data: null, error: null },
    accountBindingMutation: {
      isPending: false,
      error: null,
      mutateAsync: vi.fn(),
    },
    testEndpointMutation: {
      isPending: false,
      error: null,
      mutateAsync: vi.fn(),
    },
  })),
}));

const { useAccounts } = await import("@/features/accounts/hooks/use-accounts");
const mockedUseAccounts = useAccounts as unknown as ReturnType<typeof vi.fn>;
const { useUpstreamProxyAdmin } = await import("@/features/settings/hooks/use-settings");
const mockedUseUpstreamProxyAdmin = useUpstreamProxyAdmin as unknown as ReturnType<typeof vi.fn>;

function mockAccountsQuery(accounts: AccountSummary[], mutations: Record<string, unknown> = {}) {
  mockedUseAccounts.mockReturnValue({
    accountsQuery: { data: accounts, error: null, refetch: vi.fn() },
    importMutation: idleMutation(),
    pauseMutation: idleMutation(),
    resumeMutation: idleMutation(),
    probeMutation: idleMutation(),
    usageResetMutation: idleMutation(),
    deleteMutation: idleMutation(),
    exportAuthMutation: idleMutation(),
    setAliasMutation: idleMutation(),
    limitWarmupMutation: idleMutation(),
    routingPolicyMutation: idleMutation(),
    creditPolicyMutation: idleMutation(),
    updateMutation: idleMutation(),
    ...mutations,
  } as unknown as ReturnType<typeof useAccounts>);
}

function idleMutation() {
  return {
    isPending: false,
    error: null,
    mutateAsync: vi.fn(),
  };
}

function account(overrides: Partial<AccountSummary>): AccountSummary {
  return {
    accountId: "acc-default",
    email: "default@example.com",
    displayName: "Default",
    planType: "plus",
    status: "active",
    additionalQuotas: [],
    limitWarmupEnabled: false,
    creditPolicy: "spend",
    ...overrides,
  };
}

describe("ProvidersPage", () => {
  beforeEach(() => {
    openRouterMocks.accounts = [];
    claudeMocks.accounts = [];
    // The auth store starts least-privilege; these cases exercise admin actions.
    useAuthStore.setState({
      initialized: true,
      authenticated: true,
      role: "admin",
      permissions: ADMIN_PERMISSIONS,
      canWrite: true,
    });
    useAccountQuotaDisplayStore.setState({ quotaDisplay: "weekly" });
    vi.spyOn(Date, "now").mockReturnValue(new Date("2026-01-01T12:00:00.000Z").getTime());
  });

  afterEach(() => {
    vi.restoreAllMocks();
    useAuthStore.setState({ role: "admin", permissions: ADMIN_PERMISSIONS, canWrite: true });
  });

  it("lists every provider's accounts in groups and opens an account from its row", async () => {
    claudeMocks.accounts = [createClaudeAccount({ id: "src_claude", name: "Team Claude" })];
    openRouterMocks.accounts = [createOpenRouterAccount()];
    mockAccountsQuery([account({ displayName: "Codex account" })]);
    await renderPage();

    expect(screen.getByRole("heading", { level: 1, name: "Providers" })).toBeInTheDocument();
    const groups = within(screen.getByTestId("providers-list")).getAllByRole("rowgroup");
    expect(groups.map((group) => group.getAttribute("aria-label")).slice(0, 3)).toEqual(["Codex", "Claude", "OpenRouter"]);
    expect(screen.queryByTestId("provider-detail-layout")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("link", { name: "Research" }));
    expect(await screen.findByTestId("openrouter-account-detail")).toBeVisible();
    expect(screen.queryByTestId("providers-list")).not.toBeInTheDocument();
  });

  it("opens the account from the URL beside the account rail", async () => {
    openRouterMocks.accounts = [createOpenRouterAccount()];
    mockAccountsQuery([account({ displayName: "Codex account" })]);
    await renderPage("/providers/src_research");

    expect(screen.getByTestId("openrouter-account-detail")).toBeVisible();
    const rail = screen.getByRole("navigation", { name: "Accounts" });
    expect(within(rail).getByRole("link", { name: /Research/ })).toHaveAttribute("aria-current", "page");
    const codex = within(rail).getByRole("link", { name: /Codex account/ });
    expect(codex).toHaveAttribute("href", "/providers/acc-default");
    expect(within(rail).getByRole("link", { name: /All providers/ })).toHaveAttribute("href", "/providers");

    await userEvent.click(codex);
    expect(await screen.findByRole("heading", { name: "Codex account" })).toBeInTheDocument();
    expect(screen.queryByTestId("openrouter-account-detail")).not.toBeInTheDocument();
  });

  it("explains an unknown account link", async () => {
    mockAccountsQuery([account({})]);
    await renderPage("/providers/deleted-account");
    expect(screen.getByText("Account not found")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Accounts" })).toBeInTheDocument();
  });

  it("adds OpenRouter through the account chooser", async () => {
    mockAccountsQuery([]);
    await renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Add account" }));
    await userEvent.click(within(screen.getByRole("group", { name: "API providers" })).getByRole("button", { name: /OpenRouter/ }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Add OpenRouter account" })).toBeVisible());
    expect(screen.getByLabelText("Inference API key")).toHaveAttribute("type", "password");
  });

  it("disables OpenRouter mutations for read-only users", async () => {
    useAuthStore.setState({ role: "guest", permissions: ["read"], canWrite: false, initialized: true });
    openRouterMocks.accounts = [createOpenRouterAccount()];
    mockAccountsQuery([]);
    await renderPage("/providers/src_research");
    for (const name of ["API keys", "Rename account", "Refresh balance", "Pause"])
      expect(screen.getByRole("button", { name })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(screen.getByRole("button", { name: "Models (0)" })).toBeDisabled();
    expect(screen.queryByRole("switch", { name: /All models/ })).not.toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Routing policy" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "More actions" }));
    expect(await screen.findByRole("menuitem", { name: "Delete account" })).toHaveAttribute("aria-disabled", "true");
  });

  it("keeps the upstream-proxy admin query idle and hides OAuth help for read-only guests", async () => {
    useAuthStore.setState({ role: "guest", permissions: ["read"], canWrite: false, initialized: true });
    // Guests receive a masked identity: no ChatGPT account/workspace ids and a redacted email.
    mockAccountsQuery([
      account({
        accountId: "acc-masked",
        email: "m***@example.com",
        displayName: "m***@example.com",
        chatgptAccountId: null,
        workspaceId: null,
      }),
    ]);

    const view = await renderPage();
    expect(mockedUseUpstreamProxyAdmin).toHaveBeenCalledWith({ enabled: false });
    expect(screen.queryByRole("button", { name: "Need help?" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add account" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Add Codex account" })).not.toBeInTheDocument();
    view.unmount();

    await renderPage("/providers/acc-masked");
    expect(screen.getByRole("heading", { name: "m***@example.com" })).toBeInTheDocument();
    expect(screen.getAllByText(/Personal \/ unknown workspace/).length).toBeGreaterThan(0);
  });

  it("does not render cached upstream-proxy data in the proxy-binding panel for read-only guests", async () => {
    useAuthStore.setState({ role: "guest", permissions: ["read"], canWrite: false, initialized: true });
    // enabled: false only stops fetching; an earlier admin session's response
    // can still be in the cache and must not reach the panel.
    mockedUseUpstreamProxyAdmin.mockReturnValue({
      upstreamProxyQuery: { data: createUpstreamProxyAdmin(), error: null },
      accountBindingMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      testEndpointMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
    });
    mockAccountsQuery([account({ accountId: "acc_primary" })]);

    await renderPage("/providers/acc_primary/settings");
    expect(screen.getByRole("heading", { name: "Default" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Routing policy" })).toBeDisabled();
    expect(screen.queryByText("Proxy binding")).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Account proxy pool" })).not.toBeInTheDocument();
    expect(screen.queryByText("Primary pool")).not.toBeInTheDocument();
  });

  it("renders the proxy-binding panel from upstream-proxy data for writers", async () => {
    mockedUseUpstreamProxyAdmin.mockReturnValue({
      upstreamProxyQuery: { data: createUpstreamProxyAdmin(), error: null },
      accountBindingMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
      testEndpointMutation: { isPending: false, error: null, mutateAsync: vi.fn() },
    });
    mockAccountsQuery([account({ accountId: "acc_primary" })]);

    await renderPage("/providers/acc_primary/settings");
    expect(screen.getByRole("region", { name: "Proxy binding" })).toBeInTheDocument();
  });

  it("enables the upstream-proxy admin query and toggles OAuth help for writers", async () => {
    mockAccountsQuery([]);
    await renderPage();
    expect(mockedUseUpstreamProxyAdmin).toHaveBeenCalledWith({ enabled: true });
    await userEvent.click(screen.getByRole("button", { name: "Need help?" }));
    expect(screen.getByText("Windows OAuth Help")).toBeInTheDocument();
  });

  it("confirms before resetting the account's usage", async () => {
    const user = userEvent.setup();
    const resetUsage = vi.fn().mockResolvedValue({
      status: "reset",
      accountId: "acc-reset",
      code: "reset",
      windowsReset: 2,
      usageWritten: true,
      primaryUsedPercentBefore: 100,
      primaryUsedPercentAfter: 2,
      secondaryUsedPercentBefore: 80,
      secondaryUsedPercentAfter: 0,
      accountStatusBefore: "rate_limited",
      accountStatusAfter: "active",
    });
    mockAccountsQuery(
      [
        account({
          accountId: "acc-reset",
          email: "reset@example.com",
          displayName: "Resettable",
          resetAtSecondary: "2026-01-01T13:00:00.000Z",
          windowMinutesSecondary: 10_080,
        }),
      ],
      { usageResetMutation: { isPending: false, error: null, mutateAsync: resetUsage } },
    );

    await renderPage("/providers/acc-reset");
    await user.click(screen.getByRole("button", { name: "Reset usage" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Reset usage" });
    expect(resetUsage).not.toHaveBeenCalled();
    await user.click(within(dialog).getByRole("button", { name: "Reset" }));
    await waitFor(() => expect(resetUsage).toHaveBeenCalledWith({ accountId: "acc-reset" }));
  });

  it("keeps force probe as an immediate action", async () => {
    const user = userEvent.setup();
    const probe = vi.fn().mockResolvedValue({
      status: "probed",
      accountId: "acc-probe",
      probeStatusCode: 200,
      primaryUsedPercentBefore: 10,
      primaryUsedPercentAfter: 9,
      secondaryUsedPercentBefore: 20,
      secondaryUsedPercentAfter: 19,
      accountStatusBefore: "active",
      accountStatusAfter: "active",
    });
    mockAccountsQuery(
      [
        account({
          accountId: "acc-probe",
          email: "probe@example.com",
          displayName: "Probe account",
          resetAtSecondary: "2026-01-01T13:00:00.000Z",
          windowMinutesSecondary: 10_080,
        }),
      ],
      { probeMutation: { isPending: false, error: null, mutateAsync: probe } },
    );

    await renderPage("/providers/acc-probe");
    await user.click(screen.getByRole("button", { name: "Force probe" }));
    expect(probe).toHaveBeenCalledWith({ accountId: "acc-probe" });
    expect(screen.queryByRole("alertdialog", { name: "Reset usage" })).not.toBeInTheDocument();
  });
});
