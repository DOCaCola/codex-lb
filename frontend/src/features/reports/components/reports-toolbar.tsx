import { useId } from "react";
import { LayoutList, RefreshCw, RotateCcw } from "lucide-react";
import { useTranslation } from "react-i18next";

import { ChartToggle } from "@/components/chart-toggle";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  MultiSelectFilter,
  type MultiSelectOption,
} from "@/features/dashboard/components/filters/multi-select-filter";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { getTimeFormatPreference } from "@/hooks/use-time-format";
import { getIntlLocale } from "@/utils/formatters";

import { formatReportRange, isReportDateRangeValid, localDateISO } from "../date";
import type { ReportsFilterState } from "../hooks/use-reports";
import {
  REPORT_SECTION_DEFINITIONS,
  type ReportSectionId,
} from "../hooks/use-report-sections";
import { previousWindow } from "../report-model";
import { RANGE_PRESETS, type RangePreset } from "../report-range";

export type ReportsToolbarProps = {
  filters: ReportsFilterState;
  preset: RangePreset;
  accountOptions: MultiSelectOption[];
  apiKeyOptions: MultiSelectOption[];
  modelOptions: MultiSelectOption[];
  useragentOptions: MultiSelectOption[];
  /** Whether the report compares against the previous window. */
  showComparison: boolean;
  generatedAt: string | undefined;
  refreshing: boolean;
  visibleSectionIds: ReportSectionId[];
  onPresetChange: (preset: RangePreset) => void;
  onFiltersChange: (filters: ReportsFilterState) => void;
  onRefresh: () => void;
  onSectionVisibleChange: (id: ReportSectionId, visible: boolean) => void;
};

function hasActiveReportFilters(filters: ReportsFilterState): boolean {
  return (
    filters.accounts.length > 0 ||
    filters.apiKeyIds.length > 0 ||
    filters.models.length > 0 ||
    filters.useragents.length > 0
  );
}

function formatGeneratedTime(iso: string): string {
  return new Intl.DateTimeFormat(getIntlLocale(), {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: getTimeFormatPreference() === "12h" ? "h12" : "h23",
  }).format(new Date(iso));
}

