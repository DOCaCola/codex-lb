import type { DashboardStat } from "@/features/dashboard/utils";
import { cn } from "@/lib/utils";

const COMPARISON_STYLES = {
  positive: "text-emerald-600 dark:text-emerald-400",
  negative: "text-red-600 dark:text-red-400",
  neutral: "text-muted-foreground",
} as const;

const TREND_WIDTH = 200;
const TREND_HEIGHT = 26;

/** A stat's trend as a bare line scaled to its own range. */
function TrendLine({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return <div className="mt-1.5 h-[26px]" />;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const points = values.map(
    (value, index) =>
      (index / (values.length - 1)) * TREND_WIDTH + "," + (TREND_HEIGHT - 2 - ((value - min) / (max - min || 1)) * (TREND_HEIGHT - 4)),
  );
  return (
    <svg
      aria-hidden="true"
      viewBox={"0 0 " + TREND_WIDTH + " " + TREND_HEIGHT}
      preserveAspectRatio="none"
      className="mt-1.5 block h-[26px] w-full"
    >
      <polyline points={points.join(" ")} fill="none" stroke={color} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

/** Activity figures of the selected timeframe in one strip, divided into cells that wrap on narrow screens. */
export function ActivityStrip({ stats }: { stats: DashboardStat[] }) {
  return (
    <div className="@container/kpis overflow-hidden rounded-xl border bg-card shadow-xs" data-testid="activity-strip">
      <div className="-mt-px -ml-px grid grid-cols-2 @min-[33rem]/kpis:grid-cols-3 @min-[54rem]/kpis:auto-cols-fr @min-[54rem]/kpis:grid-flow-col @min-[54rem]/kpis:grid-cols-none">
        {stats.map((stat) => (
          <div key={stat.label} className="flex min-w-0 flex-col gap-0.5 border-t border-l px-4 pt-[13px] pb-2.5" data-testid="activity-stat">
            <span className="truncate text-xs text-muted-foreground" title={stat.description}>
              {stat.label}
            </span>
            <span className="flex min-w-0 items-baseline gap-2">
              <span className="truncate text-xl font-semibold tracking-[-0.01em] tabular-nums">
                {stat.value}
                {stat.unit ? <small className="ml-1 text-xs font-medium text-muted-foreground">{stat.unit}</small> : null}
              </span>
              {stat.comparison ? (
                <span className={cn("shrink-0 text-xs font-medium", COMPARISON_STYLES[stat.comparison.tone])}>{stat.comparison.text}</span>
              ) : null}
            </span>
            {stat.meta ? <span className="truncate text-[11.5px] text-muted-foreground tabular-nums">{stat.meta}</span> : null}
            <TrendLine values={stat.trend.map((point) => point.value)} color={stat.trendColor} />
          </div>
        ))}
      </div>
    </div>
  );
}
