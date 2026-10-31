import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { createClaudeAccount, createClaudeQuotaWindow } from "@/features/claude/test-fixtures";
import { createAntigravityAccount, createAntigravityWindow } from "@/features/antigravity/test-fixtures";
import { QuotaSection, type QuotaSectionProps } from "@/features/dashboard/components/quota-section";
import { dashboardSummaries } from "@/features/dashboard/test-utils";
import type { DashboardView, WeeklyCreditPace } from "@/features/dashboard/utils";
import { useDashboardPreferencesStore } from "@/hooks/use-dashboard-preferences";
import { createAccountSummary } from "@/test/mocks/factories";

const view: DashboardView = {
  stats: [],
  primaryUsageItems: [],
  secondaryUsageItems: [],
  primaryTotal: 0,
  secondaryTotal: 0,
  safeLinePrimary: null,
  safeLineSecondary: null,
  weeklyCreditPace: null,
  claudeWeeklyPace: null,
  antigravityWeeklyPace: [],
  topConsumers: { codex: [], claude: [], antigravity: [] },
};

function renderSection(props: Partial<QuotaSectionProps>) {
  const sources = {
    accounts: props.codexAccounts ?? [],
    claudeAccounts: props.claudeAccounts ?? [],
    antigravityAccounts: props.antigravityAccounts ?? [],
  };
  return render(
    <QuotaSection
      view={view}
      codexAccounts={[]}
      primaryCapacityCredits={0}
      secondaryCapacityCredits={0}
      claudeAccounts={[]}
      antigravityAccounts={[]}
      summaries={new Map(dashboardSummaries(sources).map((summary) => [summary.id, summary]))}
      modelSourceColors={new Map()}
      keyColors={new Map()}
      {...props}
    />,
  );
}

