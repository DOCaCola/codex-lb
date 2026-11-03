import { useQuery } from "@tanstack/react-query";

import { getDashboardOverview, getDashboardProjections } from "@/features/dashboard/api";
import {
  DEFAULT_OVERVIEW_TIMEFRAME,
  type OverviewTimeframe,
} from "@/features/dashboard/schemas";
import { type RecentLookbacks, useDashboardPreferencesStore, useRecentLookbacks } from "@/hooks/use-dashboard-preferences";

/** The overview query; every reader shares one cache entry per timeframe and recent-usage periods. */
export function dashboardOverviewQuery(timeframe: OverviewTimeframe, recent: RecentLookbacks) {
  return {
    queryKey: ["dashboard", "overview", timeframe, recent] as const,
    queryFn: () => getDashboardOverview({ timeframe, recent }),
  };
}

export function useDashboard(timeframe: OverviewTimeframe = DEFAULT_OVERVIEW_TIMEFRAME) {
  const refreshSeconds = useDashboardPreferencesStore((state) => state.refreshSeconds);
  const recent = useRecentLookbacks();
  return useQuery({
    ...dashboardOverviewQuery(timeframe, recent),
    refetchInterval: refreshSeconds * 1_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
}

export function useDashboardProjections(enabled = true) {
  const refreshSeconds = useDashboardPreferencesStore((state) => state.refreshSeconds);
  return useQuery({
    queryKey: ["dashboard", "projections"],
    queryFn: getDashboardProjections,
    enabled,
    refetchInterval: refreshSeconds * 1_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
}
