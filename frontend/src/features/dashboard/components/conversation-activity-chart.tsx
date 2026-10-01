import { useTranslation } from "react-i18next";
import type { TooltipContentProps } from "recharts";
import type { z } from "zod";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "@/components/lazy-recharts";
import type { ConversationAnalyticsSchema } from "@/features/dashboard/schemas";
import { ChartTooltip } from "@/features/reports/components/chart-tooltip";
import { useChartColors } from "@/hooks/use-chart-colors";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { formatDateTimeInline } from "@/utils/formatters";

export function ConversationActivityChart({
  analytics,
}: {
  analytics: z.infer<typeof ConversationAnalyticsSchema>;
}) {
  const { t } = useTranslation();
  const dateFormat = useDateDisplayFormatStore(
    (state) => state.dateDisplayFormat,
  );
  const colors = useChartColors();
  const counts = new Map(
    analytics.activity.map((item) => [
      new Date(item.at).getTime(),
      item.requests,
    ]),
  );
  const start =
    Math.floor(new Date(analytics.start).getTime() / 3_600_000) * 3_600_000;
  const end = new Date(analytics.end).getTime();
  const data = [];
  for (let at = start; at < end; at += 3_600_000)
    data.push({ at, requests: counts.get(at) ?? 0 });
  return (
    <section
      aria-label={t("dashboard.conversations.analytics.activity")}
      className="rounded-md border bg-card p-3"
    >
      <h3 className="text-sm font-medium">
        {t("dashboard.conversations.analytics.activity")}
      </h3>
      <p className="text-xs text-muted-foreground">
        {formatDateTimeInline(analytics.start, dateFormat)} –{" "}
        {formatDateTimeInline(analytics.end, dateFormat)}
      </p>
      <div className="mt-2 h-28">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <CartesianGrid
              vertical={false}
              strokeDasharray="3 3"
              stroke="var(--border)"
            />
            <XAxis
              dataKey="at"
              tickFormatter={(value: number) =>
                new Date(value).toLocaleDateString()
              }
              minTickGap={60}
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              allowDecimals={false}
              width={30}
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              content={(props: TooltipContentProps<number, string>) =>
                props.active && props.label != null ? (
                  <ChartTooltip
                    {...props}
                    label={formatDateTimeInline(
                      new Date(Number(props.label)).toISOString(),
                      dateFormat,
                    )}
                  />
                ) : null
              }
            />
            <Area
              dataKey="requests"
              name={t("dashboard.conversations.analytics.requests")}
              type="stepAfter"
              stroke={colors[0]}
              fill={colors[0]}
              fillOpacity={0.15}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
