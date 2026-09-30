import type { ApiKeyComparisonSeries, ApiKeyTrendPoint } from "@/features/apis/schemas";
import { isCostCoverageComplete } from "@/features/dashboard/cost-coverage";

export type ComparisonMetric = "cost" | "tokens";
export type ComparisonMode = "hourly" | "cumulative";
export type ComparisonSeries = {
  id: string;
  name: string | null;
  kind: "key" | "deleted" | "other";
  points: ApiKeyTrendPoint[];
};
export type ComparisonPoint = {
  t: string;
  values: Record<string, number | null>;
  measurements: Record<string, ApiKeyTrendPoint>;
};

export function comparisonSeriesId(series: ApiKeyComparisonSeries): string {
  return series.isDeleted ? "deleted" : `key:${series.keyId}`;
}

function addPoints(left: ApiKeyTrendPoint, right: ApiKeyTrendPoint): ApiKeyTrendPoint {
  return {
    t: left.t,
    v: left.v + right.v,
    pricedRequests: (left.pricedRequests ?? 0) + (right.pricedRequests ?? 0),
    unpricedRequests: (left.unpricedRequests ?? 0) + (right.unpricedRequests ?? 0),
    unmeteredRequests: (left.unmeteredRequests ?? 0) + (right.unmeteredRequests ?? 0),
    coverageUnknown: !!left.coverageUnknown || !!right.coverageUnknown,
  };
}

/** Rank once per measure, keeping hidden keys in their original comparison group. */
export function selectComparisonSeries(
  source: ApiKeyComparisonSeries[], metric: ComparisonMetric, hidden: ReadonlySet<string> = new Set(),
): ComparisonSeries[] {
  const ranked = source.map((series) => ({
    id: comparisonSeriesId(series),
    name: series.name,
    kind: series.isDeleted ? "deleted" as const : "key" as const,
    points: series[metric],
  })).sort((left, right) => {
    const difference = right.points.reduce((sum, point) => sum + point.v, 0)
      - left.points.reduce((sum, point) => sum + point.v, 0);
    return difference || left.id.localeCompare(right.id);
  });
  if (ranked.length <= 5) return ranked;
  const other = new Map<string, ApiKeyTrendPoint>();
  for (const series of ranked.slice(5)) {
    for (const point of series.points) {
      const included = hidden.has(series.id) ? { t: point.t, v: 0 } : point;
      other.set(point.t, addPoints(other.get(point.t) ?? { t: point.t, v: 0 }, included));
    }
  }
  return [...ranked.slice(0, 5), {
    id: "other",
    name: null,
    kind: "other",
    points: [...other.values()].sort((left, right) => left.t.localeCompare(right.t)),
  }];
}

export function buildComparisonPoints(
  series: ComparisonSeries[], metric: ComparisonMetric, mode: ComparisonMode,
): ComparisonPoint[] {
  const rows = new Map<string, ComparisonPoint>();
  for (const item of series) {
    let running: ApiKeyTrendPoint = { t: "", v: 0 };
    for (const point of item.points) {
      running = { ...addPoints(running, point), t: point.t };
      const measurement = mode === "cumulative" ? running : point;
      const unknownOnly = metric === "cost" && measurement.v === 0
        && !measurement.pricedRequests && !isCostCoverageComplete(measurement);
      const row = rows.get(point.t) ?? { t: point.t, values: {}, measurements: {} };
      row.values[item.id] = unknownOnly ? null : metric === "cost"
        ? Math.round(measurement.v * 1_000_000) / 1_000_000 : measurement.v;
      row.measurements[item.id] = measurement;
      rows.set(point.t, row);
    }
  }
  return [...rows.values()].sort((left, right) => left.t.localeCompare(right.t));
}
