import { ChevronRight } from "lucide-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";

import { AlertMessage } from "@/components/alert-message";
import { SpinnerBlock } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { formatNumber } from "@/utils/formatters";

import { formatCompact, formatShare } from "../report-format";
import type { ThreadIdentityResponse } from "../schemas";

export type RoutingDiagnosticsCardProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  data: ThreadIdentityResponse | undefined;
  error: string | null;
};

export function RoutingDiagnosticsCard({ open, onOpenChange, data, error }: RoutingDiagnosticsCardProps) {
  const { t } = useTranslation();
  const bodyId = useId();
  const keyed = data?.available ? data.keyed : null;

  return (
    <section className="rounded-xl border bg-card" data-testid="reports-diagnostics" aria-label={t("reports.sections.diagnostics")}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => onOpenChange(!open)}
        className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3.5 text-left"
      >
        <ChevronRight
          className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-90")}
          aria-hidden="true"
        />
        <h2 className="text-sm font-semibold text-foreground">{t("reports.sections.diagnostics")}</h2>
        <span className="text-xs text-muted-foreground">{t("reports.diagnostics.hint")}</span>
        {keyed ? (
          <span className="ml-auto flex flex-wrap gap-x-4 text-xs text-muted-foreground" data-testid="reports-diagnostics-stats">
            <span>
              <b className="font-semibold tabular-nums text-foreground">{keyed.meanAccountsPerConversation.toFixed(2)}</b>{" "}
              {t("reports.diagnostics.stats.accountsPerConversation")}
            </span>
            <span>
              <b className="font-semibold tabular-nums text-foreground">{formatShare(keyed.accountSwitchRate)}</b>{" "}
              {t("reports.diagnostics.stats.switchRate")}
            </span>
            <span>
              <b className="font-semibold tabular-nums text-foreground">{formatShare(keyed.cacheHitRatio)}</b>{" "}
              {t("reports.diagnostics.stats.cacheHit")}
            </span>
          </span>
        ) : null}
      </button>
      {open ? (
        <div id={bodyId} className="px-4 pb-4">
          {error ? (
            <AlertMessage variant="error">{t("reports.errors.diagnostics", { error })}</AlertMessage>
          ) : !data ? (
            <SpinnerBlock />
          ) : !data.available ? (
            <p className="text-sm text-muted-foreground">{t("reports.diagnostics.unavailable", { days: data.maxDays })}</p>
          ) : (
            <DiagnosticsBody data={data} />
          )}
        </div>
      ) : null}
    </section>
  );
}

function DiagnosticsBody({ data }: { data: ThreadIdentityResponse }) {
  const { t } = useTranslation();
  const keyed = data.keyed;
  const tiles = [
    {
      id: "accounts-per-conversation",
      label: t("reports.diagnostics.tiles.accountsPerConversation"),
      value: keyed.meanAccountsPerConversation.toFixed(2),
      detail: t("reports.diagnostics.details.accountsPerConversation", {
        conversations: formatNumber(keyed.conversations),
        requests: data.conversationMinRequests,
      }),
    },
    {
      id: "single-account",
      label: t("reports.diagnostics.tiles.singleAccount"),
      value: formatShare(keyed.singleAccountConversationShare),
      detail: t("reports.diagnostics.details.singleAccount"),
    },
    {
      id: "switch-rate",
      label: t("reports.diagnostics.tiles.switchRate"),
      value: formatShare(keyed.accountSwitchRate),
      detail: t("reports.diagnostics.details.switchRate", {
        turns: formatNumber(keyed.turns),
        minutes: Math.round(data.switchMaxGapSeconds / 60),
      }),
    },
    {
      id: "cache-hit",
      label: t("reports.diagnostics.tiles.cacheHit"),
      value: formatShare(keyed.cacheHitRatio),
      detail: t("reports.diagnostics.details.cacheHit", { tokens: formatCompact(keyed.cacheSampleInputTokens) }),
    },
  ];
  // Deleted accounts detach their history, which pulls the spread figures down; disclose it.
  const unattributedShare =
    data.totalRequests > 0
      ? (keyed.unattributedRequestShare * keyed.requests +
          data.unkeyed.unattributedRequestShare * data.unkeyed.requests) /
        data.totalRequests
      : 0;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {tiles.map((tile) => (
        <div key={tile.id} className="rounded-lg border p-3" data-testid={`reports-diagnostics-${tile.id}`}>
          <div className="text-xs text-muted-foreground">{tile.label}</div>
          <div className="mb-0.5 mt-1 text-xl font-semibold tabular-nums text-foreground">{tile.value}</div>
          <div className="text-[11.5px] text-muted-foreground">{tile.detail}</div>
        </div>
      ))}
      <p className="col-span-full text-xs leading-relaxed text-muted-foreground" data-testid="reports-diagnostics-note">
        {t("reports.diagnostics.note.keyed", {
          share: formatShare(keyed.requestShare),
          unkeyed: formatNumber(data.unkeyed.requests),
        })}
        {unattributedShare > 0 ? ` ${t("reports.diagnostics.note.unattributed", { share: formatShare(unattributedShare) })}` : ""}
      </p>
    </div>
  );
}
