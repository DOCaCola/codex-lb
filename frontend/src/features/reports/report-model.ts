import { shiftISODate } from "./daily-series";
import type { DailyReportRow } from "./schemas";

export type TrendMetric = "cost" | "input" | "output" | "requests";
export type TrendSplit = "total" | "account" | "model";
export type BreakdownMetric = "cost" | "requests";

export type MetricMeasures = {
  costUsd: number;
  inputTokens: number;
  outputTokens: number;
  requests: number;
};

export function metricValue(measures: MetricMeasures, metric: TrendMetric): number {
  switch (metric) {
    case "cost":
      return measures.costUsd;
    case "input":
      return measures.inputTokens;
    case "output":
      return measures.outputTokens;
    case "requests":
      return measures.requests;
  }
}

/** Identity of a Codex account or a provider account, as used by the account filter. */
export type AccountIdentity = {
  accountId: string | null;
  modelSourceId: string | null;
};

/** Filter value of an account: provider accounts are model sources, the rest Codex accounts. */
export function accountFilterKey(identity: AccountIdentity): string | null {
  if (identity.modelSourceId) return `source:${identity.modelSourceId}`;
  if (identity.accountId) return `account:${identity.accountId}`;
  return null;
}

export function splitAccountFilterKeys(keys: readonly string[]): {
  accountIds: string[];
  modelSourceIds: string[];
} {
  const accountIds: string[] = [];
  const modelSourceIds: string[] = [];
  for (const key of keys) {
    if (key.startsWith("source:")) modelSourceIds.push(key.slice("source:".length));
    else if (key.startsWith("account:")) accountIds.push(key.slice("account:".length));
  }
  return { accountIds, modelSourceIds };
}

export const OTHER_SERIES_KEY = "other";

export type StackedPoint = { group: string; date: string; value: number };

export type StackedRow = { date: string } & Record<string, number | string>;

export type StackedSeries = {
  /** Groups of the plotted series, largest first; their data keys come from seriesDataKey. */
  groups: string[];
  /** True when the remainder beyond the limit is plotted under OTHER_SERIES_KEY. */
  hasOther: boolean;
  /** One row per day with a value per data key; days without data are zero. */
  rows: StackedRow[];
};

/** Positional data keys, since group names such as "gpt-6.1-sol" read as nested paths in charts. */
export function seriesDataKey(index: number): string {
  return `s${index}`;
}

/**
 * Stacks the limit largest groups of the window per day and sums the rest
 * into one remainder series. Groups without any value are dropped.
 */
export function stackTopGroups(points: readonly StackedPoint[], days: readonly string[], limit: number): StackedSeries {
  const totals = new Map<string, number>();
  for (const point of points) {
    totals.set(point.group, (totals.get(point.group) ?? 0) + point.value);
  }
  const ranked = [...totals.entries()]
    .filter(([, total]) => total > 0)
    .sort((left, right) => right[1] - left[1])
    .map(([group]) => group);
  const groups = ranked.slice(0, limit);
  const hasOther = ranked.length > limit;
  const indexOf = new Map(groups.map((group, index) => [group, index]));
  const byDay = new Map<string, StackedRow>(
    days.map((date) => {
      const row: StackedRow = { date };
      groups.forEach((_, index) => {
        row[seriesDataKey(index)] = 0;
      });
      if (hasOther) row[OTHER_SERIES_KEY] = 0;
      return [date, row];
    }),
  );
  for (const point of points) {
    const row = byDay.get(point.date);
    const index = indexOf.get(point.group);
    if (!row || (index === undefined && !ranked.includes(point.group))) continue;
    const key = index === undefined ? OTHER_SERIES_KEY : seriesDataKey(index);
    row[key] = (row[key] as number) + point.value;
  }
  return { groups, hasOther, rows: [...byDay.values()] };
}

export type TotalSeriesPart = "value" | "uncachedInput" | "cachedInput" | "visibleOutput" | "reasoning";

/** Parts of the unsplit trend: input divides into uncached and cached, output into visible and reasoning. */
export function totalSeriesParts(metric: TrendMetric): TotalSeriesPart[] {
  if (metric === "input") return ["uncachedInput", "cachedInput"];
  if (metric === "output") return ["visibleOutput", "reasoning"];
  return ["value"];
}

export function totalSeriesValue(row: DailyReportRow, metric: TrendMetric, part: TotalSeriesPart): number {
  switch (part) {
    case "value":
      return metricValue(row, metric);
    case "uncachedInput":
      return Math.max(0, row.inputTokens - row.cachedInputTokens);
    case "cachedInput":
      return row.cachedInputTokens;
    case "visibleOutput":
      return Math.max(0, row.outputTokens - (row.reasoningTokens ?? 0));
    case "reasoning":
      return row.reasoningTokens ?? 0;
  }
}

export function median(values: readonly number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const middle = sorted.length >> 1;
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

/** A day is an outlier when it exceeds this multiple of the median of the other days. */
export const OUTLIER_FACTOR = 4;

export type CappedSeries = {
  /** Upper bound of the scale, set by the days that are not outliers. */
  scaleMax: number;
  outliers: boolean[];
};

/** Keeps a single extreme day from flattening the rest of a small line chart. */
export function capOutliers(values: ReadonlyArray<number | null>): CappedSeries {
  const present = values.flatMap((value, index) => (value === null ? [] : [{ value, index }]));
  const outliers = values.map(() => false);
  for (const { value, index } of present) {
    const othersMedian = median(present.filter((entry) => entry.index !== index).map((entry) => entry.value));
    if (othersMedian !== null && othersMedian > 0 && value > OUTLIER_FACTOR * othersMedian) {
      outliers[index] = true;
    }
  }
  const inScale = present.filter(({ index }) => !outliers[index]).map(({ value }) => value);
  return { scaleMax: Math.max(0, ...inScale), outliers };
}

/** The equally long window immediately before the selected one. */
export function previousWindow(startDate: string, endDate: string): { startDate: string; endDate: string } {
  const length = (Date.parse(`${endDate}T00:00:00Z`) - Date.parse(`${startDate}T00:00:00Z`)) / 86_400_000 + 1;
  return { startDate: shiftISODate(startDate, -length), endDate: shiftISODate(startDate, -1) };
}
