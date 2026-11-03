import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { AppearanceSettings } from "@/features/settings/components/appearance-settings";
import i18n from "@/i18n";
import { useAccountQuotaDisplayStore } from "@/hooks/use-account-quota-display";
import { useThemeStore } from "@/hooks/use-theme";
import { useTimeFormatStore } from "@/hooks/use-time-format";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { useDashboardPreferencesStore } from "@/hooks/use-dashboard-preferences";

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

describe("AppearanceSettings", () => {
  beforeEach(() => {
    installLocalStorageMock();
    useThemeStore.setState({ preference: "light", theme: "light", initialized: true });
    useTimeFormatStore.setState({ timeFormat: "12h" });
    useDateDisplayFormatStore.setState({ dateDisplayFormat: "default" });
    useAccountQuotaDisplayStore.setState({ quotaDisplay: "both" });
    useDashboardPreferencesStore.setState({
      refreshSeconds: 15,
      recentUsageEnabled: true,
      recentShortMinutes: 60,
      recentLongPeriod: 1440,
    });
  });

  it("updates the dashboard refresh cadence", async () => {
    const user = userEvent.setup();
    render(<AppearanceSettings />);

    const fiveSeconds = screen.getByRole("button", { name: "5s" });
    const fifteenSeconds = screen.getByRole("button", { name: "15s" });
    expect(fifteenSeconds).toHaveAttribute("aria-pressed", "true");

    await user.click(fiveSeconds);

    expect(fiveSeconds).toHaveAttribute("aria-pressed", "true");
    expect(useDashboardPreferencesStore.getState().refreshSeconds).toBe(5);
  });

  it("toggles recent usage on the dashboard limit bars", async () => {
    const user = userEvent.setup();
    useDashboardPreferencesStore.setState({ recentUsageEnabled: true });
    render(<AppearanceSettings />);

    const toggle = screen.getByRole("switch", { name: "Show recent usage on limit bars" });
    expect(toggle).toBeChecked();

    await user.click(toggle);

    expect(useDashboardPreferencesStore.getState().recentUsageEnabled).toBe(false);
    expect(window.localStorage.getItem("codex-lb-dashboard-recent-usage")).toBe("false");
  });

  it("selects the recent usage periods for 5h and weekly limits", async () => {
    const user = userEvent.setup();
    render(<AppearanceSettings />);

    const fiveHour = screen.getByRole("group", { name: "Recent usage period for 5h limits" });
    const weekly = screen.getByRole("group", { name: "Recent usage period for weekly limits" });
    expect(within(fiveHour).getAllByRole("button").map((button) => button.textContent)).toEqual(["15m", "30m", "1h"]);
    expect(within(weekly).getAllByRole("button").map((button) => button.textContent)).toEqual([
      "1h",
      "2h",
      "4h",
      "6h",
      "12h",
      "24h",
      "Today",
    ]);
    expect(within(fiveHour).getByRole("button", { name: "1h" })).toHaveAttribute("aria-pressed", "true");
    expect(within(weekly).getByRole("button", { name: "24h" })).toHaveAttribute("aria-pressed", "true");

    await user.click(within(fiveHour).getByRole("button", { name: "15m" }));
    await user.click(within(weekly).getByRole("button", { name: "Today" }));

    expect(useDashboardPreferencesStore.getState().recentShortMinutes).toBe(15);
    expect(useDashboardPreferencesStore.getState().recentLongPeriod).toBe("today");
    expect(window.localStorage.getItem("codex-lb-dashboard-recent-short-minutes")).toBe("15");
    expect(window.localStorage.getItem("codex-lb-dashboard-recent-long-period")).toBe("today");
    expect(within(weekly).getByRole("button", { name: "Today" })).toHaveAttribute("aria-pressed", "true");
  });

  it("disables the period pickers while recent usage is hidden", () => {
    useDashboardPreferencesStore.setState({ recentUsageEnabled: false });
    render(<AppearanceSettings />);

    for (const name of ["Recent usage period for 5h limits", "Recent usage period for weekly limits"]) {
      for (const button of within(screen.getByRole("group", { name })).getAllByRole("button")) {
        expect(button).toBeDisabled();
      }
    }
  });

  it("exposes selected state for the time-format toggle", async () => {
    const user = userEvent.setup();

    render(<AppearanceSettings />);

    const timeFormat = screen.getByRole("group", { name: "Time format" });
    const button12h = within(timeFormat).getByRole("button", { name: /12h/i });
    const button24h = within(timeFormat).getByRole("button", { name: /24h/i });

    expect(button12h).toHaveAttribute("aria-pressed", "true");
    expect(button24h).toHaveAttribute("aria-pressed", "false");

    await user.click(button24h);

    expect(button12h).toHaveAttribute("aria-pressed", "false");
    expect(button24h).toHaveAttribute("aria-pressed", "true");
    expect(useTimeFormatStore.getState().timeFormat).toBe("24h");
  });

  it("exposes selected state for the date-format toggle", async () => {
    const user = userEvent.setup();

    render(<AppearanceSettings />);

    const buttonDefault = screen.getByRole("button", { name: /default/i });
    const buttonIso = screen.getByRole("button", { name: /iso 8601/i });

    expect(buttonDefault).toHaveAttribute("aria-pressed", "true");
    expect(buttonIso).toHaveAttribute("aria-pressed", "false");

    await user.click(buttonIso);

    expect(buttonDefault).toHaveAttribute("aria-pressed", "false");
    expect(buttonIso).toHaveAttribute("aria-pressed", "true");
    expect(useDateDisplayFormatStore.getState().dateDisplayFormat).toBe("iso8601");
  });

  it("exposes selected state for the account quota toggle", async () => {
    const user = userEvent.setup();

    render(<AppearanceSettings />);

    const button5h = screen.getByRole("button", { name: "5H" });
    const buttonWeekly = screen.getByRole("button", { name: "W" });
    const buttonBoth = screen.getByRole("button", { name: "Both" });

    expect(buttonBoth).toHaveAttribute("aria-pressed", "true");
    expect(button5h).toHaveAttribute("aria-pressed", "false");
    expect(buttonWeekly).toHaveAttribute("aria-pressed", "false");

    await user.click(button5h);

    expect(button5h).toHaveAttribute("aria-pressed", "true");
    expect(useAccountQuotaDisplayStore.getState().quotaDisplay).toBe("5h");

    await user.click(buttonWeekly);

    expect(buttonWeekly).toHaveAttribute("aria-pressed", "true");
    expect(useAccountQuotaDisplayStore.getState().quotaDisplay).toBe("weekly");
  });

  it("localizes the account burn projection row in zh-CN", async () => {
    await i18n.changeLanguage("zh-CN");
    try {
      render(<AppearanceSettings />);

      expect(screen.getByText("账户消耗预测")).toBeInTheDocument();
      expect(screen.getByText("在仪表盘上显示账户等效预测卡片。")).toBeInTheDocument();
      expect(screen.queryByText("Account burn projection")).not.toBeInTheDocument();
      expect(
        screen.queryByText("Show the account-equivalent projection card on the dashboard."),
      ).not.toBeInTheDocument();
    } finally {
      await i18n.changeLanguage("en");
    }
  });
});
