import { Monitor, Moon, Palette, Sun } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Switch } from "@/components/ui/switch";
import { useAccountQuotaDisplayStore, type AccountQuotaDisplayPreference } from "@/hooks/use-account-quota-display";
import {
  RECENT_LONG_PERIODS,
  RECENT_SHORT_MINUTES,
  useDashboardPreferencesStore,
  type DashboardRefreshSeconds,
} from "@/hooks/use-dashboard-preferences";
import { useThemeStore, type ThemePreference } from "@/hooks/use-theme";
import { useTimeFormatStore, type TimeFormatPreference } from "@/hooks/use-time-format";
import { useDateDisplayFormatStore, type DateDisplayFormat } from "@/hooks/use-date-format";
import { cn } from "@/lib/utils";

const THEME_OPTIONS: { value: ThemePreference; labelKey: string; icon: typeof Sun }[] = [
  { value: "light", labelKey: "settings.appearance.theme.light", icon: Sun },
  { value: "dark", labelKey: "settings.appearance.theme.dark", icon: Moon },
  { value: "auto", labelKey: "settings.appearance.theme.auto", icon: Monitor },
];

const TIME_FORMAT_OPTIONS: { value: TimeFormatPreference; labelKey: string }[] = [
  { value: "12h", labelKey: "settings.appearance.timeFormat.h12" },
  { value: "24h", labelKey: "settings.appearance.timeFormat.h24" },
];

const DATE_FORMAT_OPTIONS: { value: DateDisplayFormat; labelKey: string }[] = [
  { value: "default", labelKey: "settings.appearance.dateFormat.default" },
  { value: "iso8601", labelKey: "settings.appearance.dateFormat.iso8601" },
];

const REFRESH_OPTIONS: DashboardRefreshSeconds[] = [5, 15, 30, 60];

function PeriodPicker<T extends number | "today">({
  label,
  ariaLabel,
  options,
  value,
  disabled,
  onChange,
}: {
  label: string;
  ariaLabel: string;
  options: readonly T[];
  value: T;
  disabled: boolean;
  onChange: (minutes: T) => void;
}) {
  const { t } = useTranslation();
  const optionLabel = (period: number | "today") =>
    period === "today"
      ? t("settings.appearance.recentPeriod.today")
      : period % 60 === 0
        ? t("settings.appearance.recentPeriod.hours", { hours: period / 60 })
        : t("settings.appearance.recentPeriod.minutes", { minutes: period });
  return (
    <div className="flex items-center justify-between gap-3 sm:justify-end">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div
        role="group"
        aria-label={ariaLabel}
        className={cn("flex items-center gap-1 rounded-lg border border-border/50 bg-muted/40 p-0.5", disabled && "opacity-50")}
      >
        {options.map((period) => (
          <button
            key={period}
            type="button"
            disabled={disabled}
            aria-pressed={value === period}
            onClick={() => onChange(period)}
            className={cn(
              "rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors duration-200 disabled:cursor-not-allowed",
              value === period
                ? "bg-background text-foreground shadow-[var(--shadow-xs)]"
                : "text-muted-foreground enabled:hover:text-foreground",
            )}
          >
            {optionLabel(period)}
          </button>
        ))}
      </div>
    </div>
  );
}

const QUOTA_DISPLAY_OPTIONS: {
  value: AccountQuotaDisplayPreference;
  labelKey: string;
  descriptionKey: string;
}[] = [
  {
    value: "5h",
    labelKey: "settings.appearance.accountRows.fiveHour",
    descriptionKey: "settings.appearance.accountRows.fiveHourDescription",
  },
  {
    value: "weekly",
    labelKey: "settings.appearance.accountRows.weekly",
    descriptionKey: "settings.appearance.accountRows.weeklyDescription",
  },
  {
    value: "both",
    labelKey: "settings.appearance.accountRows.both",
    descriptionKey: "settings.appearance.accountRows.bothDescription",
  },
];

