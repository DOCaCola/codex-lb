import { describe, expect, it } from "vitest";

import { summarizeEntry, type ProviderSummary } from "@/features/accounts/provider-summary";
import { summaryContext } from "@/features/accounts/test-utils";
import { createClaudeAccount, createClaudeQuotaWindow } from "@/features/claude/test-fixtures";
import { buildUpcomingEvents, UPCOMING_HORIZON_MS, type UpcomingPool, type UpcomingSources } from "@/features/dashboard/upcoming-events";
import type { WeeklyCreditPace } from "@/features/dashboard/utils";
import { createAccountSummary } from "@/test/mocks/factories";

const NOW = Date.parse("2026-11-07T12:15:00Z");
const inHours = (hours: number) => new Date(NOW + hours * 3_600_000).toISOString();

function codex(id: string, overrides: Parameters<typeof createAccountSummary>[0] = {}): ProviderSummary {
  return summarizeEntry(
    { kind: "codex", account: createAccountSummary({ accountId: id, email: `${id}@example.com`, displayName: id, ...overrides }) },
    summaryContext({ now: NOW }),
  );
}

function pace(overrides: Partial<WeeklyCreditPace> = {}): WeeklyCreditPace {
  return {
    unit: "credits",
    totalFullCredits: 80_000,
    totalActualRemainingCredits: 25_600,
    totalExpectedRemainingCredits: 40_000,
    actualUsedPercent: 68,
    scheduledUsedPercent: 50,
    deltaPercent: 18,
    scheduleGapCredits: 14_400,
    overPlanCredits: 14_400,
    projectedShortfallCredits: 0,
    pauseForBreakEvenHours: null,
    paceMultiplier: null,
    throttleToPercent: null,
    reduceByPercent: null,
    proAccountEquivalentToCoverOverPlan: null,
    proAccountsToCoverOverPlan: null,
    projectedDepletionHours: null,
    projectedMinimumRemainingCredits: null,
    forecastBurnRateCreditsPerHour: null,
    scheduledBurnRateCreditsPerHour: 500,
    status: "on_track",
    accountCount: 3,
    staleAccountCount: 0,
    inactiveAccountCount: 0,
    confidence: "high",
    resetEvents: [],
    subscriptionEnds: [],
    runwayStatus: "safe",
    ...overrides,
  };
}

function build(sources: Partial<UpcomingSources>) {
  return buildUpcomingEvents({
    summaries: [],
    subscriptionEnds: [],
    pools: [],
    now: NOW,
    horizonMs: UPCOMING_HORIZON_MS["24h"],
    ...sources,
  });
}

const codexPool = (overrides: Partial<WeeklyCreditPace>): UpcomingPool => ({ provider: "codex", family: null, pace: pace(overrides) });

describe("buildUpcomingEvents", () => {
  it("gives a limited account's return the credits its weekly reset returns", () => {
    const limited = codex("plus-2", {
      status: "rate_limited",
      usage: { primaryRemainingPercent: 40, secondaryRemainingPercent: 0, monthlyRemainingPercent: null },
      resetAtSecondary: inHours(8.6),
    });
    const events = build({
      summaries: [limited],
      pools: [codexPool({ resetEvents: [{ at: inHours(8.6), creditsReturned: 36_800 }] })],
    });

    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({
      kind: "back",
      window: "Weekly",
      accounts: [limited],
      amount: { value: 36_800, unit: "credits" },
      poolPercent: 46,
    });
  });

  it("puts accounts coming back at the same moment on one row", () => {
    const at = inHours(2);
    const accounts = ["a", "b", "c"].map((id) =>
      codex(id, {
        status: "rate_limited",
        usage: { primaryRemainingPercent: 0, secondaryRemainingPercent: 50, monthlyRemainingPercent: null },
        resetAtPrimary: at,
      }),
    );

    const events = build({ summaries: accounts });

    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ kind: "back", window: "5h" });
    expect(events[0].accounts.map((summary) => summary.id)).toEqual(["a", "b", "c"]);
  });

  it("names the account of a pool reset and leaves out barely used and well-filled windows", () => {
    const low = codex("low", {
      usage: { primaryRemainingPercent: 60, secondaryRemainingPercent: 12, monthlyRemainingPercent: null },
      resetAtPrimary: inHours(1),
      resetAtSecondary: inHours(5),
    });
    const fresh = codex("fresh", {
      usage: { primaryRemainingPercent: 90, secondaryRemainingPercent: 85, monthlyRemainingPercent: null },
      resetAtPrimary: inHours(3),
      resetAtSecondary: inHours(6),
    });
    const events = build({
      summaries: [low, fresh],
      pools: [
        codexPool({
          resetEvents: [
            { at: inHours(5), creditsReturned: 22_000 },
            { at: inHours(6), creditsReturned: 3_750 },
          ],
        }),
      ],
    });

    expect(events.map((event) => [event.kind, event.accounts.map((summary) => summary.id), event.window])).toEqual([
      ["reset", ["low"], "Weekly"],
    ]);
  });

  it("lists low windows of active accounts refilling, in time order", () => {
    const claude = summarizeEntry(
      {
        kind: "claude",
        account: createClaudeAccount({
          quota: {
            observedAt: null,
            models: [],
            windows: [
              createClaudeQuotaWindow({ name: "five_hour", utilization: 98, resetsAt: inHours(0.4) }),
              createClaudeQuotaWindow({ name: "seven_day", utilization: 50, resetsAt: inHours(10.75) }),
            ],
          },
        }),
      },
      summaryContext({ now: NOW }),
    );
    const paused = codex("paused", {
      status: "paused",
      usage: { primaryRemainingPercent: 5, secondaryRemainingPercent: 50, monthlyRemainingPercent: null },
      resetAtPrimary: inHours(0.2),
    });

    const events = build({ summaries: [paused, claude] });

    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ kind: "refill", provider: "claude", window: "5h", percentLeft: 2 });
    expect(events[0].at).toBe(Date.parse(inHours(0.4)));
  });

  it("marks run-outs and lapses at their estimated moment and drops those past the horizon", () => {
    const events = build({
      pools: [
        { provider: "claude", family: null, pace: pace({ unit: "pro_units", runwayStatus: "runs_dry", depletionEtaHours: 5 }) },
        codexPool({ runwayStatus: "lapses", lapsingCredits: 12_000, lapseInHours: 9 }),
        { provider: "antigravity", family: "gemini", pace: pace({ runwayStatus: "runs_dry", depletionEtaHours: 30 }) },
      ],
    });

    expect(events.map((event) => [event.kind, event.provider, (event.at - NOW) / 3_600_000])).toEqual([
      ["runsDry", "claude", 5],
      ["lapse", "codex", 9],
    ]);
    expect(events[1].amount).toEqual({ value: 12_000, unit: "credits" });
  });

  it("lists subscription ends with the weekly credits they remove", () => {
    const ending = codex("ending");
    const events = build({
      summaries: [ending],
      subscriptionEnds: [{ accountId: "ending", modelSourceId: null, endsAt: inHours(70) }],
      pools: [codexPool({ subscriptionEnds: [{ at: inHours(70), weeklyCredits: 7_560 }] })],
      horizonMs: UPCOMING_HORIZON_MS["7d"],
    });

    expect(events).toEqual([
      expect.objectContaining({ kind: "subscriptionEnd", accounts: [ending], amount: { value: 7_560, unit: "credits" } }),
    ]);
    expect(build({ summaries: [ending], subscriptionEnds: [{ accountId: "ending", modelSourceId: null, endsAt: inHours(70) }] })).toEqual([]);
  });
});
