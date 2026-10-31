import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ChartToggle } from "@/components/chart-toggle";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "@/components/lazy-recharts";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { usePrivacyStore } from "@/hooks/use-privacy";

import { calendarDays } from "../daily-series";
import { formatReportDay } from "../date";
import { formatMetricTick, formatMetricValue } from "../report-format";
import {
  metricValue,
  OTHER_SERIES_KEY,
  seriesDataKey,
  stackTopGroups,
  totalSeriesParts,
  totalSeriesValue,
  type StackedRow,
  type TrendMetric,
  type TrendSplit,
} from "../report-model";
import { UNATTRIBUTED_ACCOUNT_KEY, type ReportSeriesStyles, type SeriesStyle } from "../report-series-styles";
import type { ReportsResponse } from "../schemas";
import { ReportEmptyState, ReportSection } from "./report-section";
import { SeriesMarker } from "./series-marker";

const TOP_SERIES = 5;
const CHART_HEIGHT = 260;

export type DailyTrendCardProps = {
  report: ReportsResponse;
  startDate: string;
  endDate: string;
  styles: ReportSeriesStyles;
};

type PlottedSeries = SeriesStyle & { dataKey: string; blur: boolean };

export function DailyTrendCard({ report, startDate, endDate, styles }: DailyTrendCardProps) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
  const blurred = usePrivacyStore((state) => state.blurred);
  const [metric, setMetric] = useState<TrendMetric>("cost");
  const [split, setSplit] = useState<TrendSplit>("account");

  const { series, rows } = useMemo(() => {
    const days = calendarDays(startDate, endDate);
    if (split === "total") {
      const byDate = new Map(report.daily.map((row) => [row.date, row]));
      const parts = totalSeriesParts(metric);
      return {
        series: parts.map((part, index): PlottedSeries => ({
          dataKey: part,
          label: t(`reports.trend.parts.${part === "value" ? metric : part}`),
          color: part === "cachedInput" ? styles.neutral : styles.palette[index],
          provider: null,
          blur: false,
        })),
        rows: days.map((date) => {
          const day = byDate.get(date);
          const row: StackedRow = { date };
          for (const part of parts) row[part] = day ? totalSeriesValue(day, metric, part) : 0;
          return row;
        }),
      };
    }
    const groupStyles = new Map<string, SeriesStyle & { blur: boolean }>();
    const points =
      split === "account"
        ? report.dailyByAccount.map((entry) => {
            const style = styles.account(entry);
            const group = style.filterKey ?? UNATTRIBUTED_ACCOUNT_KEY;
            groupStyles.set(group, { ...style, blur: style.filterKey !== null });
            return { group, date: entry.date, value: metricValue(entry, metric) };
          })
        : report.dailyByModel.map((entry) => {
            groupStyles.set(entry.model, { ...styles.model(entry.model), blur: false });
            return { group: entry.model, date: entry.date, value: metricValue(entry, metric) };
          });
    const stacked = stackTopGroups(points, days, TOP_SERIES);
    const plotted: PlottedSeries[] = stacked.groups.map((group, index) => ({
      ...(groupStyles.get(group) as SeriesStyle & { blur: boolean }),
      dataKey: seriesDataKey(index),
    }));
    if (stacked.hasOther) {
      plotted.push({
        dataKey: OTHER_SERIES_KEY,
        label: t("reports.trend.other"),
        color: styles.neutral,
        provider: null,
        blur: false,
      });
    }
    return { series: plotted, rows: stacked.rows };
  }, [endDate, metric, report, split, startDate, styles, t]);

  return (
    <ReportSection
      title={t("reports.sections.trend")}
      testId="reports-trend"
      actions={
        <>
          <ChartToggle
            label={t("reports.trend.metric")}
            value={metric}
            onChange={setMetric}
            options={(["cost", "input", "output", "requests"] as const).map((value) => ({
              value,
              label: t(`reports.trend.metrics.${value}`),
            }))}
          />
          <span className="flex-1" />
          <span className="text-xs text-muted-foreground">{t("reports.trend.splitBy")}</span>
          <ChartToggle
            label={t("reports.trend.splitBy")}
            value={split}
            onChange={setSplit}
            options={(["total", "account", "model"] as const).map((value) => ({
              value,
              label: t(`reports.trend.splits.${value}`),
            }))}
          />
        </>
      }
    >
      {report.daily.length === 0 ? (
        <ReportEmptyState />
      ) : (
        <>
          <div className="px-2 pt-2" style={{ height: CHART_HEIGHT }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap="22%">
                <CartesianGrid vertical={false} stroke="var(--border)" strokeOpacity={0.6} />
                <XAxis
                  dataKey="date"
                  tickLine={false}
                  axisLine={false}
                  fontSize={11}
                  minTickGap={8}
                  tickFormatter={(date: string) => formatReportDay(date, dateDisplayFormat, "short")}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  fontSize={11}
                  width={60}
                  tickFormatter={(value: number) => formatMetricTick(metric, value)}
                />
                <Tooltip
                  cursor={{ fill: "var(--accent)", opacity: 0.5 }}
                  content={(props: TooltipContentProps<number, string>) => (
                    <TrendTooltip
                      {...props}
                      series={series}
                      metric={metric}
                      dateLabel={(date) => formatReportDay(date, dateDisplayFormat)}
                      blurred={blurred}
                    />
                  )}
                />
                {series.map((entry, index) => (
                  <Bar
                    key={entry.dataKey}
                    dataKey={entry.dataKey}
                    name={entry.label}
                    stackId="trend"
                    fill={entry.color}
                    maxBarSize={56}
                    isAnimationActive={false}
                    radius={index === series.length - 1 ? [3, 3, 0, 0] : 0}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 px-4 pb-4 pt-1 text-xs text-muted-foreground" data-testid="reports-trend-legend">
            {series.map((entry) => (
              <li key={entry.dataKey} className="inline-flex items-center gap-1.5">
                <SeriesMarker style={entry} />
                <span className={blurred && entry.blur ? "privacy-blur" : undefined}>{entry.label}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </ReportSection>
  );
}

type TrendTooltipProps = TooltipContentProps<number, string> & {
  series: PlottedSeries[];
  metric: TrendMetric;
  dateLabel: (date: string) => string;
  blurred: boolean;
};

function TrendTooltip({ active, payload, label, series, metric, dateLabel, blurred }: TrendTooltipProps) {
  const { t } = useTranslation();
  if (!active || !payload?.length) return null;
  const row = payload[0].payload as StackedRow;
  const present = series.filter((entry) => (row[entry.dataKey] as number) > 0).reverse();
  const total = series.reduce((sum, entry) => sum + (row[entry.dataKey] as number), 0);
  return (
    <div className="min-w-52 rounded-lg border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
      <div className="mb-1.5 flex justify-between gap-4 font-semibold">
        <span>{dateLabel(String(label))}</span>
        <span className="tabular-nums">{formatMetricValue(metric, total)}</span>
      </div>
      {present.length === 0 ? (
        <div className="text-muted-foreground">{t("reports.empty.title")}</div>
      ) : (
        present.map((entry) => (
          <div key={entry.dataKey} className="flex items-center gap-2 py-0.5">
            <SeriesMarker style={entry} />
            <span className={blurred && entry.blur ? "privacy-blur" : undefined}>{entry.label}</span>
            <span className="ml-auto pl-3 font-medium tabular-nums">
              {formatMetricValue(metric, row[entry.dataKey] as number)}
            </span>
          </div>
        ))
      )}
    </div>
  );
}
