import { useTranslation } from "react-i18next";

import { AlertMessage } from "@/components/alert-message";
import { Button } from "@/components/ui/button";
import { SpinnerBlock } from "@/components/ui/spinner";
import { cacheBand, type CacheBand } from "@/features/dashboard/cache-band";
import { useConversationTrace } from "@/features/dashboard/hooks/use-conversation-trace";
import { requestTypeLabel } from "@/features/dashboard/request-operation";
import type { ConversationTraceRequest } from "@/features/dashboard/schemas";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { cn } from "@/lib/utils";
import {
  formatCompactNumber,
  formatDateTimeInline,
  formatElapsed,
  formatModelLabel,
  formatTimeLong,
} from "@/utils/formatters";

const BAND_CLASSES: Record<CacheBand, string> = {
  high: "bg-emerald-500/70",
  mid: "bg-amber-500/70",
  low: "bg-red-500/70",
  none: "bg-muted-foreground/30",
};

export function ConversationTrace({ conversationId, enabled }: { conversationId: string; enabled: boolean }) {
  const { t } = useTranslation();
  const traceQuery = useConversationTrace(conversationId, enabled);
  const requests = traceQuery.data?.pages.flatMap((page) => page.requests) ?? [];
  const total = traceQuery.data?.pages[0]?.total ?? 0;
  const longest = Math.max(1, ...requests.map((request) => request.latencyMs ?? 0));

  return (
    <section data-testid="conversation-trace" className="space-y-2">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-medium">{t("dashboard.conversations.trace.title")}</h3>
        {requests.length > 0 ? (
          <span className="text-xs text-muted-foreground tabular-nums">
            {t("dashboard.conversations.trace.shown", { shown: requests.length, total })}
          </span>
        ) : null}
      </div>
      <p className="text-xs text-muted-foreground">{t("dashboard.conversations.trace.caption")}</p>
      {traceQuery.isPending ? (
        <div className="rounded-md border bg-muted/30 py-6">
          <SpinnerBlock />
        </div>
      ) : traceQuery.error ? (
        <div role="alert">
          <AlertMessage variant="error">
            {traceQuery.error instanceof Error ? traceQuery.error.message : t("dashboard.conversations.errorDescription")}
          </AlertMessage>
        </div>
      ) : (
        <>
          <ol className="divide-y rounded-md border">
            {requests.map((request) => (
              <TraceRow key={request.id} request={request} longest={longest} />
            ))}
          </ol>
          {traceQuery.hasNextPage ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void traceQuery.fetchNextPage()}
              disabled={traceQuery.isFetchingNextPage}
            >
              {t("dashboard.conversations.trace.loadMore")}
            </Button>
          ) : null}
        </>
      )}
    </section>
  );
}

function TraceRow({ request, longest }: { request: ConversationTraceRequest; longest: number }) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
  const band = cacheBand(request.cacheReadRatio);
  const width = Math.max(2, ((request.latencyMs ?? 0) / longest) * 100);
  const type = requestTypeLabel(request, t);
  const failed = request.status !== "success";
  return (
    <li
      data-testid="conversation-trace-row"
      className="grid grid-cols-[4.5rem_minmax(8rem,14rem)_minmax(6rem,1fr)_7.5rem_4.5rem] items-center gap-3 px-3 py-1.5 text-xs"
    >
      <span
        className="font-mono tabular-nums text-muted-foreground"
        title={formatDateTimeInline(request.requestedAt, dateDisplayFormat)}
      >
        {formatTimeLong(request.requestedAt, dateDisplayFormat).time}
      </span>
      <span className="min-w-0 truncate">
        <span className="font-mono" translate="no">{formatModelLabel(request.model, request.reasoningEffort)}</span>
        {type ? <span className="ml-1.5 text-muted-foreground">{type}</span> : null}
      </span>
      <span className="flex min-w-0 items-center gap-2">
        <span className="h-2.5 min-w-0 flex-1 rounded-sm bg-muted/50">
          <span
            data-band={band}
            className={cn("block h-full rounded-sm", BAND_CLASSES[band], failed && "ring-1 ring-red-500")}
            style={{ width: `${width}%` }}
          />
        </span>
        {request.cacheEvent ? (
          <span
            className="shrink-0 rounded border px-1 font-mono text-[10px] text-muted-foreground"
            title={t(`dashboard.conversations.trace.events.${request.cacheEvent}.description`, {
              gap: formatElapsed(request.idleGapMs),
            })}
          >
            {t(`dashboard.conversations.trace.events.${request.cacheEvent}.label`)}
          </span>
        ) : null}
        {failed ? (
          <span className="shrink-0 font-mono text-[10px] text-red-600 dark:text-red-400">
            {request.errorCode ?? request.status}
          </span>
        ) : null}
      </span>
      <span className="text-right font-mono tabular-nums">
        {request.cacheReadRatio === null
          ? "—"
          : t("dashboard.conversations.trace.cached", {
              percent: Math.round(request.cacheReadRatio * 100),
              prompt: formatCompactNumber(request.promptTokens),
            })}
      </span>
      <span className="text-right font-mono tabular-nums text-muted-foreground">{formatElapsed(request.latencyMs)}</span>
    </li>
  );
}
