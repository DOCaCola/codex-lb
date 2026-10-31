import { useState } from "react";
import { Info } from "lucide-react";
import { useTranslation } from "react-i18next";

import { ChartToggle } from "@/components/chart-toggle";
import { formatCostCoverageNote, isCostCoverageComplete } from "@/features/dashboard/cost-coverage";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import { formatCurrency, formatNumber } from "@/utils/formatters";

import { formatShare } from "../report-format";
import type { BreakdownMetric } from "../report-model";
import type { ReportSeriesStyles, SeriesStyle } from "../report-series-styles";
import type { ReportsResponse } from "../schemas";
import { SeriesMarker } from "./series-marker";

export type BreakdownFilterKind = "accounts" | "models" | "useragents";

export type BreakdownSectionProps = {
  report: ReportsResponse;
  styles: ReportSeriesStyles;
  selected: Record<BreakdownFilterKind, readonly string[]>;
  onToggle: (kind: BreakdownFilterKind, value: string) => void;
};

type BreakdownRow = SeriesStyle & {
  id: string;
  /** Filter value toggled by the row; null when the row cannot be filtered on. */
  filterValue: string | null;
  costUsd: number;
  requests: number;
  blur: boolean;
};

export function BreakdownSection({ report, styles, selected, onToggle }: BreakdownSectionProps) {
  const { t } = useTranslation();
  const [metric, setMetric] = useState<BreakdownMetric>("cost");
  const coverageNote = metric === "cost" && !isCostCoverageComplete(report.summary)
    ? formatCostCoverageNote(report.summary)
    : null;

  const accounts: BreakdownRow[] = report.byAccount.map((entry, index) => {
    const style = styles.account(entry);
    return {
      ...style,
      id: style.filterKey ?? `unattributed-${index}`,
      filterValue: style.filterKey,
      costUsd: entry.costUsd,
      requests: entry.requests,
      blur: style.filterKey !== null,
    };
  });
  const models: BreakdownRow[] = report.byModel.map((entry) => ({
    ...styles.model(entry.model),
    id: entry.model,
    filterValue: entry.model,
    costUsd: entry.costUsd,
    requests: entry.requests,
    blur: false,
  }));
  const useragents: BreakdownRow[] = report.byUseragent.map((entry) => ({
    ...styles.useragent(entry.useragent),
    id: entry.useragent,
    filterValue: entry.useragent,
    costUsd: entry.costUsd,
    requests: entry.requests,
    blur: false,
  }));

  const lists: { kind: BreakdownFilterKind; title: string; rows: BreakdownRow[] }[] = [
    { kind: "accounts", title: t("reports.breakdown.accounts"), rows: accounts },
    { kind: "models", title: t("reports.breakdown.models"), rows: models },
    { kind: "useragents", title: t("reports.breakdown.userAgents"), rows: useragents },
  ];

  return (
    <section aria-label={t("reports.sections.breakdown")} data-testid="reports-breakdown" className="space-y-2">
      <div className="flex flex-wrap items-center gap-3 px-0.5">
        <h2 className="text-sm font-semibold text-foreground">{t("reports.sections.breakdown")}</h2>
        <ChartToggle
          label={t("reports.breakdown.metric")}
          value={metric}
          onChange={setMetric}
          options={[
            { value: "cost", label: t("reports.breakdown.cost") },
            { value: "requests", label: t("reports.breakdown.requests") },
          ]}
        />
        {coverageNote ? (
          <span
            role="img"
            aria-label={coverageNote}
            title={coverageNote}
            className="inline-flex cursor-help text-muted-foreground"
            data-testid="reports-breakdown-coverage"
          >
            <Info className="h-3.5 w-3.5" aria-hidden="true" />
          </span>
        ) : null}
        <span className="text-xs text-muted-foreground">{t("reports.breakdown.hint")}</span>
      </div>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {lists.map((list) => (
          <BreakdownList
            key={list.kind}
            title={list.title}
            kind={list.kind}
            rows={list.rows}
            metric={metric}
            selected={selected[list.kind]}
            onToggle={(value) => onToggle(list.kind, value)}
          />
        ))}
      </div>
    </section>
  );
}

function BreakdownList({
  title,
  kind,
  rows,
  metric,
  selected,
  onToggle,
}: {
  title: string;
  kind: BreakdownFilterKind;
  rows: BreakdownRow[];
  metric: BreakdownMetric;
  selected: readonly string[];
  onToggle: (value: string) => void;
}) {
  const { t } = useTranslation();
  const blurred = usePrivacyStore((state) => state.blurred);
  const valueOf = (row: BreakdownRow) => (metric === "cost" ? row.costUsd : row.requests);
  const sorted = [...rows].sort((left, right) => valueOf(right) - valueOf(left) || right.requests - left.requests);
  // Shares of the listed known subtotals, so they add up to 100% within the card.
  const total = sorted.reduce((sum, row) => sum + valueOf(row), 0);
  const max = Math.max(0, ...sorted.map(valueOf));

  return (
    <div className="rounded-xl border bg-card" data-testid={`reports-breakdown-${kind}`}>
      <h3 className="px-4 pt-3.5 text-sm font-semibold text-foreground">{title}</h3>
      {sorted.length === 0 ? (
        <p className="px-4 pb-4 pt-2 text-xs text-muted-foreground">{t("reports.empty.title")}</p>
      ) : (
        <ul className="px-2 pb-3 pt-1.5">
          {sorted.map((row) => {
            const value = valueOf(row);
            const isSelected = row.filterValue !== null && selected.includes(row.filterValue);
            const content = (
              <>
                <SeriesMarker style={row} />
                <span className={cn("truncate text-left text-[13px]", blurred && row.blur && "privacy-blur")} title={row.label}>
                  {row.label}
                </span>
                <span className="text-right text-[13px] font-medium tabular-nums">
                  {metric === "cost" ? formatCurrency(row.costUsd) : formatNumber(row.requests)}
                </span>
                <span className="text-right text-xs tabular-nums text-muted-foreground">
                  {total > 0 ? formatShare(value / total) : "—"}
                </span>
                <span className="col-start-2 col-end-5 h-1 overflow-hidden rounded-full bg-muted">
                  <span
                    className="block h-full rounded-full"
                    style={{
                      width: `${max > 0 ? Math.max(value > 0 ? 1 : 0, (value / max) * 100) : 0}%`,
                      backgroundColor: row.color,
                    }}
                  />
                </span>
                <span className="col-start-2 col-end-5 -mt-0.5 text-left text-[11.5px] tabular-nums text-muted-foreground">
                  {metric === "cost"
                    ? t("reports.breakdown.requestCount", { count: row.requests, formatted: formatNumber(row.requests) })
                    : formatCurrency(row.costUsd)}
                </span>
              </>
            );
            const rowClass =
              "grid w-full grid-cols-[1rem_minmax(0,1fr)_auto_3.25rem] items-center gap-x-2 gap-y-1 rounded-lg px-2 py-1.5";
            return (
              <li key={row.id}>
                {row.filterValue === null ? (
                  <div className={rowClass}>{content}</div>
                ) : (
                  <button
                    type="button"
                    aria-pressed={isSelected}
                    onClick={() => onToggle(row.filterValue as string)}
                    className={cn(
                      rowClass,
                      "cursor-pointer transition-colors hover:bg-accent",
                      isSelected && "bg-accent ring-1 ring-border",
                    )}
                  >
                    {content}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
