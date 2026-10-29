import { useTranslation } from "react-i18next";

import { FAMILY_LABELS } from "@/features/antigravity/display-values";
import { formatProUnits, type AntigravityQuotaBars, type RemainingItem } from "@/features/dashboard/utils";
import { useThemeStore } from "@/hooks/use-theme";
import { buildDonutPalette } from "@/utils/colors";
import { formatQuotaResetLabel } from "@/utils/formatters";

export type AntigravityQuotaBarsCardProps = {
  title: string;
  bars: AntigravityQuotaBars;
  /** Muted note under the bars, e.g. accounts left out of the pools. */
  note?: string;
};

function formatUsedPercent(remaining: number, total: number): string {
  const used = (100 * (total - remaining)) / total;
  return used > 0 && used < 10 ? used.toFixed(1) + "%" : Math.round(used) + "%";
}

/**
 * One stacked bar per Antigravity model family. Google limits the families
 * separately, so each bar is its own plan-weighted pool in Pro units; the
 * segments are the accounts' remaining quota in their chart colours.
 */
export function AntigravityQuotaBarsCard({ title, bars, note }: AntigravityQuotaBarsCardProps) {
  const { t } = useTranslation();
  const isDark = useThemeStore((s) => s.theme === "dark");
  const consumedColor = isDark ? "#404040" : "#d3d3d3";

  // Every account keeps one colour across the family bars.
  const legend = [
    ...new Map(bars.families.flatMap((bar) => bar.items).map((item) => [item.accountId, item])).values(),
  ];
  const palette = buildDonutPalette(legend.length, isDark);
  const colors = new Map(legend.map((item, index) => [item.accountId, item.color ?? palette[index % palette.length]]));
  const segments = (items: RemainingItem[]) => [...items].sort((a, b) => b.value - a.value);

  return (
    <section
      className="min-w-0 rounded-xl border bg-card p-5"
      aria-label={title}
      data-testid="antigravity-quota-bars"
    >
      <div className="mb-5">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">{t("dashboard.usage.subtitleAntigravity")}</p>
      </div>

      <div className="space-y-3.5">
        {bars.families.map((bar) => (
          <div key={bar.family} data-testid={"antigravity-family-" + bar.family}>
            <div className="mb-1.5 flex items-baseline justify-between gap-3 text-xs">
              <span className="truncate font-medium">{FAMILY_LABELS[bar.family]}</span>
              <span className="whitespace-nowrap tabular-nums text-muted-foreground">
                {bar.total > 0
                  ? t("dashboard.usage.familyRemaining", {
                      remaining: formatProUnits(bar.remaining),
                      total: formatProUnits(bar.total),
                      used: formatUsedPercent(bar.remaining, bar.total),
                    })
                  : t("dashboard.usage.familyNotReported")}
              </span>
            </div>
            {bar.total > 0 ? (
              <>
                <div className="flex h-2 overflow-hidden rounded-full" style={{ backgroundColor: consumedColor }}>
                  {segments(bar.items).map((item) => (
                    <div
                      key={item.accountId}
                      className="h-full"
                      title={item.label + ": " + formatProUnits(item.value)}
                      style={{ width: (100 * item.value) / bar.total + "%", backgroundColor: colors.get(item.accountId) }}
                    />
                  ))}
                </div>
                <p className="mt-1 text-[11px] tabular-nums text-muted-foreground">
                  {[
                    bar.nextResetAt
                      ? t("dashboard.usage.familyNextReset", { time: formatQuotaResetLabel(bar.nextResetAt) })
                      : null,
                    bar.notReported.length > 0
                      ? t("dashboard.usage.familyNotReportedBy", { names: bar.notReported.join(", ") })
                      : null,
                  ]
                    .filter((part): part is string => part !== null)
                    .join(" · ")}
                </p>
              </>
            ) : (
              <div className="h-2 rounded-full border border-dashed" />
            )}
          </div>
        ))}
      </div>

      {legend.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-x-3 gap-y-1 border-t pt-3 text-[11px] text-muted-foreground">
          {legend.map((item) => (
            <span key={item.accountId} className="inline-flex min-w-0 items-center gap-1.5">
              <span aria-hidden className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: colors.get(item.accountId) }} />
              <span className="truncate">{item.label}</span>
            </span>
          ))}
          <span className="inline-flex items-center gap-1.5">
            <span aria-hidden className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: consumedColor }} />
            {t("components.donut.used")}
          </span>
        </div>
      ) : null}
      {note ? (
        <p className="mt-3 text-[11px] text-muted-foreground" data-testid="antigravity-quota-note">
          {note}
        </p>
      ) : null}
    </section>
  );
}

