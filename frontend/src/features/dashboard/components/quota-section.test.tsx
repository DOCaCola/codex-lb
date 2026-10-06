import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { createClaudeAccount, createClaudeQuotaWindow } from "@/features/claude/test-fixtures";
import { QuotaSection } from "@/features/dashboard/components/quota-section";
import type { DashboardView } from "@/features/dashboard/utils";
import { useDashboardPreferencesStore } from "@/hooks/use-dashboard-preferences";

const view: DashboardView = {
  stats: [],
  primaryUsageItems: [],
  secondaryUsageItems: [],
  primaryTotal: 0,
  secondaryTotal: 0,
  requestLogs: [],
  safeLinePrimary: null,
  safeLineSecondary: null,
  weeklyCreditPace: null,
  claudeWeeklyPace: null,
  topConsumers: { codex: [], claude: [] },
};

describe("QuotaSection", () => {
  beforeEach(() => {
    localStorage.clear();
    useDashboardPreferencesStore.setState({ quotaProvider: "codex" });
  });

  it("shows Codex quota without a provider toggle when no Claude accounts exist", async () => {
    useDashboardPreferencesStore.setState({ quotaProvider: "claude" });

    render(
      <QuotaSection
        view={view}
        primaryCapacityCredits={0}
        secondaryCapacityCredits={0}
        claudeAccounts={[]}
        claudeAccountColors={new Map()}
      />,
    );

    expect(screen.getByTestId("quota-section")).toHaveAttribute("data-provider", "codex");
    expect(screen.queryByRole("group", { name: "Quota provider" })).not.toBeInTheDocument();
    expect(await screen.findByText("5-Hour Credits")).toBeInTheDocument();
  });

  it("switches to pooled Claude quota and notes accounts left out of the pool", async () => {
    const user = userEvent.setup();
    const accounts = [
      createClaudeAccount({ id: "max", name: "Claude Max", quotaWeight: 5 }),
      createClaudeAccount({
        id: "stale",
        name: "Claude Stale",
        quota: {
          observedAt: null,
          models: [],
          windows: [
            createClaudeQuotaWindow({ name: "five_hour", freshness: "stale" }),
            createClaudeQuotaWindow({ name: "seven_day" }),
          ],
        },
      }),
    ];

    render(
      <QuotaSection
        view={view}
        primaryCapacityCredits={0}
        secondaryCapacityCredits={0}
        claudeAccounts={accounts}
        claudeAccountColors={new Map()}
      />,
    );

    const toggle = screen.getByRole("group", { name: "Quota provider" });
    await user.click(within(toggle).getByRole("button", { name: "Claude" }));

    expect(useDashboardPreferencesStore.getState().quotaProvider).toBe("claude");
    expect(screen.getByTestId("quota-section")).toHaveAttribute("data-provider", "claude");
    expect(await screen.findByText("5-Hour Quota")).toBeInTheDocument();
    expect(screen.getByText("Weekly Quota")).toBeInTheDocument();
    expect(screen.getByText("1 account not pooled · quota unknown (Claude Stale)")).toBeInTheDocument();
    expect(screen.queryByText("5-Hour Credits")).not.toBeInTheDocument();
  });
});
