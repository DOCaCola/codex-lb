import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test/utils";
import {
  ADMIN_PERMISSIONS,
  createDashboardOverview,
  createDashboardProjections,
} from "@/test/mocks/factories";
import type { ProviderSummary } from "@/features/accounts/provider-summary";
import { useAccountMutations } from "@/features/accounts/hooks/use-accounts";
import { useAuthStore } from "@/features/auth/hooks/use-auth";
import type { DashboardAccountsProps } from "@/features/dashboard/components/dashboard-accounts";
import { useDashboard, useDashboardProjections } from "@/features/dashboard/hooks/use-dashboard";
import { buildDashboardView } from "@/features/dashboard/utils";
import { useDashboardPreferencesStore } from "@/hooks/use-dashboard-preferences";

import { DashboardPage } from "./dashboard-page";

const { accountCardsSpy, accountListSpy } = vi.hoisted(() => ({
  accountCardsSpy: vi.fn(),
  accountListSpy: vi.fn(),
}));

vi.mock("@/features/accounts/hooks/use-accounts", () => ({
  useAccountMutations: vi.fn(),
}));

vi.mock("@/features/dashboard/hooks/use-dashboard", () => ({
  useDashboard: vi.fn(),
  useDashboardProjections: vi.fn(),
}));

vi.mock("@/features/dashboard/utils", () => ({
  buildDashboardView: vi.fn(),
}));

vi.mock("@/features/dashboard/components/dashboard-accounts", () => ({
  DashboardAccountCards: (props: DashboardAccountsProps) => {
    accountCardsSpy(props);
    return <div data-testid="account-cards">Cards for {props.summaries.length} accounts</div>;
  },
  DashboardAccountList: (props: DashboardAccountsProps) => {
    accountListSpy(props);
    return <div data-testid="account-list">List for {props.summaries.length} accounts</div>;
  },
}));

vi.mock("@/features/dashboard/components/dashboard-skeleton", () => ({
  DashboardSkeleton: () => <div data-testid="dashboard-skeleton" />,
}));

vi.mock("@/features/dashboard/components/activity-strip", () => ({
  ActivityStrip: () => <div data-testid="activity-strip" />,
}));

vi.mock("@/features/dashboard/components/quota-section", () => ({
  QuotaSection: () => <div data-testid="quota-section" />,
}));

const useAccountMutationsMock = vi.mocked(useAccountMutations);
const useDashboardMock = vi.mocked(useDashboard);
const useDashboardProjectionsMock = vi.mocked(useDashboardProjections);
const buildDashboardViewMock = vi.mocked(buildDashboardView);

