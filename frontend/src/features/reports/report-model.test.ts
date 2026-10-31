import { describe, expect, it } from "vitest";

import {
  accountFilterKey,
  capOutliers,
  median,
  OTHER_SERIES_KEY,
  previousWindow,
  splitAccountFilterKeys,
  stackTopGroups,
  totalSeriesParts,
  totalSeriesValue,
} from "./report-model";
import type { DailyReportRow } from "./schemas";

describe("account filter keys", () => {
  it("keys provider accounts by model source and Codex accounts by account", () => {
    expect(accountFilterKey({ accountId: null, modelSourceId: "src-1" })).toBe("source:src-1");
    expect(accountFilterKey({ accountId: "acc-1", modelSourceId: null })).toBe("account:acc-1");
    expect(accountFilterKey({ accountId: null, modelSourceId: null })).toBeNull();
  });

  it("splits selected keys into account and model-source IDs", () => {
    expect(splitAccountFilterKeys(["account:a", "source:s", "account:b"])).toEqual({
      accountIds: ["a", "b"],
      modelSourceIds: ["s"],
    });
  });
});

describe("stackTopGroups", () => {
  const days = ["2026-10-01", "2026-10-02"];

  it("keeps the largest groups and sums the remainder into other", () => {
    const points = ["a", "b", "c", "d", "e", "f"].flatMap((group, index) => [
      { group, date: days[0], value: 60 - index * 10 },
      { group, date: days[1], value: 1 },
    ]);

    const stacked = stackTopGroups(points, days, 5);

    expect(stacked.groups).toEqual(["a", "b", "c", "d", "e"]);
    expect(stacked.hasOther).toBe(true);
    expect(stacked.rows[0][OTHER_SERIES_KEY]).toBe(10);
    const dayTotal = (row: Record<string, number | string>) =>
      Object.entries(row).reduce((sum, [key, value]) => (key === "date" ? sum : sum + (value as number)), 0);
    expect(dayTotal(stacked.rows[0])).toBe(60 + 50 + 40 + 30 + 20 + 10);
    expect(dayTotal(stacked.rows[1])).toBe(6);
  });

  it("zero-fills days without data and drops groups without any value", () => {
    const stacked = stackTopGroups(
      [
        { group: "a", date: days[1], value: 3 },
        { group: "empty", date: days[0], value: 0 },
      ],
      days,
      5,
    );

    expect(stacked.groups).toEqual(["a"]);
    expect(stacked.hasOther).toBe(false);
    expect(stacked.rows).toEqual([
      { date: days[0], s0: 0 },
      { date: days[1], s0: 3 },
    ]);
  });
});

describe("total series", () => {
  const row = {
    date: "2026-10-01",
    requests: 4,
    conversations: 1,
    inputTokens: 1000,
    cachedInputTokens: 900,
    outputTokens: 300,
    reasoningTokens: 120,
    costUsd: 2.5,
    activeAccounts: 1,
    cancelledCount: 0,
    errorCount: 0,
  } satisfies DailyReportRow;

  it("divides input into uncached and cached input", () => {
    expect(totalSeriesParts("input").map((part) => totalSeriesValue(row, "input", part))).toEqual([100, 900]);
  });

  it("divides output into visible output and reported reasoning", () => {
    expect(totalSeriesParts("output").map((part) => totalSeriesValue(row, "output", part))).toEqual([180, 120]);
  });

  it("keeps cost and requests as one series", () => {
    expect(totalSeriesParts("cost").map((part) => totalSeriesValue(row, "cost", part))).toEqual([2.5]);
  });
});

describe("capOutliers", () => {
  it("draws a day above four times the median of the others at the scale edge", () => {
    const values = [84, 233, 99, 110, 2941, 101, 106];

    const capped = capOutliers(values);

    expect(capped.outliers).toEqual([false, false, false, false, true, false, false]);
    expect(capped.scaleMax).toBe(233);
  });

  it("ignores missing days", () => {
    expect(capOutliers([null, 10, 12, null])).toEqual({ scaleMax: 12, outliers: [false, false, false, false] });
  });
});

describe("median", () => {
  it("returns the middle value or the mean of the two middle values", () => {
    expect(median([3, 1, 2])).toBe(2);
    expect(median([4, 1, 3, 2])).toBe(2.5);
    expect(median([])).toBeNull();
  });
});

describe("previousWindow", () => {
  it("returns the equally long window before the selection", () => {
    expect(previousWindow("2026-10-25", "2026-10-31")).toEqual({ startDate: "2026-10-18", endDate: "2026-10-24" });
  });
});
