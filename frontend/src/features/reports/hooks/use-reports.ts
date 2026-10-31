import { useQuery } from "@tanstack/react-query";

import { getReports, getReportsOptions, getThreadIdentity, type ReportsParams } from "../api";
import { isReportDateRangeValid } from "../date";
import { splitAccountFilterKeys } from "../report-model";

export type ReportsFilterState = {
  startDate: string;
  endDate: string;
  /** Account filter keys from accountFilterKey. */
  accounts: string[];
  apiKeyIds: string[];
  models: string[];
  useragents: string[];
};

const sorted = (values: readonly string[]) => [...values].sort();

/** Request scope shared by the report and its options; order-independent so reordering selections hits the cache. */
function accountScope(filters: ReportsFilterState, timeZone: string | undefined): ReportsParams {
  const { accountIds, modelSourceIds } = splitAccountFilterKeys(filters.accounts);
  return {
    startDate: filters.startDate,
    endDate: filters.endDate,
    timezone: timeZone,
    accountIds: sorted(accountIds),
    modelSourceIds: sorted(modelSourceIds),
    apiKeyIds: sorted(filters.apiKeyIds),
  };
}

const REPORT_QUERY_OPTIONS = {
  staleTime: 5 * 60_000,
  refetchInterval: false,
  refetchOnWindowFocus: false,
  retry: false,
} as const;

export function useReports(filters: ReportsFilterState, timeZone: string | undefined) {
  const params: ReportsParams = {
    ...accountScope(filters, timeZone),
    models: sorted(filters.models),
    useragents: sorted(filters.useragents),
  };
  return useQuery({
    ...REPORT_QUERY_OPTIONS,
    enabled: isReportDateRangeValid(filters.startDate, filters.endDate),
    queryKey: ["reports", params],
    queryFn: () => getReports(params),
  });
}

/** Filter choices; the model and user-agent selections do not narrow them. */
export function useReportsOptions(filters: ReportsFilterState, timeZone: string | undefined) {
  const params = accountScope(filters, timeZone);
  return useQuery({
    ...REPORT_QUERY_OPTIONS,
    enabled: isReportDateRangeValid(filters.startDate, filters.endDate),
    queryKey: ["reports-options", params],
    queryFn: () => getReportsOptions(params),
  });
}

/**
 * Thread identity scans raw request logs over the whole pool, so it is scoped
 * by the date range alone and only requested while its section is open.
 */
export function useThreadIdentity(
  filters: Pick<ReportsFilterState, "startDate" | "endDate">,
  timeZone: string | undefined,
  enabled: boolean,
) {
  const params = { startDate: filters.startDate, endDate: filters.endDate, timezone: timeZone };
  return useQuery({
    ...REPORT_QUERY_OPTIONS,
    enabled: enabled && isReportDateRangeValid(filters.startDate, filters.endDate),
    queryKey: ["reports-thread-identity", params],
    queryFn: () => getThreadIdentity(params),
  });
}
