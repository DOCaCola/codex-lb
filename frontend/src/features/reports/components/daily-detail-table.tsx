import { useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, Download } from "lucide-react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { CoveredCost } from "@/features/dashboard/components/covered-cost";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { cn } from "@/lib/utils";
import { formatNumber } from "@/utils/formatters";

import { buildContinuousDailyRows } from "../daily-series";
import { formatReportDay } from "../date";
import { formatCompact, formatMilliseconds, formatShare, formatTokensPerSecond } from "../report-format";
import type { DailyReportRow, ReportSummary } from "../schemas";
import { ReportSection } from "./report-section";

export type DailyDetailTableProps = {
  startDate: string;
  endDate: string;
  data: DailyReportRow[];
  summary: ReportSummary;
};

type SortKey =
  | "date"
  | "requests"
  | "conversations"
  | "inputTokens"
  | "outputTokens"
  | "reasoningTokens"
  | "costUsd"
  | "errorCount"
  | "cancelledCount"
  | "activeAccounts"
  | "medianTtftMs"
  | "medianTps";
type SortDirection = "asc" | "desc";

type Column = {
  key: SortKey;
  label: string;
  group?: string;
  cell: (row: DailyReportRow) => ReactNode;
  total: ReactNode;
};

function InputTokens({ input, cached }: { input: number; cached: number }) {
  const { t } = useTranslation();
  if (input === 0) return <>0</>;
  return (
    <>
      {formatCompact(input)}
      <span className="ml-1 text-[11.5px] text-muted-foreground">
        {t("reports.table.cachedShare", { share: formatShare(cached / input, 0) })}
      </span>
    </>
  );
}

function Errors({ errors, requests }: { errors: number; requests: number }) {
  return (
    <>
      {formatNumber(errors)}
      {requests > 0 ? (
        <span className="ml-1 text-[11.5px] text-muted-foreground">{formatShare(errors / requests)}</span>
      ) : null}
    </>
  );
}

const speedCell = (value: number | undefined, format: (value: number) => string) =>
  value && value > 0 ? format(value) : "—";

