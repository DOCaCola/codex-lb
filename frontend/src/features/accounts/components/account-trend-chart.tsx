import { useId, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "@/components/lazy-recharts";

import { useChartColors } from "@/hooks/use-chart-colors";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import type { UsageTrendPoint } from "@/features/accounts/schemas";
import { formatChartDateTime } from "@/utils/formatters";

export type AccountChartSeries = {
  key: string;
  label: string;
  points: { t: string; v: number | null }[];
  dashed?: boolean;
  colorIndex?: number;
};

function mergeSeries(series: AccountChartSeries[]) {
  const times = [...new Set(series.flatMap((s) => s.points.map((p) => p.t)))].sort();
  const maps = series.map((s) => new Map(s.points.map((p) => [p.t, p.v])));
  return times.map((t) => Object.assign({ t }, ...series.map((s, i) => ({ [s.key]: maps[i].get(t) ?? null }))));
}

function formatXTick(isoStr: string): string {
  return isoStr.slice(5, 10);
}

type ChartTooltipPayloadEntry = {
  dataKey?: string | number;
  value?: number;
  color?: string;
};

type ChartTooltipProps = {
  active?: boolean;
  payload?: ChartTooltipPayloadEntry[];
  label?: string;
  series: AccountChartSeries[];
  percentage: boolean;
};

function CustomTooltip({ active, payload, label, series, percentage }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  const heading = formatChartDateTime(label as string);
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-popover-foreground shadow-md">
      <p className="mb-1 text-[11px] text-muted-foreground">{heading}</p>
      {payload.map((entry: ChartTooltipPayloadEntry) => {
        const meta = series.find((item) => item.key === entry.dataKey);
        return (
          <div key={entry.dataKey} className="flex items-center gap-2 text-xs">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-muted-foreground">{meta?.label}</span>
            <span className="ml-auto tabular-nums font-medium">{percentage ? `${entry.value?.toFixed(1)}%` : entry.value?.toLocaleString()}</span>
          </div>
        );
      })}
    </div>
  );
}

const CHART_MARGIN = { top: 4, right: 8, bottom: 0, left: 0 } as const;

export type AccountTrendChartProps = {
  primary: UsageTrendPoint[];
  secondary: UsageTrendPoint[];
  secondaryScheduled?: UsageTrendPoint[];
};

const EMPTY_TREND_POINTS: UsageTrendPoint[] = [];

export function AccountTrendChart({
  primary,
  secondary,
  secondaryScheduled = EMPTY_TREND_POINTS,
}: AccountTrendChartProps) {
  const { t } = useTranslation();
  return <AccountSeriesChart series={[
    { key: "primary", label: t("accounts.trend.series.primary", "Primary"), points: primary, colorIndex: 0 },
    { key: "secondary", label: t("accounts.trend.series.secondary", "Secondary"), points: secondary, colorIndex: 1 },
    { key: "secondaryScheduled", label: t("accounts.trend.series.secondaryScheduled", "Weekly plan"), points: secondaryScheduled, dashed: true, colorIndex: 1 },
  ]} />;
}

export function AccountSeriesChart({ series, percentage = true }: {
  series: AccountChartSeries[];
  percentage?: boolean;
}) {
  const { t } = useTranslation();
  const chartColors = useChartColors();
  const reducedMotion = useReducedMotion();
  const id = useId().replaceAll(":", "");
  const data = useMemo(() => mergeSeries(series), [series]);

  if (data.length === 0) {
    return (
      <div className="flex h-[200px] items-center justify-center text-xs text-muted-foreground">
        {t("accounts.trend.empty")}
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={CHART_MARGIN}>
        <defs>
          {series.map((s, i) => <linearGradient key={s.key} id={`${id}-${s.key}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={chartColors[(s.colorIndex ?? i) % chartColors.length]} stopOpacity={0.12} />
            <stop offset="100%" stopColor={chartColors[(s.colorIndex ?? i) % chartColors.length]} stopOpacity={0} />
          </linearGradient>)}
        </defs>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" opacity={0.06} />
        <XAxis
          dataKey="t"
          tickFormatter={formatXTick}
          tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
          tickLine={false}
          axisLine={false}
          minTickGap={50}
          dy={4}
        />
        <YAxis
          domain={percentage ? [0, 100] : [0, "auto"]}
          ticks={percentage ? [0, 25, 50, 75, 100] : undefined}
          allowDecimals={percentage}
          tickFormatter={(v: number) => percentage ? `${v}%` : v.toLocaleString()}
          tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
          tickLine={false}
          axisLine={false}
          width={38}
        />
        <Tooltip
          content={<CustomTooltip series={series} percentage={percentage} />}
          cursor={{ stroke: "hsl(var(--border))", strokeWidth: 1 }}
        />
        {series.filter((s) => s.points.length > 0).map((s, i) => s.dashed ? (
          <Line key={s.key} type="linear" dataKey={s.key}
            stroke={chartColors[(s.colorIndex ?? i) % chartColors.length]} strokeWidth={1.25} strokeDasharray="5 5"
            dot={false} connectNulls={false} isAnimationActive={!reducedMotion} animationDuration={500} />
        ) : (
          <Area key={s.key} type="monotone" dataKey={s.key}
            stroke={chartColors[(s.colorIndex ?? i) % chartColors.length]} strokeWidth={1.5}
            fill={`url(#${id}-${s.key})`} dot={s.points.filter((p) => p.v !== null).length === 1 ? { r: 3 } : false}
            activeDot={{ r: 3, strokeWidth: 1.5, fill: "hsl(var(--popover))" }}
            connectNulls={false} isAnimationActive={!reducedMotion} animationDuration={500} />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
