import { describe, expect, it } from "vitest";

import { accountActivityByKey, activityDates } from "@/features/accounts/hooks/use-provider-activity";
import { EMPTY_REPORT, NO_COVERAGE_GAPS } from "@/features/reports/test-fixtures";
import type { ReportsResponse } from "@/features/reports/schemas";

type Split = ReportsResponse["dailyByAccount"][number];

function split(date: string, identity: Pick<Split, "accountId" | "modelSourceId">, overrides: Partial<Split> = {}): Split {
  return {
    ...NO_COVERAGE_GAPS,
    ...identity,
    provider: identity.modelSourceId ? "claude" : "codex",
    name: null,
    date,
    requests: 1,
    inputTokens: 100,
    cachedInputTokens: 40,
    outputTokens: 10,
    reasoningTokens: null,
    costUsd: 0.5,
    errorCount: 0,
    ...overrides,
  };
}

describe("provider activity", () => {
  it("lists the seven calendar days ending today", () => {
    expect(activityDates(new Date(2026, 9, 31, 15))).toEqual([
      "2026-10-25",
      "2026-10-26",
      "2026-10-27",
      "2026-10-28",
      "2026-10-29",
      "2026-10-30",
      "2026-10-31",
    ]);
  });

  it("keys activity by account, fills missing days and totals the range", () => {
    const dates = ["2026-10-29", "2026-10-30", "2026-10-31"];
    const report: ReportsResponse = {
      ...EMPTY_REPORT,
      dailyByAccount: [
        split("2026-10-29", { accountId: "acc_a", modelSourceId: null }),
        split("2026-10-31", { accountId: "acc_a", modelSourceId: null }, { requests: 3, errorCount: 1, costUsd: 1.5 }),
        split("2026-10-31", { accountId: null, modelSourceId: "src_claude" }, { unpricedRequests: 2 }),
        split("2026-10-31", { accountId: null, modelSourceId: null }),
      ],
    };
    const activity = accountActivityByKey(report, dates);
    expect([...activity.keys()]).toEqual(["account:acc_a", "source:src_claude"]);
    const codex = activity.get("account:acc_a")!;
    expect(codex.days.map((day) => day.requests)).toEqual([1, 0, 3]);
    expect(codex.today).toMatchObject({ date: "2026-10-31", requests: 3, errors: 1, costUsd: 1.5, tokens: 110 });
    expect(codex.total).toMatchObject({ requests: 4, errors: 1, costUsd: 2, cachedInputTokens: 80, inputTokens: 200 });
    expect(activity.get("source:src_claude")!.today.unpricedRequests).toBe(2);
  });
});
