import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { AlertMessage } from "@/components/alert-message";
import { Button } from "@/components/ui/button";
import { getRequestLogOptions } from "@/features/dashboard/api";
import { useReports, useReportsOptions, useThreadIdentity, type ReportsFilterState } from "@/features/reports/hooks/use-reports";
import { useReportSections } from "@/features/reports/hooks/use-report-sections";
import { getErrorMessageOrNull } from "@/utils/errors";

import { daysAgoLocalISO, getBrowserReportsTimeZone, isReportDateRangeValid, localDateISO } from "../date";
import { PRESET_DAYS, type RangePreset } from "../report-range";
import { useReportSeriesStyles } from "../report-series-styles";
import { BreakdownSection, type BreakdownFilterKind } from "./breakdown-section";
import { DailyDetailTable } from "./daily-detail-table";
import { DailyTrendCard } from "./daily-trend-card";
import { PerformanceCard } from "./performance-card";
import { ReportsSummaryCards } from "./reports-summary-cards";
import { ReportsToolbar } from "./reports-toolbar";
import { RoutingDiagnosticsCard } from "./routing-diagnostics-card";
import { SeriesMarker } from "./series-marker";

const REPORTS_TIMEZONE_REFRESH_INTERVAL_MS = 60_000;
const DEFAULT_PRESET = "7d" satisfies RangePreset;

function presetRange(days: number): Pick<ReportsFilterState, "startDate" | "endDate"> {
  return { startDate: daysAgoLocalISO(days - 1), endDate: localDateISO() };
}

export type ReportsPageProps = {
  initialFilters?: Partial<ReportsFilterState>;
};