export function ReportsToolbar({
  filters,
  preset,
  accountOptions,
  apiKeyOptions,
  modelOptions,
  useragentOptions,
  showComparison,
  generatedAt,
  refreshing,
  visibleSectionIds,
  onPresetChange,
  onFiltersChange,
  onRefresh,
  onSectionVisibleChange,
}: ReportsToolbarProps) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
  const dateRangeErrorId = useId();
  const today = localDateISO();
  const rangeValid = isReportDateRangeValid(filters.startDate, filters.endDate);
  const rangeComplete = rangeValid && Boolean(filters.startDate && filters.endDate);
  const startDateMax = filters.endDate && filters.endDate < today ? filters.endDate : today;
  const filtersActive = hasActiveReportFilters(filters);
  const previous = rangeComplete ? previousWindow(filters.startDate, filters.endDate) : null;

  return (
    <section
      aria-label={t("reports.toolbar.label")}
      className="sticky top-[4.25rem] z-10 space-y-2 rounded-xl border bg-card/95 p-3 backdrop-blur supports-[backdrop-filter]:bg-card/85"
    >
      <div className="flex flex-wrap items-center gap-3">
        <ChartToggle
          label={t("reports.toolbar.range")}
          value={preset}
          onChange={onPresetChange}
          options={[
            ...RANGE_PRESETS.map((value) => ({ value, label: value })),
            { value: "custom" as const, label: t("reports.toolbar.custom") },
          ]}
        />
        {preset === "custom" ? (
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <input
                type="date"
                name="report-start-date"
                autoComplete="off"
                aria-label={t("reports.filters.startDate")}
                aria-invalid={!rangeValid || undefined}
                aria-describedby={rangeValid ? undefined : dateRangeErrorId}
                max={startDateMax}
                value={filters.startDate}
                onChange={(event) => onFiltersChange({ ...filters, startDate: event.target.value })}
                className="h-8 rounded-md border bg-transparent px-2 text-xs text-foreground aria-invalid:border-destructive aria-invalid:ring-destructive/20"
              />
              <span aria-hidden="true" className="text-xs text-muted-foreground">
                –
              </span>
              <input
                type="date"
                name="report-end-date"
                autoComplete="off"
                aria-label={t("reports.filters.endDate")}
                aria-invalid={!rangeValid || undefined}
                aria-describedby={rangeValid ? undefined : dateRangeErrorId}
                min={filters.startDate || undefined}
                max={today}
                value={filters.endDate}
                onChange={(event) => onFiltersChange({ ...filters, endDate: event.target.value })}
                className="h-8 rounded-md border bg-transparent px-2 text-xs text-foreground aria-invalid:border-destructive aria-invalid:ring-destructive/20"
              />
            </div>
            {rangeValid ? null : (
              <p id={dateRangeErrorId} aria-live="polite" className="text-xs text-destructive">
                {t("reports.filters.invalidDateRange")}
              </p>
            )}
          </div>
        ) : rangeComplete ? (
          <span className="text-sm font-medium tabular-nums" data-testid="reports-range-label">
            {formatReportRange(filters.startDate, filters.endDate, dateDisplayFormat)}
          </span>
        ) : null}
        {showComparison && previous ? (
          <span className="text-xs text-muted-foreground">
            {t("reports.toolbar.comparedWith", {
              range: formatReportRange(previous.startDate, previous.endDate, dateDisplayFormat, { withYear: false }),
            })}
          </span>
        ) : null}
        <span className="flex-1" />
        {generatedAt ? (
          <span className="text-xs tabular-nums text-muted-foreground">
            {t("reports.toolbar.updated", { time: formatGeneratedTime(generatedAt) })}
          </span>
        ) : null}
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing || !rangeValid}
          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
          aria-label={t("reports.toolbar.refresh")}
          title={t("reports.toolbar.refresh")}
        >
          <RefreshCw className={`h-4 w-4${refreshing ? " animate-spin" : ""}`} aria-hidden="true" />
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <MultiSelectFilter
          label={t("reports.filters.accounts")}
          values={filters.accounts}
          options={accountOptions}
          onChange={(accounts) => onFiltersChange({ ...filters, accounts })}
        />
        <MultiSelectFilter
          label={t("reports.filters.apiKeys")}
          values={filters.apiKeyIds}
          options={apiKeyOptions}
          onChange={(apiKeyIds) => onFiltersChange({ ...filters, apiKeyIds })}
        />
        <MultiSelectFilter
          label={t("reports.filters.models")}
          values={filters.models}
          options={modelOptions}
          onChange={(models) => onFiltersChange({ ...filters, models })}
        />
        <MultiSelectFilter
          label={t("reports.filters.userAgents")}
          values={filters.useragents}
          options={useragentOptions}
          onChange={(useragents) => onFiltersChange({ ...filters, useragents })}
        />
        {filtersActive ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-xs text-muted-foreground"
            onClick={() => onFiltersChange({ ...filters, accounts: [], apiKeyIds: [], models: [], useragents: [] })}
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            {t("common.actions.reset")}
          </Button>
        ) : null}
        <span className="flex-1" />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button type="button" variant="outline" size="sm" className="h-8">
              <LayoutList className="mr-2 h-4 w-4" aria-hidden="true" />
              {t("reports.toolbar.sections", { visible: visibleSectionIds.length })}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>{t("reports.toolbar.visibleSections")}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {REPORT_SECTION_DEFINITIONS.map(({ id, labelKey }) => (
              <DropdownMenuCheckboxItem
                key={id}
                checked={visibleSectionIds.includes(id)}
                onCheckedChange={(checked) => onSectionVisibleChange(id, checked === true)}
                onSelect={(event) => event.preventDefault()}
              >
                {t(labelKey)}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </section>
  );
}
