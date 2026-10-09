import { lazy, Suspense } from "react";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { get } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { useChartColors } from "@/hooks/use-chart-colors";

const Chart = lazy(() => import("./account-trend-chart").then((m) => ({ default: m.AccountSeriesChart })));
const schema = z.object({ series: z.array(z.object({
  key: z.string(), label: z.string(), points: z.array(z.object({ t: z.string(), v: z.number().nullable() })),
  dashed: z.boolean(), colorIndex: z.number().int().nonnegative(),
})) });

type TrendProvider = "openrouter" | "claude" | "openai_compatible";

const TRENDS_COLLECTION: Record<TrendProvider, string> = {
  openrouter: "/api/openrouter-accounts",
  claude: "/api/claude-accounts",
  openai_compatible: "/api/model-sources",
};

const ACTIVITY_SCOPE: Record<Exclude<TrendProvider, "claude">, { label: string; note: string }> = {
  openrouter: { label: "OpenRouter activity", note: "Other OpenRouter activity is not included" },
  openai_compatible: { label: "Provider activity", note: "Requests sent to this provider by other clients are not included" },
};

export function ProviderAccountTrends({ provider, accountId, embedded = false }: { provider: TrendProvider; accountId: string; embedded?: boolean }) {
  const colors = useChartColors();
  const query = useQuery({
    queryKey: ["provider-account-trends", provider, accountId],
    queryFn: ({ signal }) => get(`${TRENDS_COLLECTION[provider]}/${encodeURIComponent(accountId)}/trends`, schema, { signal }),
    refetchInterval: 60000,
  });
  const activity = provider === "claude" ? null : ACTIVITY_SCOPE[provider];
  const quota = activity === null;
  return <section className={embedded ? "min-w-0" : "rounded-xl border bg-card p-5"} aria-label={activity?.label ?? "Claude quota history"}>
    <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {quota ? "Quota remaining · 7 days" : "Request activity · 7 days"}
      </h4>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
        {query.data?.series.map((s) => <span key={s.key} className="flex items-center gap-1.5">
          <span className={s.dashed ? "inline-block h-0 w-4 border-t border-dashed" : "inline-block h-2 w-2 rounded-full"}
            style={s.dashed ? { borderColor: colors[s.colorIndex % colors.length] } : { backgroundColor: colors[s.colorIndex % colors.length] }} />
          {s.label}
        </span>)}
      </div>
    </div>
    {query.isPending ? <div className="flex h-[200px] items-center justify-center text-xs text-muted-foreground" role="status">Loading history…</div>
      : query.isError ? <div className="flex h-[200px] items-center justify-center gap-2 text-xs text-muted-foreground" role="alert">
        Unable to load history. <Button variant="outline" size="sm" onClick={() => void query.refetch()}>Retry</Button>
      </div> : <Suspense fallback={<div className="h-[220px]" />}>
        <Chart series={query.data.series} percentage={quota} />
      </Suspense>}
    <p className="mt-2 text-xs text-muted-foreground">
      {activity ? `Hourly requests recorded by codex-lb, including errors. ${activity.note}; history depends on log retention.`
        : "Hourly averages of observed quota. Gaps mean no observations. Weekly plan is an even-consumption guideline based on recorded reset deadlines, not reported quota."}
    </p>
  </section>;
}
