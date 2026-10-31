import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { usePermission } from "@/features/auth/hooks/use-auth";
import { getReports } from "@/features/reports/api";
import { getBrowserReportsTimeZone, daysAgoLocalISO, localDateISO } from "@/features/reports/date";
import { accountFilterKey } from "@/features/reports/report-model";
import type { ReportsResponse } from "@/features/reports/schemas";

export const ACTIVITY_DAYS = 7;

export type ActivityDay = {
  date: string;
  requests: number;
  costUsd: number;
  tokens: number;
  cachedInputTokens: number;
  inputTokens: number;
  errors: number;
  unpricedRequests: number;
};

export type AccountActivity = {
  days: ActivityDay[];
  today: ActivityDay;
  total: ActivityDay;
};

const emptyDay = (date: string): ActivityDay => ({
  date,
  requests: 0,
  costUsd: 0,
  tokens: 0,
  cachedInputTokens: 0,
  inputTokens: 0,
  errors: 0,
  unpricedRequests: 0,
});

function addDay(total: ActivityDay, day: ActivityDay): ActivityDay {
  return {
    date: total.date,
    requests: total.requests + day.requests,
    costUsd: total.costUsd + day.costUsd,
    tokens: total.tokens + day.tokens,
    cachedInputTokens: total.cachedInputTokens + day.cachedInputTokens,
    inputTokens: total.inputTokens + day.inputTokens,
    errors: total.errors + day.errors,
    unpricedRequests: total.unpricedRequests + day.unpricedRequests,
  };
}

/** Per-account daily activity of the report range, keyed by the reports account key; days without activity are zero. */
export function accountActivityByKey(report: ReportsResponse, dates: string[]): Map<string, AccountActivity> {
  const byKey = new Map<string, Map<string, ActivityDay>>();
  for (const row of report.dailyByAccount) {
    const key = accountFilterKey(row);
    if (key === null) continue;
    const days = byKey.get(key) ?? new Map<string, ActivityDay>();
    byKey.set(key, days);
    days.set(
      row.date,
      addDay(days.get(row.date) ?? emptyDay(row.date), {
        date: row.date,
        requests: row.requests,
        costUsd: row.costUsd,
        tokens: row.inputTokens + row.outputTokens,
        cachedInputTokens: row.cachedInputTokens,
        inputTokens: row.inputTokens,
        errors: row.errorCount,
        unpricedRequests: row.unpricedRequests,
      }),
    );
  }
  const result = new Map<string, AccountActivity>();
  for (const [key, recorded] of byKey) {
    const days = dates.map((date) => recorded.get(date) ?? emptyDay(date));
    result.set(key, {
      days,
      today: days[days.length - 1],
      total: days.reduce(addDay, emptyDay(dates[0])),
    });
  }
  return result;
}

/** Dates of the activity range in the browser's calendar, oldest first, ending today. */
export function activityDates(now = new Date()): string[] {
  return Array.from({ length: ACTIVITY_DAYS }, (_, index) => daysAgoLocalISO(ACTIVITY_DAYS - 1 - index, now));
}

/**
 * The last seven days of recorded activity of every account, from the reports
 * API. Undefined while loading or when the user cannot read reports.
 */
export function useProviderActivity() {
  const canRead = usePermission("dashboard:read");
  const dates = useMemo(() => activityDates(), []);
  const timeZone = useMemo(() => getBrowserReportsTimeZone(), []);
  const params = { startDate: dates[0], endDate: localDateISO(), timezone: timeZone };
  const query = useQuery({
    queryKey: ["providers", "activity", params],
    queryFn: () => getReports(params),
    enabled: canRead,
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
  const activity = useMemo(
    () => (query.data ? accountActivityByKey(query.data, dates) : undefined),
    [query.data, dates],
  );
  return { activity, dates, available: canRead, isError: query.isError };
}