export function ReportsPage({ initialFilters }: ReportsPageProps = {}) {
  const { t } = useTranslation();
  const [filters, setFilters] = useState<ReportsFilterState>(() => ({
    ...presetRange(PRESET_DAYS[DEFAULT_PRESET]),
    accounts: [],
    apiKeyIds: [],
    models: [],
    useragents: [],
    ...initialFilters,
  }));
  const [preset, setPreset] = useState<RangePreset>(() =>
    initialFilters?.startDate || initialFilters?.endDate ? "custom" : DEFAULT_PRESET,
  );
  const [reportsTimeZone, setReportsTimeZone] = useState<string | undefined>(() => getBrowserReportsTimeZone());
  const { visibleSectionIds, setSectionVisible } = useReportSections();
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false);

  useEffect(() => {
    const refreshReportsTimeZone = () => {
      setReportsTimeZone((current) => {
        const next = getBrowserReportsTimeZone();
        return current === next ? current : next;
      });
    };
    const intervalId = window.setInterval(refreshReportsTimeZone, REPORTS_TIMEZONE_REFRESH_INTERVAL_MS);
    window.addEventListener("focus", refreshReportsTimeZone);
    document.addEventListener("visibilitychange", refreshReportsTimeZone);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", refreshReportsTimeZone);
      document.removeEventListener("visibilitychange", refreshReportsTimeZone);
    };
  }, []);

  const isVisible = (id: (typeof visibleSectionIds)[number]) => visibleSectionIds.includes(id);
  const diagnosticsActive = diagnosticsOpen && isVisible("diagnostics");
  const reportsQuery = useReports(filters, reportsTimeZone);
  const optionsQuery = useReportsOptions(filters, reportsTimeZone);
  const threadIdentityQuery = useThreadIdentity(filters, reportsTimeZone, diagnosticsActive);
  const apiKeysQuery = useQuery({
    queryKey: ["request-log-options", "reports-filter"],
    queryFn: () => getRequestLogOptions(),
  });
  const report = reportsQuery.data;
  const styles = useReportSeriesStyles(report);

  const accountOptions = useMemo(
    () =>
      (optionsQuery.data?.accounts ?? []).flatMap((identity) => {
        const series = styles.account(identity);
        return series.filterKey
          ? [{ value: series.filterKey, label: series.label, isEmail: true, icon: <SeriesMarker style={series} /> }]
          : [];
      }),
    [optionsQuery.data, styles],
  );
  const apiKeyOptions = useMemo(
    () =>
      (apiKeysQuery.data?.apiKeys ?? []).map((key) => ({
        value: key.id,
        label: key.keyPrefix ? `${key.name} · ${key.keyPrefix}` : key.name,
      })),
    [apiKeysQuery.data],
  );
  const modelOptions = useMemo(
    () => (optionsQuery.data?.models ?? []).map((model) => ({ value: model, label: model })),
    [optionsQuery.data],
  );
  const useragentOptions = useMemo(
    () => (optionsQuery.data?.useragents ?? []).map((useragent) => ({ value: useragent, label: useragent })),
    [optionsQuery.data],
  );

  const rangeValid = isReportDateRangeValid(filters.startDate, filters.endDate);
  const reportError = getErrorMessageOrNull(reportsQuery.error);
  const optionsError = getErrorMessageOrNull(optionsQuery.error);
  const apiKeysError = getErrorMessageOrNull(apiKeysQuery.error);

  const handleRetry = async () => {
    if (!rangeValid) {
      await apiKeysQuery.refetch();
      return;
    }
    await Promise.allSettled([
      reportsQuery.refetch(),
      optionsQuery.refetch(),
      apiKeysQuery.refetch(),
      ...(diagnosticsActive ? [threadIdentityQuery.refetch()] : []),
    ]);
  };

  const handleRefresh = () => {
    void Promise.allSettled([
      reportsQuery.refetch(),
      optionsQuery.refetch(),
      ...(diagnosticsActive ? [threadIdentityQuery.refetch()] : []),
    ]);
  };

  const handlePresetChange = (next: RangePreset) => {
    setPreset(next);
    if (next !== "custom") {
      setFilters((current) => ({ ...current, ...presetRange(PRESET_DAYS[next]) }));
    }
  };

  const handleFiltersChange = (next: ReportsFilterState) => {
    if (next.startDate !== filters.startDate || next.endDate !== filters.endDate) {
      setPreset("custom");
    }
    setFilters(next);
  };

  const handleBreakdownToggle = (kind: BreakdownFilterKind, value: string) => {
    setFilters((current) => {
      const field = kind === "accounts" ? "accounts" : kind === "models" ? "models" : "useragents";
      const values = current[field];
      return {
        ...current,
        [field]: values.includes(value) ? values.filter((entry) => entry !== value) : [...values, value],
      };
    });
  };

  const retryButton = (
    <Button type="button" variant="outline" size="sm" onClick={() => void handleRetry()}>
      {t("common.actions.retry")}
    </Button>
  );

  return (
    <div className="flex flex-col gap-4" data-testid="reports-page">
      <ReportsToolbar
        filters={filters}
        preset={preset}
        accountOptions={accountOptions}
        apiKeyOptions={apiKeyOptions}
        modelOptions={modelOptions}
        useragentOptions={useragentOptions}
        showComparison={report?.comparison.canCompare ?? false}
        generatedAt={report?.generatedAt}
        refreshing={reportsQuery.isFetching || optionsQuery.isFetching}
        visibleSectionIds={visibleSectionIds}
        onPresetChange={handlePresetChange}
        onFiltersChange={handleFiltersChange}
        onRefresh={handleRefresh}
        onSectionVisibleChange={setSectionVisible}
      />

      {reportError ? <AlertMessage variant="error">{t("reports.errors.data", { error: reportError })}</AlertMessage> : null}
      {optionsError ? (
        <div className="flex items-center justify-between gap-2">
          <AlertMessage variant="error" className="flex-1">
            {t("reports.errors.options", { error: optionsError })}
          </AlertMessage>
          {retryButton}
        </div>
      ) : null}
      {apiKeysError ? (
        <div className="flex items-center justify-between gap-2">
          <AlertMessage variant="error" className="flex-1">
            {t("reports.errors.apiKeys", { error: apiKeysError })}
          </AlertMessage>
          {retryButton}
        </div>
      ) : null}

      {reportsQuery.isLoading ? (
        <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">{t("common.loading")}</div>
      ) : report ? (
        <>
          <ReportsSummaryCards summary={report.summary} comparison={report.comparison} />
          {isVisible("trend") ? (
            <DailyTrendCard report={report} startDate={filters.startDate} endDate={filters.endDate} styles={styles} />
          ) : null}
          {isVisible("breakdown") ? (
            <BreakdownSection
              report={report}
              styles={styles}
              selected={{ accounts: filters.accounts, models: filters.models, useragents: filters.useragents }}
              onToggle={handleBreakdownToggle}
            />
          ) : null}
          {isVisible("perf") ? <PerformanceCard report={report} styles={styles} /> : null}
          {isVisible("table") ? (
            <DailyDetailTable
              startDate={filters.startDate}
              endDate={filters.endDate}
              data={report.daily}
              summary={report.summary}
            />
          ) : null}
          {isVisible("diagnostics") ? (
            <RoutingDiagnosticsCard
              open={diagnosticsOpen}
              onOpenChange={setDiagnosticsOpen}
              data={threadIdentityQuery.data}
              error={getErrorMessageOrNull(threadIdentityQuery.error)}
            />
          ) : null}
        </>
      ) : reportError || optionsError || apiKeysError ? (
        <div className="space-y-3 rounded-xl border bg-card p-4">
          <AlertMessage variant="warning">{t("reports.errors.partial")}</AlertMessage>
          {retryButton}
        </div>
      ) : null}
    </div>
  );
}
