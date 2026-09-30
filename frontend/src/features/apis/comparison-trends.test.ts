import { describe, expect, it } from "vitest";

import type { ApiKeyComparisonSeries } from "./schemas";
import { buildComparisonPoints, selectComparisonSeries } from "./comparison-trends";

const hours = ["2026-09-30T08:00:00Z", "2026-09-30T09:00:00Z", "2026-09-30T10:00:00Z"];
function key(id: string, cost: number, tokens = 100): ApiKeyComparisonSeries {
  return { keyId: id, name: id, isDeleted: false,
    cost: hours.map((t) => ({ t, v: cost, pricedRequests: 1 })),
    tokens: hours.map((t) => ({ t, v: tokens })),
  };
}

describe("API-key comparison trends", () => {
  it("ranks the selected measure and combines every remaining key into Other without losing coverage", () => {
    const source = Array.from({ length: 7 }, (_, index) => key(`key${index}`, index, 10 - index));
    source[0].cost[0] = { t: hours[0], v: 0, unpricedRequests: 1, coverageUnknown: true };
    const selected = selectComparisonSeries(source, "cost");
    expect(selected.map((series) => series.id)).toEqual([
      "key:key6", "key:key5", "key:key4", "key:key3", "key:key2", "other",
    ]);
    const rows = buildComparisonPoints(selected, "cost", "hourly");
    expect(rows[0].measurements.other).toMatchObject({ v: 1, pricedRequests: 1, unpricedRequests: 1, coverageUnknown: true });
    expect(rows.reduce((sum, row) => sum + Object.values(row.values).reduce<number>((s, value) => s + (value ?? 0), 0), 0)).toBe(63);
    expect(selectComparisonSeries(source, "tokens").map((series) => series.id)).toEqual([
      "key:key0", "key:key1", "key:key2", "key:key3", "key:key4", "other",
    ]);
  });

  it("makes cumulative values window-local and carries missing-price coverage forward", () => {
    const source = key("a", 0.1);
    source.cost[1] = { t: hours[1], v: 0, unpricedRequests: 1, unmeteredRequests: 1 };
    source.cost[2] = { t: hours[2], v: 0.2, pricedRequests: 1 };
    const series = selectComparisonSeries([source], "cost");
    const hourly = buildComparisonPoints(series, "cost", "hourly");
    const cumulative = buildComparisonPoints(series, "cost", "cumulative");
    expect(hourly.map((point) => point.values["key:a"])).toEqual([0.1, null, 0.2]);
    expect(cumulative.map((point) => point.values["key:a"])).toEqual([0.1, 0.1, 0.3]);
    expect(cumulative[2].measurements["key:a"]).toMatchObject({ pricedRequests: 2, unpricedRequests: 1, unmeteredRequests: 1 });
    expect(buildComparisonPoints(selectComparisonSeries([source], "tokens"), "tokens", "cumulative")
      .map((point) => point.values["key:a"])).toEqual([100, 200, 300]);
  });

  it("keeps a hidden key excluded when changing the measure moves it into Other", () => {
    const source = Array.from({ length: 7 }, (_, index) => key(`key${index}`, index, 10 - index));
    const hidden = new Set(["key:key1"]);
    expect(selectComparisonSeries(source, "tokens", hidden).slice(0, 5).some((item) => item.id === "key:key1")).toBe(true);
    const series = selectComparisonSeries(source, "cost", hidden);
    expect(series.slice(0, 5).some((item) => item.id === "key:key1")).toBe(false);
    expect(buildComparisonPoints(series, "cost", "cumulative")[2].values.other).toBe(0);
  });

  it("keeps unknown-only cost as a gap while genuine free usage remains zero", () => {
    const unknown = key("unknown", 0);
    unknown.cost = hours.map((t) => ({ t, v: 0, unpricedRequests: 1 }));
    const series = selectComparisonSeries([unknown, key("free", 0)], "cost");
    for (const mode of ["hourly", "cumulative"] as const) {
      const rows = buildComparisonPoints(series, "cost", mode);
      expect(rows.every((row) => row.values["key:unknown"] === null)).toBe(true);
      expect(rows.every((row) => row.values["key:free"] === 0)).toBe(true);
    }
  });

  it("breaks ranking ties by identity and keeps deleted keys anonymous", () => {
    const first = key("a", 1);
    const second = key("b", 1);
    const deleted = { ...key("c", 1), keyId: null, name: null, isDeleted: true };
    expect(selectComparisonSeries([second, deleted, first], "cost").map((item) => [item.id, item.kind]))
      .toEqual([["deleted", "deleted"], ["key:a", "key"], ["key:b", "key"]]);
    expect(buildComparisonPoints([], "cost", "hourly")).toEqual([]);
  });
});
