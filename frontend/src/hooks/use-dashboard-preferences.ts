import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";

import type { QuotaProvider } from "@/features/dashboard/utils";

const ACCOUNT_BURNRATE_STORAGE_KEY = "codex-lb-account-burnrate-enabled";
const ACCOUNT_VIEW_MODE_STORAGE_KEY = "codex-lb-dashboard-account-view-mode";
const DASHBOARD_REFRESH_STORAGE_KEY = "codex-lb-dashboard-refresh-seconds";
const QUOTA_PROVIDER_STORAGE_KEY = "codex-lb-dashboard-quota-provider";
const RECENT_USAGE_STORAGE_KEY = "codex-lb-dashboard-recent-usage";
const RECENT_SHORT_MINUTES_STORAGE_KEY = "codex-lb-dashboard-recent-short-minutes";
const RECENT_LONG_PERIOD_STORAGE_KEY = "codex-lb-dashboard-recent-long-period";

export type DashboardRefreshSeconds = 5 | 15 | 30 | 60;

export type DashboardAccountViewMode = "cards" | "list";

/** How far back the recent-usage tint looks on 5h limits. */
export const RECENT_SHORT_MINUTES = [15, 30, 60] as const;
export type RecentShortMinutes = (typeof RECENT_SHORT_MINUTES)[number];
/** How far back the recent-usage tint looks on weekly limits: a number of minutes, or since local midnight. */
export const RECENT_LONG_PERIODS = [60, 120, 240, 360, 720, 1440, "today"] as const;
export type RecentLongPeriod = (typeof RECENT_LONG_PERIODS)[number];

export type RecentLookbacks = { recentShortMinutes: RecentShortMinutes; recentLongPeriod: RecentLongPeriod };

type DashboardPreferencesState = {
  accountBurnrateEnabled: boolean;
  accountViewMode: DashboardAccountViewMode;
  refreshSeconds: DashboardRefreshSeconds;
  quotaProvider: QuotaProvider;
  recentUsageEnabled: boolean;
  recentShortMinutes: RecentShortMinutes;
  recentLongPeriod: RecentLongPeriod;
  initialized: boolean;
  initializePreferences: () => void;
  setAccountBurnrateEnabled: (enabled: boolean) => void;
  setAccountViewMode: (mode: DashboardAccountViewMode) => void;
  setRefreshSeconds: (seconds: DashboardRefreshSeconds) => void;
  setQuotaProvider: (provider: QuotaProvider) => void;
  setRecentUsageEnabled: (enabled: boolean) => void;
  setRecentShortMinutes: (minutes: RecentShortMinutes) => void;
  setRecentLongPeriod: (period: RecentLongPeriod) => void;
};

function readStoredAccountBurnrateEnabled(): boolean | null {
  if (typeof window === "undefined") {
    return null;
  }
  const stored = window.localStorage.getItem(ACCOUNT_BURNRATE_STORAGE_KEY);
  if (stored === "true") {
    return true;
  }
  if (stored === "false") {
    return false;
  }
  return null;
}

function readStoredAccountViewMode(): DashboardAccountViewMode | null {
  if (typeof window === "undefined") {
    return null;
  }
  const stored = window.localStorage.getItem(ACCOUNT_VIEW_MODE_STORAGE_KEY);
  return stored === "cards" || stored === "list" ? stored : null;
}

function readStoredRefreshSeconds(): DashboardRefreshSeconds | null {
  if (typeof window === "undefined") {
    return null;
  }
  const numeric = Number(window.localStorage.getItem(DASHBOARD_REFRESH_STORAGE_KEY));
  return numeric === 5 || numeric === 15 || numeric === 30 || numeric === 60
    ? numeric
    : null;
}

function persistAccountBurnrateEnabled(enabled: boolean): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(ACCOUNT_BURNRATE_STORAGE_KEY, String(enabled));
}

function readStoredRecentUsageEnabled(): boolean | null {
  if (typeof window === "undefined") {
    return null;
  }
  const stored = window.localStorage.getItem(RECENT_USAGE_STORAGE_KEY);
  if (stored === "true") {
    return true;
  }
  if (stored === "false") {
    return false;
  }
  return null;
}

function persistRecentUsageEnabled(enabled: boolean): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(RECENT_USAGE_STORAGE_KEY, String(enabled));
}

function readStoredPeriod<T extends number | string>(key: string, options: readonly T[]): T | null {
  if (typeof window === "undefined") {
    return null;
  }
  const stored = window.localStorage.getItem(key);
  return options.find((option) => String(option) === stored) ?? null;
}

function persistPeriod(key: string, period: number | string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(key, String(period));
}

