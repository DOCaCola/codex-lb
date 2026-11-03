import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { renderDashboardAccounts } from "@/features/dashboard/test-utils";
import { useDashboardPreferencesStore } from "@/hooks/use-dashboard-preferences";
import { createAccountSummary } from "@/test/mocks/factories";

const usage = {
  primaryRemainingPercent: 60,
  secondaryRemainingPercent: 80,
  monthlyRemainingPercent: null,
  primaryRecentUsedPercent: 12.5,
  secondaryRecentUsedPercent: 0,
};

describe("dashboard recent usage slice", () => {
  beforeEach(() => {
    useDashboardPreferencesStore.setState({ recentUsageEnabled: true, recentShortMinutes: 60, recentLongPeriod: 1440 });
  });

  it("tints the share used in the last hour right after the remaining fill", () => {
    renderDashboardAccounts({ accounts: [createAccountSummary({ usage })] });
    const card = screen.getByTestId("dashboard-account-card");
    const slices = within(card).getAllByTestId("limit-recent-usage");
    expect(slices).toHaveLength(1);
    expect(slices[0]).toHaveStyle({ left: "calc(60% - 3px)", width: "calc(12.5% + 3px)" });
    expect(slices[0].parentElement).toHaveAttribute("title", "Used 12.5% in the last hour");
    expect(within(card).getByText("Used 12.5% in the last hour")).toHaveClass("sr-only");
  });

  it("names the chosen recent usage periods", () => {
    useDashboardPreferencesStore.setState({ recentShortMinutes: 30, recentLongPeriod: 360 });
    renderDashboardAccounts({
      accounts: [createAccountSummary({ usage: { ...usage, secondaryRemainingPercent: 70, secondaryRecentUsedPercent: 4 } })],
    });
    const card = screen.getByTestId("dashboard-account-card");
    expect(within(card).getByText("Used 12.5% in the last 30 minutes")).toBeInTheDocument();
    expect(within(card).getByText("Used 4% in the last 6 hours")).toBeInTheDocument();
  });

  it("names the weekly period since local midnight as today", () => {
    useDashboardPreferencesStore.setState({ recentLongPeriod: "today" });
    renderDashboardAccounts({
      accounts: [createAccountSummary({ usage: { ...usage, secondaryRemainingPercent: 70, secondaryRecentUsedPercent: 4 } })],
    });
    expect(within(screen.getByTestId("dashboard-account-card")).getByText("Used 4% today")).toBeInTheDocument();
  });

  it("caps the slice at the used part of the bar", () => {
    renderDashboardAccounts({
      accounts: [createAccountSummary({ usage: { ...usage, primaryRemainingPercent: 95, primaryRecentUsedPercent: 20 } })],
    });
    expect(screen.getByTestId("limit-recent-usage")).toHaveStyle({ width: "calc(5% + 3px)" });
  });

  it("hides the slice when the preference is off", () => {
    useDashboardPreferencesStore.setState({ recentUsageEnabled: false });
    renderDashboardAccounts({ accounts: [createAccountSummary({ usage })] }, { view: "list" });
    expect(screen.queryByTestId("limit-recent-usage")).not.toBeInTheDocument();
    expect(screen.queryByText(/in the last hour/)).not.toBeInTheDocument();
  });

  it("draws nothing without a recent-usage reading", () => {
    renderDashboardAccounts({ accounts: [createAccountSummary()] });
    expect(screen.queryByTestId("limit-recent-usage")).not.toBeInTheDocument();
  });
});