describe("QuotaSection", () => {
  beforeEach(() => {
    localStorage.clear();
    useDashboardPreferencesStore.setState({ quotaProvider: "codex" });
  });

  it("shows Codex credits without a provider toggle when no other subscription accounts exist", () => {
    useDashboardPreferencesStore.setState({ quotaProvider: "claude" });
    const account = createAccountSummary({ accountId: "acc_plus", displayName: "DOCa Plus" });

    renderSection({
      view: {
        ...view,
        primaryUsageItems: [{ accountId: "acc_plus", label: "DOCa Plus", labelSuffix: "", isEmail: false, value: 120, remainingPercent: 50, color: "#2563eb" }],
        secondaryUsageItems: [{ accountId: "acc_plus", label: "DOCa Plus", labelSuffix: "", isEmail: false, value: 900, remainingPercent: 60, color: "#2563eb" }],
        primaryTotal: 120,
        secondaryTotal: 900,
      },
      codexAccounts: [account],
      primaryCapacityCredits: 240,
      secondaryCapacityCredits: 1500,
    });

    expect(screen.getByTestId("quota-section")).toHaveAttribute("data-provider", "codex");
    expect(screen.queryByRole("group", { name: "Quota provider" })).not.toBeInTheDocument();
    expect(screen.getByText("Remaining credits")).toBeInTheDocument();
    expect(screen.getByTestId("quota-ring-5h")).toHaveTextContent("of 240");
    expect(screen.getByTestId("quota-ring-weekly")).toHaveTextContent("of 1.5K");
    const row = screen.getByTestId("quota-remaining-row");
    expect(row).toHaveTextContent("DOCa Plus");
    expect(row).toHaveTextContent("120");
    expect(row).toHaveTextContent("900");
  });

  it("switches to pooled Claude quota and notes accounts left out of the pool", async () => {
    const user = userEvent.setup();
    const accounts = [
      createClaudeAccount({ id: "max", name: "Claude Max", quotaWeights: { fiveHour: 5, weekly: 5 } }),
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

    renderSection({ claudeAccounts: accounts });

    const toggle = screen.getByRole("group", { name: "Quota provider" });
    await user.click(within(toggle).getByRole("button", { name: "Claude" }));

    expect(useDashboardPreferencesStore.getState().quotaProvider).toBe("claude");
    expect(screen.getByTestId("quota-section")).toHaveAttribute("data-provider", "claude");
    expect(screen.getByText("Remaining quota")).toBeInTheDocument();
    expect(screen.queryByText("Remaining credits")).not.toBeInTheDocument();
    const [max, stale] = screen.getAllByTestId("quota-remaining-row");
    expect(max).toHaveTextContent("Claude Max");
    expect(stale).toHaveTextContent("not pooled");
    expect(screen.getByTestId("quota-remaining-note")).toHaveTextContent("1 account not pooled · quota unknown (Claude Stale)");
  });

  it("shows each Antigravity family as its own plan-weighted pool and paces the tightest family", async () => {
    const user = userEvent.setup();
    const weekly = (family: "gemini" | "argon" | "claude", usedPercent: number) =>
      createAntigravityWindow({ family, window: "weekly", usedPercent, resetsAt: new Date(Date.now() + 49 * 3_600_000).toISOString() });
    const accounts = [
      createAntigravityAccount({
        id: "ultra",
        name: "Team Ultra",
        planType: "ultra_5x",
        quotaWeight: 5,
        windows: [weekly("gemini", 40), weekly("argon", 10), weekly("claude", 50)],
      }),
      createAntigravityAccount({ id: "pro", name: "Team Pro", windows: [weekly("gemini", 60), weekly("claude", 10)] }),
      createAntigravityAccount({ id: "free", name: "Free Seat", planType: "free", quotaWeight: null }),
      createAntigravityAccount({ id: "stale", name: "Stale Seat", quotaFresh: false }),
    ];

    renderSection({
      view: {
        ...view,
        antigravityWeeklyPace: [
          { family: "gemini", pace: familyPace({ runwayStatus: "safe", headroomPercent: 57, depletionEtaHours: 120 }) },
          { family: "claude", pace: familyPace({ runwayStatus: "tight", headroomPercent: 57, depletionEtaHours: 40 }) },
        ],
      },
      antigravityAccounts: accounts,
    });

    const toggle = screen.getByRole("group", { name: "Quota provider" });
    expect(within(toggle).queryByRole("button", { name: "Claude" })).not.toBeInTheDocument();
    await user.click(within(toggle).getByRole("button", { name: "Antigravity" }));

    expect(screen.getByTestId("quota-section")).toHaveAttribute("data-provider", "antigravity");
    const card = screen.getByTestId("antigravity-remaining-card");
    const gemini = within(card).getByTestId("antigravity-family-gemini");
    expect(gemini.children[1]).toHaveTextContent("not reported");
    expect(gemini.children[2]).toHaveTextContent("57%");
    const argon = within(card).getByTestId("antigravity-family-argon");
    expect(argon.children[2]).toHaveTextContent("90%");
    expect(argon.children[2]).toHaveTextContent("not reported by Team Pro");
    expect(within(card).getByTestId("antigravity-quota-note")).toHaveTextContent(
      "2 accounts not pooled · plan not weighted (Free Seat) · quota unknown (Stale Seat)",
    );
    expect(screen.getByText("Antigravity · tightest: Claude & GPT")).toBeInTheDocument();
    const breakdown = screen.getByTestId("pace-breakdown");
    expect(within(breakdown).getByText("Gemini")).toBeInTheDocument();
    expect(within(breakdown).getByText("Claude & GPT")).toHaveClass("font-semibold");
    expect(screen.getByText("Antigravity · last 2h")).toBeInTheDocument();
  });
});


function familyPace(overrides: Partial<WeeklyCreditPace>): WeeklyCreditPace {
  return {
    unit: "pro_units",
    totalFullCredits: 6,
    totalActualRemainingCredits: 3.4,
    totalExpectedRemainingCredits: 3,
    actualUsedPercent: 43,
    scheduledUsedPercent: 50,
    deltaPercent: -7,
    scheduleGapCredits: 0,
    overPlanCredits: 0,
    projectedShortfallCredits: 0,
    pauseForBreakEvenHours: null,
    paceMultiplier: null,
    throttleToPercent: null,
    reduceByPercent: null,
    proAccountEquivalentToCoverOverPlan: null,
    proAccountsToCoverOverPlan: null,
    projectedDepletionHours: null,
    projectedMinimumRemainingCredits: null,
    forecastBurnRateCreditsPerHour: 0.03,
    scheduledBurnRateCreditsPerHour: 0.03,
    headroomCredits: 3.4,
    burnRateRecentCreditsPerHour: 0.03,
    nextReliefInHours: 49,
    nextReliefCredits: 2,
    resetEvents: [],
    saturatedAccountCount: 0,
    status: "on_track",
    accountCount: 2,
    staleAccountCount: 0,
    inactiveAccountCount: 0,
    confidence: "high",
    ...overrides,
  };
}
