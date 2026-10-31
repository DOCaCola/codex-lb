import { create } from "zustand";

import type { QuotaProvider } from "@/features/dashboard/utils";

const ACCOUNT_BURNRATE_STORAGE_KEY = "codex-lb-account-burnrate-enabled";
const ACCOUNT_VIEW_MODE_STORAGE_KEY = "codex-lb-dashboard-account-view-mode";
const DASHBOARD_REFRESH_STORAGE_KEY = "codex-lb-dashboard-refresh-seconds";
const QUOTA_PROVIDER_STORAGE_KEY = "codex-lb-dashboard-quota-provider";

export type DashboardRefreshSeconds = 5 | 15 | 30 | 60;

export type DashboardAccountViewMode = "cards" | "list";

type DashboardPreferencesState = {
  accountBurnrateEnabled: boolean;
  accountViewMode: DashboardAccountViewMode;
  refreshSeconds: DashboardRefreshSeconds;
  quotaProvider: QuotaProvider;
  initialized: boolean;
  initializePreferences: () => void;
  setAccountBurnrateEnabled: (enabled: boolean) => void;
  setAccountViewMode: (mode: DashboardAccountViewMode) => void;
  setRefreshSeconds: (seconds: DashboardRefreshSeconds) => void;
  setQuotaProvider: (provider: QuotaProvider) => void;
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
  initialized: false,
  initializePreferences: () => {
    const accountBurnrateEnabled = readStoredAccountBurnrateEnabled() ?? true;
    const accountViewMode = readStoredAccountViewMode() ?? "cards";
    const refreshSeconds = readStoredRefreshSeconds() ?? 15;
    const quotaProvider = readStoredQuotaProvider() ?? "codex";
    persistAccountBurnrateEnabled(accountBurnrateEnabled);
    persistAccountViewMode(accountViewMode);
    persistRefreshSeconds(refreshSeconds);
    persistQuotaProvider(quotaProvider);
    set({ accountBurnrateEnabled, accountViewMode, refreshSeconds, quotaProvider, initialized: true });
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
}));