export function DailyDetailTable({ startDate, endDate, data, summary }: DailyDetailTableProps) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
  const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({ key: "date", direction: "desc" });
  const days = buildContinuousDailyRows(startDate, endDate, data);
  const rows = sortRows(days, sort);

  const columns: Column[] = [
    {
      key: "date",
      label: t("reports.table.day"),
      cell: (row) => formatReportDay(row.date, dateDisplayFormat),
      total: t("reports.table.total"),
    },
    {
      key: "requests",
      label: t("reports.table.requests"),
      cell: (row) => formatNumber(row.requests),
      total: formatNumber(summary.totalRequests),
    },
    {
      key: "conversations",
      label: t("reports.table.conversations"),
      cell: (row) => formatNumber(row.conversations),
      total: formatNumber(summary.totalConversations),
    },
    {
      key: "inputTokens",
      label: t("reports.table.input"),
      group: t("reports.table.tokens"),
      cell: (row) => <InputTokens input={row.inputTokens} cached={row.cachedInputTokens} />,
      total: <InputTokens input={summary.totalInputTokens} cached={summary.totalCachedTokens} />,
    },
    {
      key: "outputTokens",
      label: t("reports.table.output"),
      group: t("reports.table.tokens"),
      cell: (row) => formatCompact(row.outputTokens),
      total: formatCompact(summary.totalOutputTokens),
    },
    {
      key: "reasoningTokens",
      label: t("reports.table.reasoning"),
      group: t("reports.table.tokens"),
      cell: (row) => (row.reasoningTokens == null ? "—" : formatCompact(row.reasoningTokens)),
      total: formatCompact(summary.totalReasoningTokens),
    },
    {
      key: "costUsd",
      label: t("reports.table.cost"),
      cell: (row) => <CoveredCost costUsd={row.costUsd} coverage={row} />,
      total: <CoveredCost costUsd={summary.totalCostUsd} coverage={summary} />,
    },
    {
      key: "errorCount",
      label: t("reports.table.errors"),
      cell: (row) => <Errors errors={row.errorCount} requests={row.requests} />,
      total: <Errors errors={summary.totalErrors} requests={summary.totalRequests} />,
    },
    {
      key: "cancelledCount",
      label: t("reports.table.cancelled"),
      cell: (row) => formatNumber(row.cancelledCount),
      total: formatNumber(summary.totalCancelled),
    },
    {
      key: "activeAccounts",
      label: t("reports.table.accounts"),
      cell: (row) => formatNumber(row.activeAccounts),
      total: formatNumber(summary.activeAccounts),
    },
    {
      key: "medianTtftMs",
      label: t("reports.table.ttft"),
      group: t("reports.table.median"),
      cell: (row) => speedCell(row.medianTtftMs, formatMilliseconds),
      total: null,
    },
    {
      key: "medianTps",
      label: t("reports.table.tps"),
      group: t("reports.table.median"),
      cell: (row) => speedCell(row.medianTps, formatTokensPerSecond),
      total: null,
    },
  ];

  const toggleSort = (key: SortKey) => {
    setSort((current) =>
      current.key === key
        ? { key, direction: current.direction === "asc" ? "desc" : "asc" }
        : { key, direction: "desc" },
    );
  };

  return (
    <ReportSection
      title={t("reports.sections.table")}
      hint={t("reports.table.hint")}
      testId="reports-table"
      actions={
        <>
          <span className="flex-1" />
          <Button
            variant="outline"
            size="sm"
            className="h-7 gap-1 text-xs"
            onClick={() => exportCSV(sortRows(days, { key: "date", direction: "asc" }), t)}
          >
            <Download className="h-3 w-3" aria-hidden="true" />
            {t("reports.table.csv")}
          </Button>
        </>
      }
    >
      <div className="overflow-x-auto pb-1.5 pt-1">
        <table className="w-full border-collapse text-[13px] tabular-nums">
          <thead>
            <tr className="border-b">
              {columns.map((column, index) => {
                const active = sort.key === column.key;
                const Icon = sort.direction === "asc" ? ArrowUp : ArrowDown;
                return (
                  <th
                    key={column.key}
                    scope="col"
                    aria-sort={active ? (sort.direction === "asc" ? "ascending" : "descending") : "none"}
                    className={cn(
                      "whitespace-nowrap px-3 py-2 font-medium",
                      index === 0 ? "pl-4 text-left" : "text-right",
                      index === columns.length - 1 && "pr-4",
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => toggleSort(column.key)}
                      className={cn(
                        "inline-flex flex-col gap-0.5 text-[11.5px]",
                        index === 0 ? "items-start" : "items-end",
                        active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      <span className="text-[10px] uppercase tracking-wider opacity-70">{column.group ?? "\u00a0"}</span>
                      <span className="inline-flex items-center gap-1">
                        {column.label}
                        {active ? <Icon className="h-3 w-3" aria-hidden="true" data-testid={`sort-icon-${sort.direction}`} /> : null}
                      </span>
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.date} data-testid={`daily-breakdown-row-${row.date}`} className="border-b border-border/60 hover:bg-accent/50">
                {columns.map((column, index) => (
                  <td
                    key={column.key}
                    className={cn(
                      "whitespace-nowrap px-3 py-2",
                      index === 0 ? "pl-4 text-left font-medium" : "text-right",
                      index === columns.length - 1 && "pr-4",
                    )}
                  >
                    {column.cell(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr data-testid="daily-breakdown-total" className="font-semibold">
              {columns.map((column, index) => (
                <td
                  key={column.key}
                  className={cn(
                    "whitespace-nowrap px-3 py-2",
                    index === 0 ? "pl-4 text-left" : "text-right",
                    index === columns.length - 1 && "pr-4",
                  )}
                >
                  {column.total}
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>
    </ReportSection>
  );
}

function sortRows(rows: DailyReportRow[], sort: { key: SortKey; direction: SortDirection }): DailyReportRow[] {
  const factor = sort.direction === "asc" ? 1 : -1;
  return [...rows].sort((left, right) => {
    const leftValue = left[sort.key];
    const rightValue = right[sort.key];
    if (leftValue == null || rightValue == null) {
      return leftValue == null ? (rightValue == null ? 0 : 1) : -1;
    }
    return leftValue < rightValue ? -factor : leftValue > rightValue ? factor : 0;
  });
}

function exportCSV(rows: DailyReportRow[], t: TFunction) {
  const headers = [
    t("reports.table.csvColumns.date"),
    t("reports.table.csvColumns.requests"),
    t("reports.table.csvColumns.conversations"),
    t("reports.table.csvColumns.inputTokens"),
    t("reports.table.csvColumns.cachedTokens"),
    t("reports.table.csvColumns.outputTokens"),
    t("reports.table.csvColumns.reasoningTokens"),
    t("reports.table.csvColumns.costUsd"),
    t("reports.table.csvColumns.pricedRequests"),
    t("reports.table.csvColumns.unpricedRequests"),
    t("reports.table.csvColumns.unmeteredRequests"),
    t("reports.table.csvColumns.coverageUnknown"),
    t("reports.table.csvColumns.errors"),
    t("reports.table.csvColumns.cancelled"),
    t("reports.table.csvColumns.activeAccounts"),
    t("reports.table.csvColumns.medianTtftMs"),
    t("reports.table.csvColumns.medianTps"),
  ];
  const lines = rows.map((row) =>
    [
      row.date,
      row.requests,
      row.conversations,
      row.inputTokens,
      row.cachedInputTokens,
      row.outputTokens,
      row.reasoningTokens ?? "",
      row.costUsd.toFixed(4),
      row.pricedRequests ?? 0,
      row.unpricedRequests ?? 0,
      row.unmeteredRequests ?? 0,
      row.coverageUnknown ? "true" : "false",
      row.errorCount,
      row.cancelledCount,
      row.activeAccounts,
      row.medianTtftMs ?? 0,
      row.medianTps ?? 0,
    ].join(","),
  );
  const blob = new Blob([[headers.join(","), ...lines].join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `reports-${rows[0]?.date ?? "data"}-${rows[rows.length - 1]?.date ?? "data"}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