describe("DashboardPage", () => {
  const resume = vi.fn();

  beforeEach(() => {
    useAuthStore.setState({
      role: "admin",
      permissions: ADMIN_PERMISSIONS,
      canWrite: true,
      initialized: true,
    });
    accountCardsSpy.mockReset();
    accountListSpy.mockReset();
    resume.mockReset();
    useAccountMutationsMock.mockReset();
    useDashboardMock.mockReset();
    useDashboardProjectionsMock.mockReset();
    buildDashboardViewMock.mockReset();
    useDashboardPreferencesStore.setState({
      accountBurnrateEnabled: true,
      accountViewMode: "cards",
      initialized: true,
    });
  });

  function mockReadyDashboard() {
    const overview = createDashboardOverview();

    useAccountMutationsMock.mockReturnValue({
      resumeMutation: { mutateAsync: resume },
    } as unknown as ReturnType<typeof useAccountMutations>);
    useDashboardMock.mockReturnValue({
      data: overview,
      isFetching: false,
      error: null,
    } as ReturnType<typeof useDashboard>);
    useDashboardProjectionsMock.mockReturnValue({
      data: createDashboardProjections(),
      isFetching: false,
      error: null,
    } as ReturnType<typeof useDashboardProjections>);
    buildDashboardViewMock.mockReturnValue({
      stats: [],
      weeklyCreditPace: null,
      claudeWeeklyPace: null,
      antigravityWeeklyPace: [],
      topConsumers: { codex: [], claude: [], antigravity: [] },
      primaryUsageItems: [],
      secondaryUsageItems: [],
      primaryTotal: 0,
      secondaryTotal: 0,
      safeLinePrimary: null,
      safeLineSecondary: null,
    } as ReturnType<typeof buildDashboardView>);

    return overview;
  }

  it("keeps the page-wide skeleton while overview data is unavailable", () => {
    mockReadyDashboard();
    useDashboardMock.mockReturnValue({
      data: undefined,
      isFetching: true,
      error: null,
    } as ReturnType<typeof useDashboard>);

    renderWithProviders(<DashboardPage />);

    expect(screen.getByTestId("dashboard-skeleton")).toBeInTheDocument();
    expect(screen.queryByTestId("activity-strip")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Accounts" })).not.toBeInTheDocument();
  });

  it("summarizes account health under the title and in the Accounts header", () => {
    mockReadyDashboard();

    renderWithProviders(<DashboardPage />);

    expect(screen.getByTestId("dashboard-status-line")).toHaveTextContent("of 2 accounts can take work");
    const accountsHeader = screen.getByRole("heading", { name: "Accounts" }).parentElement as HTMLElement;
    expect(accountsHeader).toHaveTextContent(/2 accounts · \d ready/);
  });

  it("defaults the Accounts section to cards built from the overview accounts", () => {
    const overview = mockReadyDashboard();

    renderWithProviders(<DashboardPage />);

    expect(screen.getByTestId("account-cards")).toHaveTextContent("Cards for 2 accounts");
    expect(screen.queryByTestId("account-list")).not.toBeInTheDocument();
    const { summaries } = accountCardsSpy.mock.lastCall![0] as DashboardAccountsProps;
    expect(summaries.map((summary) => summary.id)).toEqual(
      expect.arrayContaining(overview.accounts.map((account) => account.accountId)),
    );
    expect(screen.getByRole("radio", { name: "View accounts as cards" })).toHaveAttribute("aria-checked", "true");
  });

  it("switches the Accounts section to list view", async () => {
    const user = userEvent.setup();
    mockReadyDashboard();

    renderWithProviders(<DashboardPage />);

    await user.click(screen.getByRole("radio", { name: "View accounts as list" }));

    expect(screen.getByTestId("account-list")).toHaveTextContent("List for 2 accounts");
    expect(screen.queryByTestId("account-cards")).not.toBeInTheDocument();
    expect(useDashboardPreferencesStore.getState().accountViewMode).toBe("list");
  });

  it("selects the overview timeframe from the Activity section", async () => {
    const user = userEvent.setup();
    mockReadyDashboard();

    renderWithProviders(<DashboardPage />);

    expect(useDashboardMock).toHaveBeenLastCalledWith("7d");
    const range = screen.getByRole("group", { name: "Overview timeframe" });
    expect(within(range).getByRole("button", { name: "7d" })).toHaveAttribute("aria-pressed", "true");
    await user.click(within(range).getByRole("button", { name: "30d" }));

    expect(useDashboardMock).toHaveBeenLastCalledWith("30d");
    expect(within(range).getByRole("button", { name: "30d" })).toHaveAttribute("aria-pressed", "true");
  });

  it("resumes a paused Codex account through the account mutations", () => {
    const overview = mockReadyDashboard();

    renderWithProviders(<DashboardPage />);

    const { summaries, actions } = accountCardsSpy.mock.lastCall![0] as DashboardAccountsProps;
    const codex = summaries.find((summary) => summary.id === overview.accounts[0].accountId) as ProviderSummary;
    act(() => actions.onResume(codex));

    expect(resume).toHaveBeenCalledWith(overview.accounts[0].accountId);
    expect(actions.readOnly).toBe(false);
  });
});