export function AppearanceSettings() {
  const { t } = useTranslation();
  const preference = useThemeStore((s) => s.preference);
  const setTheme = useThemeStore((s) => s.setTheme);
  const timeFormat = useTimeFormatStore((s) => s.timeFormat);
  const setTimeFormat = useTimeFormatStore((s) => s.setTimeFormat);
  const quotaDisplay = useAccountQuotaDisplayStore((s) => s.quotaDisplay);
  const setQuotaDisplay = useAccountQuotaDisplayStore((s) => s.setQuotaDisplay);
  const accountBurnrateEnabled = useDashboardPreferencesStore((s) => s.accountBurnrateEnabled);
  const setAccountBurnrateEnabled = useDashboardPreferencesStore((s) => s.setAccountBurnrateEnabled);
  const recentUsageEnabled = useDashboardPreferencesStore((s) => s.recentUsageEnabled);
  const setRecentUsageEnabled = useDashboardPreferencesStore((s) => s.setRecentUsageEnabled);
  const recentShortMinutes = useDashboardPreferencesStore((s) => s.recentShortMinutes);
  const setRecentShortMinutes = useDashboardPreferencesStore((s) => s.setRecentShortMinutes);
  const recentLongPeriod = useDashboardPreferencesStore((s) => s.recentLongPeriod);
  const setRecentLongPeriod = useDashboardPreferencesStore((s) => s.setRecentLongPeriod);
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  const setDateDisplayFormat = useDateDisplayFormatStore((s) => s.setDateDisplayFormat);
  const refreshSeconds = useDashboardPreferencesStore((s) => s.refreshSeconds);
  const setRefreshSeconds = useDashboardPreferencesStore((s) => s.setRefreshSeconds);

  return (
    <section className="rounded-xl border bg-card p-5">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Palette className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">{t("settings.appearance.title")}</h3>
              <p className="text-xs text-muted-foreground">{t("settings.appearance.description")}</p>
            </div>
          </div>
        </div>

        <div className="divide-y rounded-lg border">
          <div className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium">{t("settings.appearance.theme.label")}</p>
              <p className="text-xs text-muted-foreground">{t("settings.appearance.theme.description")}</p>
            </div>
            <div className="flex items-center gap-1 rounded-lg border border-border/50 bg-muted/40 p-0.5">
              {THEME_OPTIONS.map(({ value, labelKey, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={preference === value}
                  onClick={() => setTheme(value)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors duration-200",
                    preference === value
                      ? "bg-background text-foreground shadow-[var(--shadow-xs)]"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {t(labelKey)}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium">{t("settings.appearance.timeFormat.label")}</p>
              <p className="text-xs text-muted-foreground">{t("settings.appearance.timeFormat.description")}</p>
            </div>
            <div
              role="group"
              aria-label={t("settings.appearance.timeFormat.label")}
              className="flex items-center gap-1 rounded-lg border border-border/50 bg-muted/40 p-0.5"
            >
              {TIME_FORMAT_OPTIONS.map(({ value, labelKey }) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={timeFormat === value}
                  onClick={() => setTimeFormat(value)}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-left text-xs font-medium transition-colors duration-200",
                    timeFormat === value
                      ? "bg-background text-foreground shadow-[var(--shadow-xs)]"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <span className="block">{t(labelKey)}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium">{t("settings.appearance.dateFormat.label")}</p>
              <p className="text-xs text-muted-foreground">{t("settings.appearance.dateFormat.description")}</p>
            </div>
            <div className="flex items-center gap-1 rounded-lg border border-border/50 bg-muted/40 p-0.5">
              {DATE_FORMAT_OPTIONS.map(({ value, labelKey }) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={dateDisplayFormat === value}
                  onClick={() => setDateDisplayFormat(value)}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-left text-xs font-medium transition-colors duration-200",
                    dateDisplayFormat === value
                      ? "bg-background text-foreground shadow-[var(--shadow-xs)]"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <span className="block">{t(labelKey)}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium">{t("settings.appearance.accountRows.label")}</p>
              <p className="text-xs text-muted-foreground">{t("settings.appearance.accountRows.description")}</p>
            </div>
            <div className="flex items-center gap-1 rounded-lg border border-border/50 bg-muted/40 p-0.5">
              {QUOTA_DISPLAY_OPTIONS.map(({ value, labelKey, descriptionKey }) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={quotaDisplay === value}
                  title={t(descriptionKey)}
                  onClick={() => setQuotaDisplay(value)}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-left text-xs font-medium transition-colors duration-200",
                    quotaDisplay === value
                      ? "bg-background text-foreground shadow-[var(--shadow-xs)]"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <span className="block">{t(labelKey)}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium">{t("settings.appearance.refreshRate.label")}</p>
              <p className="text-xs text-muted-foreground">{t("settings.appearance.refreshRate.description")}</p>
            </div>
            <div className="flex items-center gap-1 rounded-lg border border-border/50 bg-muted/40 p-0.5">
              {REFRESH_OPTIONS.map((seconds) => (
                <button
                  key={seconds}
                  type="button"
                  aria-pressed={refreshSeconds === seconds}
                  onClick={() => setRefreshSeconds(seconds)}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-left text-xs font-medium transition-colors duration-200",
                    refreshSeconds === seconds
                      ? "bg-background text-foreground shadow-[var(--shadow-xs)]"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {t("settings.appearance.refreshRate.seconds", { seconds })}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium">{t("settings.appearance.burnProjection.label")}</p>
              <p className="text-xs text-muted-foreground">{t("settings.appearance.burnProjection.description")}</p>
            </div>
            <Switch
              aria-label={t("settings.appearance.burnProjection.ariaLabel")}
              checked={accountBurnrateEnabled}
              onCheckedChange={setAccountBurnrateEnabled}
            />
          </div>

          <div className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium">{t("settings.appearance.recentUsage.label")}</p>
              <p className="text-xs text-muted-foreground">{t("settings.appearance.recentUsage.description")}</p>
            </div>
            <Switch
              aria-label={t("settings.appearance.recentUsage.ariaLabel")}
              checked={recentUsageEnabled}
              onCheckedChange={setRecentUsageEnabled}
            />
          </div>

          <div className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium">{t("settings.appearance.recentPeriod.label")}</p>
              <p className="text-xs text-muted-foreground">{t("settings.appearance.recentPeriod.description")}</p>
            </div>
            <div className="flex flex-col gap-2">
              <PeriodPicker
                label={t("settings.appearance.recentPeriod.fiveHour")}
                ariaLabel={t("settings.appearance.recentPeriod.fiveHourAriaLabel")}
                options={RECENT_SHORT_MINUTES}
                value={recentShortMinutes}
                disabled={!recentUsageEnabled}
                onChange={setRecentShortMinutes}
              />
              <PeriodPicker
                label={t("settings.appearance.recentPeriod.weekly")}
                ariaLabel={t("settings.appearance.recentPeriod.weeklyAriaLabel")}
                options={RECENT_LONG_PERIODS}
                value={recentLongPeriod}
                disabled={!recentUsageEnabled}
                onChange={setRecentLongPeriod}
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
