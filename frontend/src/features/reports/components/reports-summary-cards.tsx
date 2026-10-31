import type { ReactNode } from "react";
import { Info } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  formatCoveredCost,
  formatCoveredCostShort,
  isCostCoverageComplete,
} from "@/features/dashboard/cost-coverage";
import { formatCurrency, formatNumber } from "@/utils/formatters";

import { formatCompact, formatShare } from "../report-format";
import type { ReportComparison, ReportSummary } from "../schemas";

export type ReportsSummaryCardsProps = {
  summary: ReportSummary;
  comparison: ReportComparison;
};

type SummaryCard = {
  id: string;
  label: string;
  value: ReactNode;
  /** Shown as a native tooltip on the info marker. */
  details?: string;
  delta?: Delta;
  sub?: string;
};

export function ReportsSummaryCards({ summary, comparison }: ReportsSummaryCardsProps) {
  const { t } = useTranslation();
  const totalTokens = summary.totalInputTokens + summary.totalOutputTokens;
  const cards: SummaryCard[] = [
    {
      id: "cost",
      label: t("reports.summary.cost"),
      value: formatCoveredCostShort(summary.totalCostUsd, summary),
      details: formatCoveredCost(summary.totalCostUsd, summary),
      delta: buildDelta(
        summary.totalCostUsd,
        comparison.previous.totalCostUsd,
        comparison.canCompare && isCostCoverageComplete(summary) && isCostCoverageComplete(comparison.previous),
        formatCurrency,
      ),
      sub: t("reports.summary.perDay", { value: formatCurrency(summary.avgCostPerDay) }),
    },
    {
      id: "tokens",
      label: t("reports.summary.tokens"),
      value: formatCompact(totalTokens),
      details: t("reports.summary.tokensDetails", {
        input: formatNumber(summary.totalInputTokens),
        cached: formatNumber(summary.totalCachedTokens),
        output: formatNumber(summary.totalOutputTokens),
        reasoning: formatNumber(summary.totalReasoningTokens),
        known: formatNumber(summary.reasoningUsageKnownRequests),
        total: formatNumber(summary.totalRequests),
      }),
      delta: buildDelta(totalTokens, comparison.previous.totalTokens, comparison.canCompare, formatCompact),
      sub:
        summary.totalInputTokens > 0
          ? t("reports.summary.tokensSub", {
              cached: formatShare(summary.totalCachedTokens / summary.totalInputTokens),
              output: formatCompact(summary.totalOutputTokens),
            })
          : undefined,
    },
    {
      id: "requests",
      label: t("reports.summary.requests"),
      value: formatNumber(summary.totalRequests),
      delta: buildDelta(summary.totalRequests, comparison.previous.totalRequests, comparison.canCompare, formatNumber),
      sub: t("reports.summary.requestsSub", {
        perDay: formatNumber(Math.round(summary.avgRequestsPerDay)),
        accounts: formatNumber(summary.activeAccounts),
      }),
    },
    {
      id: "conversations",
      label: t("reports.summary.conversations"),
      value: formatNumber(summary.totalConversations),
      sub:
        summary.totalConversations > 0
          ? t("reports.summary.conversationsSub", {
              requests: formatNumber(Math.round(summary.totalRequests / summary.totalConversations)),
            })
          : undefined,
    },
    {
      id: "errors",
      label: t("reports.summary.errors"),
      value: (
        <>
          {formatNumber(summary.totalErrors)}
          {summary.totalRequests > 0 ? (
            <span className="text-xs font-medium text-muted-foreground">
              {formatShare(summary.totalErrors / summary.totalRequests, 2)}
            </span>
          ) : null}
        </>
      ),
      sub:
        summary.totalRequests > 0
          ? t("reports.summary.errorsSub", {
              cancelled: formatNumber(summary.totalCancelled),
              share: formatShare(summary.totalCancelled / summary.totalRequests),
            })
          : undefined,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      {cards.map((card) => (
        <div
          key={card.id}
          data-testid={`report-summary-card-${card.id}`}
          className="flex min-h-[6.5rem] flex-col gap-1 rounded-xl border bg-card px-4 py-3.5"
        >
          <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            {card.label}
            {card.details ? (
              <span
                role="img"
                aria-label={card.details}
                title={card.details}
                className="inline-flex cursor-help normal-case"
                data-testid={`report-summary-details-${card.id}`}
              >
                <Info className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
            ) : null}
          </div>
          <div className="flex items-baseline gap-2 text-[1.625rem] font-semibold tracking-[-0.02em] tabular-nums text-foreground">
            {card.value}
            {card.delta ? (
              <span className="whitespace-nowrap text-xs font-medium text-muted-foreground" title={card.delta.title}>
                {card.delta.text}
              </span>
            ) : null}
          </div>
          {card.sub ? <div className="text-xs tabular-nums text-muted-foreground">{card.sub}</div> : null}
        </div>
      ))}
    </div>
  );

  function buildDelta(
    current: number,
    previous: number,
    canCompare: boolean,
    format: (value: number) => string,
  ): Delta | undefined {
    if (!canCompare || previous <= 0) {
      return undefined;
    }
    const percent = Math.round((Math.abs(current - previous) / previous) * 100);
    if (percent === 0) {
      return undefined;
    }
    return {
      // Change is reported, not judged: a rise in cost or traffic is neither good nor bad by itself.
      text: `${current > previous ? "▲" : "▼"} ${percent}%`,
      title: t("reports.summary.previousWindow", { value: format(previous) }),
    };
  }
}

type Delta = { text: string; title: string };
