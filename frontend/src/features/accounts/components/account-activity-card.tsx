import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ChartToggle } from "@/components/chart-toggle";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "@/components/lazy-recharts";
import { DetailCard } from "@/features/accounts/components/provider-detail";
import { useProviderActivity, type ActivityDay } from "@/features/accounts/hooks/use-provider-activity";
import { formatReportDay } from "@/features/reports/date";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { formatCompactNumber, formatCurrency, formatPercentNullable } from "@/utils/formatters";

type Metric = "cost" | "requests";

const metricValue = (day: ActivityDay, metric: Metric) => (metric === "cost" ? day.costUsd : day.requests);
const formatMetric = (metric: Metric, value: number) =>
  metric === "cost" ? formatCurrency(value) : formatCompactNumber(value);

/** Daily cost or requests of one account over the last seven days, with totals and a link to its logs. */
export function AccountActivityCard({
  activityKey,
  logsAccountId,
  color,
}: {
  activityKey: string;
  logsAccountId: string;
  color?: string;
}) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  const { activity, dates, available, isError } = useProviderActivity();
  const [metric, setMetric] = useState<Metric>("cost");
  if (!available) return null;
  const account = activity?.get(activityKey);
  const days = account?.days ?? dates.map((date) => ({ date, requests: 0, costUsd: 0, tokens: 0, cachedInputTokens: 0, inputTokens: 0, errors: 0, unpricedRequests: 0 }));
  const rows = days.map((day) => ({ date: day.date, value: metricValue(day, metric) }));
  const total = account?.total;
  const today = account?.today;
  const fill = color ?? "var(--primary)";
  const logsHref = `/logs?accountId=${encodeURIComponent(logsAccountId)}`;
  return (
    <DetailCard
      title={t("providers.activity.title")}
      data-testid="account-activity"
      action={
        <ChartToggle
          label={t("providers.activity.metric")}
          value={metric}
          onChange={setMetric}
          options={[
            { value: "cost", label: t("providers.activity.cost") },
            { value: "requests", label: t("providers.activity.requests") },
          ]}
        />
      }
    >
      {isError ? (
        <p role="alert" className="py-6 text-center text-xs text-muted-foreground">
          {t("providers.activity.unavailable")}
        </p>
      ) : activity === undefined ? (
        <div role="status" className="flex h-[180px] items-center justify-center text-xs text-muted-foreground">
          {t("providers.activity.loading")}
        </div>
      ) : (
        <div className="h-[180px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} margin={{ top: 6, right: 4, bottom: 0, left: 0 }} barCategoryGap="28%">
              <CartesianGrid vertical={false} stroke="var(--border)" strokeOpacity={0.6} />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                fontSize={11}
                tickFormatter={(date: string) => formatReportDay(date, dateDisplayFormat, "short")}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                fontSize={11}
                width={52}
                tickFormatter={(value: number) => formatMetric(metric, value)}
              />
              <Tooltip
                cursor={{ fill: "var(--accent)", opacity: 0.5 }}
                formatter={(value: number) => [formatMetric(metric, value), t(`providers.activity.${metric}`)]}
                labelFormatter={(date: string) => formatReportDay(date, dateDisplayFormat)}
                contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
              />
              <Bar dataKey="value" fill={fill} radius={[3, 3, 0, 0]} maxBarSize={44} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <dl className="-mx-4 -mb-4 mt-3 grid grid-cols-2 border-t sm:grid-cols-4 [&>div]:border-l [&>div]:px-4 [&>div]:py-3 [&>div:first-child]:border-l-0 max-sm:[&>div:nth-child(3)]:border-l-0 max-sm:[&>div:nth-child(n+3)]:border-t">
        <div>
          <dt className="text-xs text-muted-foreground">{t("providers.activity.requests")}</dt>
          <dd className="text-lg font-semibold tabular-nums">{formatCompactNumber(total?.requests ?? 0)}</dd>
          <dd className="text-[11px] text-muted-foreground">{t("providers.activity.today", { value: formatCompactNumber(today?.requests ?? 0) })}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">{t("providers.activity.estCost")}</dt>
          <dd className="text-lg font-semibold tabular-nums">{formatCurrency(total?.costUsd ?? 0)}</dd>
          <dd className="text-[11px] text-muted-foreground">{t("providers.activity.today", { value: formatCurrency(today?.costUsd ?? 0) })}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">{t("providers.activity.tokens")}</dt>
          <dd className="text-lg font-semibold tabular-nums">{formatCompactNumber(total?.tokens ?? 0)}</dd>
          <dd className="text-[11px] text-muted-foreground">
            {total && total.inputTokens > 0
              ? t("providers.activity.cached", { value: formatPercentNullable((total.cachedInputTokens / total.inputTokens) * 100) })
              : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">{t("providers.activity.errors")}</dt>
          <dd className="text-lg font-semibold tabular-nums">{formatCompactNumber(total?.errors ?? 0)}</dd>
          <dd className="text-[11px]">
            <Link to={logsHref} className="text-muted-foreground underline-offset-2 hover:text-foreground hover:underline">
              {t("providers.activity.openLogs")}
            </Link>
          </dd>
        </div>
      </dl>
    </DetailCard>
  );
}

