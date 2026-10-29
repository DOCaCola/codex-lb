import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { createClaudeAccount, createClaudeQuotaWindow } from "@/features/claude/test-fixtures";
import { createAntigravityAccount, createAntigravityWindow } from "@/features/antigravity/test-fixtures";
import { QuotaSection } from "@/features/dashboard/components/quota-section";
import type { DashboardView, WeeklyCreditPace } from "@/features/dashboard/utils";
import { useDashboardPreferencesStore } from "@/hooks/use-dashboard-preferences";

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
        antigravityAccounts={[]}
        modelSourceColors={new Map()}
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
        antigravityAccounts={[]}
        modelSourceColors={new Map()}
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
  it("shows each Antigravity family as its own plan-weighted bar and paces the tightest family", async () => {
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

    render(
      <QuotaSection
        view={{
          ...view,
          antigravityWeeklyPace: [
            { family: "gemini", pace: familyPace({ runwayStatus: "safe", headroomPercent: 57, depletionEtaHours: 120 }) },
            { family: "claude", pace: familyPace({ runwayStatus: "tight", headroomPercent: 57, depletionEtaHours: 40 }) },
          ],
        }}
        primaryCapacityCredits={0}
        secondaryCapacityCredits={0}
        claudeAccounts={[]}
        antigravityAccounts={accounts}
        modelSourceColors={new Map()}
      />,
    );

    const toggle = screen.getByRole("group", { name: "Quota provider" });
    expect(within(toggle).queryByRole("button", { name: "Claude" })).not.toBeInTheDocument();
    await user.click(within(toggle).getByRole("button", { name: "Antigravity" }));

    expect(screen.getByTestId("quota-section")).toHaveAttribute("data-provider", "antigravity");
    const [fiveHour, weeklyCard] = screen.getAllByTestId("antigravity-quota-bars");
    expect(within(fiveHour).getByTestId("antigravity-family-gemini")).toHaveTextContent("not reported");
    expect(within(weeklyCard).getByTestId("antigravity-family-gemini")).toHaveTextContent("3.4 / 6 · 43% used");
    const argon = within(weeklyCard).getByTestId("antigravity-family-argon");
    expect(argon).toHaveTextContent("4.5 / 5 · 10% used");
    expect(argon).toHaveTextContent("not reported by Team Pro");
    expect(within(weeklyCard).getByTestId("antigravity-quota-note")).toHaveTextContent(
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
