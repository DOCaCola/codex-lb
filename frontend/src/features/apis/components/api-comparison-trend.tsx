import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ChartToggle } from "@/components/chart-toggle";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "@/components/lazy-recharts";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { buildComparisonPoints, comparisonSeriesId, selectComparisonSeries } from "@/features/apis/comparison-trends";
import type { ComparisonMetric, ComparisonMode, ComparisonPoint, ComparisonSeries } from "@/features/apis/comparison-trends";
import type { ApiKeysTrendsResponse } from "@/features/apis/schemas";
import { formatCoveredCostShort, isCostCoverageComplete } from "@/features/dashboard/cost-coverage";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { useThemeStore } from "@/hooks/use-theme";
import { cn } from "@/lib/utils";
import { buildDonutPalette } from "@/utils/colors";
import { formatChartDateTime, formatCompactNumber, formatCurrency } from "@/utils/formatters";

type DisplaySeries = ComparisonSeries & { label: string; color: string };

function ComparisonTooltip({ active, label, data, series, metric }: {
  active?: boolean;
  label?: string;
  data: ComparisonPoint[];
  series: DisplaySeries[];
  metric: ComparisonMetric;
}) {
  const { t } = useTranslation();
  const row = data.find((point) => point.t === label);
  if (!active || !row) return null;
  const incomplete = metric === "cost" && series.some((item) => !isCostCoverageComplete(row.measurements[item.id]));
  return (
    <div role="tooltip" className="max-w-[min(24rem,85vw)] rounded-lg border bg-popover px-3 py-2 text-popover-foreground shadow-md">
      <p className="mb-1 text-[11px] text-muted-foreground">{formatChartDateTime(row.t)}</p>
      {series.map((item) => {
        const point = row.measurements[item.id];
        return (
          <div key={item.id} className="flex items-center gap-2 text-xs">
            <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: item.color }} />
            <span className="min-w-0 truncate text-muted-foreground" title={item.label}>{item.label}</span>
            <span className="ml-auto shrink-0 pl-2 font-medium tabular-nums">
              {metric === "cost" ? formatCoveredCostShort(point.v, point) : formatCompactNumber(point.v)}
            </span>
          </div>
        );
      })}
      {incomplete ? <p className="mt-1 text-[11px] text-muted-foreground">{t("apiKeys.trend.knownCostOnly")}</p> : null}
    </div>
  );
}

export type ApiComparisonTrendProps = {
  data?: ApiKeysTrendsResponse;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
};

