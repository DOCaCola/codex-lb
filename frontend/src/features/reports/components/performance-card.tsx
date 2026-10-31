import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "@/components/lazy-recharts";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";

import { formatReportDay } from "../date";
import { formatMilliseconds, formatTokensPerSecond } from "../report-format";
import { capOutliers, median } from "../report-model";
import type { ReportSeriesStyles } from "../report-series-styles";
import type { DailyReportRow, ReportsResponse } from "../schemas";
import { ReportEmptyState, ReportSection } from "./report-section";

const CHART_HEIGHT = 120;
/** Room above the highest regular point for an outlier's label. */
const SCALE_HEADROOM = 1.25;

type SpeedMetric = {
  id: "ttft" | "tps" | "queue";
  field: "medianTtftMs" | "medianTps" | "medianQueueMs";
  format: (value: number) => string;
  paletteIndex: number;
  /** A day without a timed request reports 0, which is a missing sample rather than an instant answer. */
  zeroIsMissing: boolean;
};

const SPEED_METRICS: SpeedMetric[] = [
  { id: "ttft", field: "medianTtftMs", format: formatMilliseconds, paletteIndex: 3, zeroIsMissing: true },
  { id: "tps", field: "medianTps", format: formatTokensPerSecond, paletteIndex: 2, zeroIsMissing: true },
  { id: "queue", field: "medianQueueMs", format: formatMilliseconds, paletteIndex: 1, zeroIsMissing: false },
];

export type PerformanceCardProps = {
  report: ReportsResponse;
  styles: ReportSeriesStyles;
};

export function PerformanceCard({ report, styles }: PerformanceCardProps) {
  const { t } = useTranslation();
  const days = useMemo(() => [...report.daily].sort((left, right) => left.date.localeCompare(right.date)), [report.daily]);

  return (
    <ReportSection title={t("reports.sections.perf")} hint={t("reports.perf.hint")} testId="reports-perf">
      {report.speedMetricsAvailable === false ? (
        <p className="px-4 pb-4 pt-2 text-sm text-muted-foreground">
          {t("reports.speedUnavailable", { days: report.speedMetricsMaxDays ?? 7 })}
        </p>
      ) : days.length === 0 ? (
        <ReportEmptyState />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3">
          {SPEED_METRICS.map((metric) => (
            <SpeedChart key={metric.id} metric={metric} days={days} color={styles.palette[metric.paletteIndex]} />
          ))}
        </div>
      )}
    </ReportSection>
  );
}

type SpeedPoint = { date: string; plotted: number | null; value: number | null; outlier: boolean };

function SpeedChart({ metric, days, color }: { metric: SpeedMetric; days: DailyReportRow[]; color: string }) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
  const label = t(`reports.perf.${metric.id}`);
  const { points, scaleMax, headline } = useMemo(() => {
    const values = days.map((day) => {
      const value = day[metric.field] ?? 0;
      return value > 0 || !metric.zeroIsMissing ? value : null;
    });
    const capped = capOutliers(values);
    return {
      scaleMax: capped.scaleMax,
      headline: median(values.filter((value): value is number => value !== null)),
      points: days.map(
        (day, index): SpeedPoint => ({
          date: day.date,
          value: values[index],
          outlier: capped.outliers[index],
          plotted: capped.outliers[index] ? capped.scaleMax : values[index],
        }),
      ),
    };
  }, [days, metric]);

  return (
    <div className="border-t px-4 pb-3 pt-3 first:border-t-0 lg:border-l lg:border-t-0 lg:first:border-l-0" data-testid={`reports-perf-${metric.id}`}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-lg font-semibold tabular-nums text-foreground">
          {headline === null ? "—" : metric.format(headline)}
        </span>
      </div>
      <div style={{ height: CHART_HEIGHT }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 18, right: 10, bottom: 0, left: 10 }}>
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              fontSize={11}
              minTickGap={6}
              interval="preserveStartEnd"
              tickFormatter={(date: string) => formatReportDay(date, dateDisplayFormat, "short")}
            />
            <YAxis hide domain={[0, scaleMax > 0 ? scaleMax * SCALE_HEADROOM : 1]} />
            <Tooltip
              cursor={{ stroke: "var(--border)" }}
              content={(props: TooltipContentProps<number, string>) => (
                <SpeedTooltip
                  {...props}
                  label={label}
                  format={metric.format}
                  dateLabel={(date) => formatReportDay(date, dateDisplayFormat)}
                />
              )}
            />
            <Line
              dataKey="plotted"
              type="linear"
              stroke={color}
              strokeWidth={2}
              connectNulls
              isAnimationActive={false}
              dot={(props: SpeedDotProps) => (
                <SpeedDot key={props.index} {...props} lastIndex={points.length - 1} color={color} format={metric.format} />
              )}
              activeDot={{ r: 4, fill: color }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

type SpeedDotProps = { cx?: number; cy?: number; index?: number; payload?: SpeedPoint };

/** A regular point, or an outlier pinned to the top edge with its real value. */
function SpeedDot({
  cx,
  cy,
  index,
  lastIndex,
  payload,
  color,
  format,
}: SpeedDotProps & { lastIndex: number; color: string; format: (value: number) => string }) {
  if (cx === undefined || cy === undefined || !payload || payload.value === null) return null;
  if (!payload.outlier) {
    return <circle cx={cx} cy={cy} r={3} fill="var(--card)" stroke={color} strokeWidth={2} />;
  }
  // Labels on the first and last day grow inward so the chart edge does not clip them.
  const anchor = index === 0 ? "start" : index === lastIndex ? "end" : "middle";
  const labelX = anchor === "start" ? cx - 5 : anchor === "end" ? cx + 5 : cx;
  return (
    <g data-testid="reports-perf-outlier">
      <path d={`M${cx - 5},${cy + 3} L${cx},${cy - 4} L${cx + 5},${cy + 3} Z`} fill={color} />
      <text x={labelX} y={cy - 8} textAnchor={anchor} fontSize={10} fill="var(--muted-foreground)">
        {`${format(payload.value)} ↑`}
      </text>
    </g>
  );
}

type SpeedTooltipProps = TooltipContentProps<number, string> & {
  format: (value: number) => string;
  dateLabel: (date: string) => string;
};

function SpeedTooltip({ active, payload, label, format, dateLabel }: SpeedTooltipProps) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload as SpeedPoint;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
      <div className="mb-1 font-semibold">{dateLabel(point.date)}</div>
      <div className="flex gap-4">
        <span className="text-muted-foreground">{String(label)}</span>
        <span className="ml-auto font-medium tabular-nums">{point.value === null ? "—" : format(point.value)}</span>
      </div>
    </div>
  );
}