function readStoredQuotaProvider(): QuotaProvider | null {
  if (typeof window === "undefined") {
    return null;
  }
  const stored = window.localStorage.getItem(QUOTA_PROVIDER_STORAGE_KEY);
  return stored === "codex" || stored === "claude" || stored === "antigravity" ? stored : null;
}

function persistQuotaProvider(provider: QuotaProvider): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(QUOTA_PROVIDER_STORAGE_KEY, provider);
}

function persistAccountViewMode(mode: DashboardAccountViewMode): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(ACCOUNT_VIEW_MODE_STORAGE_KEY, mode);
}

function persistRefreshSeconds(seconds: DashboardRefreshSeconds): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(DASHBOARD_REFRESH_STORAGE_KEY, String(seconds));
}

export const useDashboardPreferencesStore = create<DashboardPreferencesState>((set) => ({
  accountBurnrateEnabled: true,
  accountViewMode: "cards",
  refreshSeconds: 15,
  quotaProvider: "codex",
  recentUsageEnabled: true,
  recentShortMinutes: 60,
  recentLongPeriod: 1440,
  initialized: false,
  initializePreferences: () => {
    const accountBurnrateEnabled = readStoredAccountBurnrateEnabled() ?? true;
    const accountViewMode = readStoredAccountViewMode() ?? "cards";
    const refreshSeconds = readStoredRefreshSeconds() ?? 15;
    const quotaProvider = readStoredQuotaProvider() ?? "codex";
    const recentUsageEnabled = readStoredRecentUsageEnabled() ?? true;
    const recentShortMinutes = readStoredPeriod(RECENT_SHORT_MINUTES_STORAGE_KEY, RECENT_SHORT_MINUTES) ?? 60;
    const recentLongPeriod = readStoredPeriod(RECENT_LONG_PERIOD_STORAGE_KEY, RECENT_LONG_PERIODS) ?? 1440;
    persistAccountBurnrateEnabled(accountBurnrateEnabled);
    persistAccountViewMode(accountViewMode);
    persistRefreshSeconds(refreshSeconds);
    persistQuotaProvider(quotaProvider);
    persistRecentUsageEnabled(recentUsageEnabled);
    persistPeriod(RECENT_SHORT_MINUTES_STORAGE_KEY, recentShortMinutes);
    persistPeriod(RECENT_LONG_PERIOD_STORAGE_KEY, recentLongPeriod);
    set({
      accountBurnrateEnabled,
      accountViewMode,
      refreshSeconds,
      quotaProvider,
      recentUsageEnabled,
      recentShortMinutes,
      recentLongPeriod,
      initialized: true,
    });
  },
  setAccountBurnrateEnabled: (enabled) => {
    persistAccountBurnrateEnabled(enabled);
    set({ accountBurnrateEnabled: enabled, initialized: true });
  },
  setAccountViewMode: (mode) => {
    persistAccountViewMode(mode);
    set({ accountViewMode: mode, initialized: true });
  },
  setRefreshSeconds: (seconds) => {
    persistRefreshSeconds(seconds);
    set({ refreshSeconds: seconds, initialized: true });
  },
  setQuotaProvider: (provider) => {
    persistQuotaProvider(provider);
    set({ quotaProvider: provider, initialized: true });
  },
  setRecentUsageEnabled: (enabled) => {
    persistRecentUsageEnabled(enabled);
    set({ recentUsageEnabled: enabled, initialized: true });
  },
  setRecentShortMinutes: (minutes) => {
    persistPeriod(RECENT_SHORT_MINUTES_STORAGE_KEY, minutes);
    set({ recentShortMinutes: minutes, initialized: true });
  },
  setRecentLongPeriod: (period) => {
    persistPeriod(RECENT_LONG_PERIOD_STORAGE_KEY, period);
    set({ recentLongPeriod: period, initialized: true });
  },
}));

/** The recent-usage periods the dashboard asks the server for; part of every query that reports recent usage. */
export function useRecentLookbacks(): RecentLookbacks {
  return useDashboardPreferencesStore(
    useShallow((s) => ({ recentShortMinutes: s.recentShortMinutes, recentLongPeriod: s.recentLongPeriod })),
  );
}

/**
 * Query parameters for the recent-usage periods. "Today" is sent as the start of the browser's local day, computed
 * per request so a refetch after midnight starts the new day.
 */
export function appendRecentLookbacks(query: URLSearchParams, lookbacks: RecentLookbacks): URLSearchParams {
  query.set("recentShortMinutes", String(lookbacks.recentShortMinutes));
  if (lookbacks.recentLongPeriod === "today") {
    const dayStart = new Date();
    dayStart.setHours(0, 0, 0, 0);
    query.set("recentLongSince", dayStart.toISOString());
  } else {
    query.set("recentLongMinutes", String(lookbacks.recentLongPeriod));
  }
  return query;
}