export function ApiComparisonTrend({ data, loading, error, onRetry }: ApiComparisonTrendProps) {
  const { t } = useTranslation();
  const [metric, setMetric] = useState<ComparisonMetric>("cost");
  const [mode, setMode] = useState<ComparisonMode>("hourly");
  const [hidden, setHidden] = useState<Set<string>>(() => new Set());
  const theme = useThemeStore((state) => state.theme);
  const reducedMotion = useReducedMotion();
  const series = useMemo(() => {
    const source = data?.series ?? [];
    const identities = source.map(comparisonSeriesId).sort();
    const palette = buildDonutPalette(identities.length + 1, theme === "dark");
    const colors = new Map(identities.map((id, index) => [id, palette[index]]));
    return selectComparisonSeries(source, metric, hidden).map((item) => ({
      ...item,
      label: item.kind === "other" ? t("apiKeys.trend.other")
        : item.kind === "deleted" ? t("apiKeys.trend.deleted") : item.name!,
      color: item.kind === "other" ? palette[identities.length] : colors.get(item.id)!,
    }));
  }, [data, metric, hidden, t, theme]);
  const points = useMemo(() => buildComparisonPoints(series, metric, mode), [series, metric, mode]);
  const dayTicks = useMemo(() => points.filter((point, index) => index === 0 || point.t.slice(0, 10) !== points[index - 1].t.slice(0, 10))
    .map((point) => point.t), [points]);
  const visible = series.filter((item) => !hidden.has(item.id));
  const incomplete = metric === "cost" && visible.some((item) => item.points.some((point) => !isCostCoverageComplete(point)));
  const Chart = mode === "cumulative" ? LineChart : AreaChart;
  const Series = mode === "cumulative" ? Line : Area;

  function toggleSeries(id: string) {
    setHidden((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="min-w-0 rounded-xl border bg-card p-4" data-testid="api-keys-comparison-trend">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{t("apiKeys.trend.title")}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {t(metric === "cost" ? "apiKeys.trend.costSubtitle" : "apiKeys.trend.tokensSubtitle")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ChartToggle<ComparisonMetric>
            label={t("apiKeys.trend.metric")}
            value={metric}
            options={[{ value: "cost", label: t("apiKeys.trend.cost") }, { value: "tokens", label: t("apiKeys.trend.tokens") }]}
            onChange={setMetric}
          />
          <ChartToggle<ComparisonMode>
            label={t("apiKeys.trend.mode")}
            value={mode}
            options={[{ value: "hourly", label: t("apiKeys.trend.hourly") }, { value: "cumulative", label: t("apiKeys.trend.cumulative") }]}
            onChange={setMode}
          />
        </div>
      </div>

      {error ? (
        <div role="alert" className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-destructive">
          {t("apiKeys.trend.error")}
          <Button variant="outline" size="sm" onClick={onRetry}>{t("common.actions.retry")}</Button>
        </div>
      ) : null}
      {loading ? (
        <div role="status" aria-label={t("apiKeys.trend.loading")}><Skeleton className="h-[280px] w-full" /></div>
      ) : !data && error ? null : points.length === 0 || visible.length === 0 ? (
        <div className="flex h-[280px] items-center justify-center text-xs text-muted-foreground">
          {t(points.length === 0 ? "apiKeys.trend.empty" : "apiKeys.trend.hidden")}
        </div>
      ) : (
        <div role="img" aria-label={t("apiKeys.trend.chartLabel", { metric: t(`apiKeys.trend.${metric}`), mode: t(`apiKeys.trend.${mode}`) })}>
          <ResponsiveContainer width="100%" height={280}>
            <Chart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" opacity={0.06} />
              <XAxis dataKey="t" ticks={dayTicks} tickFormatter={(value: string) => value.slice(5, 10)}
                tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} minTickGap={50} dy={4} />
              <YAxis domain={[0, "auto"]} width={56} tickFormatter={metric === "cost" ? formatCurrency : formatCompactNumber}
                tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} />
              <Tooltip content={<ComparisonTooltip data={points} series={visible} metric={metric} />}
                filterNull={false} allowEscapeViewBox={{ x: false, y: false }} cursor={{ stroke: "var(--border)", strokeWidth: 1 }} />
              {visible.map((item) => (
                <Series key={item.id} name={item.id} dataKey={(row: ComparisonPoint) => row.values[item.id]}
                  type={mode === "cumulative" ? "stepAfter" : "linear"}
                  stroke={item.color} strokeWidth={1.5} fill={item.color} fillOpacity={0.15}
                  dot={false} connectNulls={false} activeDot={{ r: 3, strokeWidth: 1.5 }}
                  isAnimationActive={!reducedMotion} animationDuration={500} />
              ))}
            </Chart>
          </ResponsiveContainer>
        </div>
      )}

      {series.length > 0 ? (
        <div role="group" aria-label={t("apiKeys.trend.legend")} className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
          {series.map((item) => (
            <button key={item.id} type="button" aria-pressed={!hidden.has(item.id)} title={item.label}
              onClick={() => toggleSeries(item.id)}
              className={cn("flex min-w-0 max-w-full items-center gap-1.5 rounded-sm text-xs focus-visible:outline-2 focus-visible:outline-ring", hidden.has(item.id) && "text-muted-foreground line-through opacity-50")}>
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: item.color }} />
              <span className="max-w-56 truncate">{item.label}</span>
            </button>
          ))}
        </div>
      ) : null}
      {incomplete ? <p className="sr-only">{t("apiKeys.trend.knownCostOnly")}</p> : null}
    </div>
  );
}
