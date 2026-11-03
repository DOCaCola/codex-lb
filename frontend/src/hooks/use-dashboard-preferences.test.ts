import { beforeEach, describe, expect, it, vi } from "vitest";

function installLocalStorageMock() {
  const storage = new Map<string, string>();
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => {
        storage.set(key, value);
      },
      removeItem: (key: string) => {
        storage.delete(key);
      },
      clear: () => {
        storage.clear();
      },
    },
  });
}

describe("useDashboardPreferencesStore", () => {
  beforeEach(() => {
    installLocalStorageMock();
    vi.resetModules();
  });

  it("defaults account view mode to cards", async () => {
    const { useDashboardPreferencesStore } = await import("@/hooks/use-dashboard-preferences");

    useDashboardPreferencesStore.getState().initializePreferences();

    expect(useDashboardPreferencesStore.getState().accountViewMode).toBe("cards");
    expect(useDashboardPreferencesStore.getState().refreshSeconds).toBe(15);
    expect(window.localStorage.getItem("codex-lb-dashboard-account-view-mode")).toBe("cards");
    expect(window.localStorage.getItem("codex-lb-dashboard-refresh-seconds")).toBe("15");
  });

  it("persists a valid dashboard refresh cadence", async () => {
    const { useDashboardPreferencesStore } = await import("@/hooks/use-dashboard-preferences");

    useDashboardPreferencesStore.getState().setRefreshSeconds(5);

    expect(useDashboardPreferencesStore.getState().refreshSeconds).toBe(5);
    expect(window.localStorage.getItem("codex-lb-dashboard-refresh-seconds")).toBe("5");
  });

  it("restores a stored refresh cadence on initialize", async () => {
    window.localStorage.setItem("codex-lb-dashboard-refresh-seconds", "30");
    const { useDashboardPreferencesStore } = await import("@/hooks/use-dashboard-preferences");

    useDashboardPreferencesStore.getState().initializePreferences();

    expect(useDashboardPreferencesStore.getState().refreshSeconds).toBe(30);
    expect(window.localStorage.getItem("codex-lb-dashboard-refresh-seconds")).toBe("30");
  });

  it("ignores an invalid stored refresh cadence", async () => {
    window.localStorage.setItem("codex-lb-dashboard-refresh-seconds", "7");
    const { useDashboardPreferencesStore } = await import("@/hooks/use-dashboard-preferences");

    useDashboardPreferencesStore.getState().initializePreferences();

    expect(useDashboardPreferencesStore.getState().refreshSeconds).toBe(15);
    expect(window.localStorage.getItem("codex-lb-dashboard-refresh-seconds")).toBe("15");
  });

  it("persists account view mode updates", async () => {
    const { useDashboardPreferencesStore } = await import("@/hooks/use-dashboard-preferences");

    useDashboardPreferencesStore.getState().setAccountViewMode("list");

    expect(useDashboardPreferencesStore.getState().accountViewMode).toBe("list");
    expect(window.localStorage.getItem("codex-lb-dashboard-account-view-mode")).toBe("list");
  });

  it("restores stored recent usage periods and rejects unknown ones", async () => {
    window.localStorage.setItem("codex-lb-dashboard-recent-short-minutes", "45");
    window.localStorage.setItem("codex-lb-dashboard-recent-long-period", "today");
    const { useDashboardPreferencesStore } = await import("@/hooks/use-dashboard-preferences");

    useDashboardPreferencesStore.getState().initializePreferences();

    expect(useDashboardPreferencesStore.getState().recentShortMinutes).toBe(60);
    expect(useDashboardPreferencesStore.getState().recentLongPeriod).toBe("today");
    expect(window.localStorage.getItem("codex-lb-dashboard-recent-short-minutes")).toBe("60");
  });

  it("sends today as the start of the local day", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 10, 3, 14, 30));
    try {
      const { appendRecentLookbacks } = await import("@/hooks/use-dashboard-preferences");

      const today = appendRecentLookbacks(new URLSearchParams(), { recentShortMinutes: 15, recentLongPeriod: "today" });
      expect(today.get("recentShortMinutes")).toBe("15");
      expect(today.get("recentLongSince")).toBe(new Date(2026, 10, 3).toISOString());
      expect(today.has("recentLongMinutes")).toBe(false);

      const hours = appendRecentLookbacks(new URLSearchParams(), { recentShortMinutes: 60, recentLongPeriod: 240 });
      expect(hours.get("recentLongMinutes")).toBe("240");
      expect(hours.has("recentLongSince")).toBe(false);
    } finally {
      vi.useRealTimers();
    }
  });
});
