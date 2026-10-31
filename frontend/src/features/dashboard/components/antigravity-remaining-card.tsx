import { useTranslation } from "react-i18next";

import { FAMILY_LABELS } from "@/features/antigravity/display-values";
import { formatProUnits, type AntigravityFamilyBar, type AntigravityQuotaBars, type RemainingItem } from "@/features/dashboard/utils";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import { formatDateTimeInline, formatResetCountdown } from "@/utils/formatters";

export type AntigravityRemainingCardProps = {
  title: string;
  subtitle: string;
  fiveHour: AntigravityQuotaBars;
  weekly: AntigravityQuotaBars;
  /** Muted notes under the table, for example accounts left out of the pools. */
  notes: string[];
};

function FamilyCell({ bar }: { bar: AntigravityFamilyBar }) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  if (bar.total <= 0) {
    return (
      <td className="py-2 pl-5 text-right text-xs text-muted-foreground">
        {t("dashboard.usage.familyNotReported")}
      </td>
    );
  }
  const percent = Math.round((bar.remaining / bar.total) * 100);
  const countdown = formatResetCountdown(bar.nextResetAt);
  const segments = [...bar.items].sort((a, b) => b.value - a.value);
  return (
    <td className="w-[40%] py-2 pl-5">
      <div className="flex items-center gap-2.5">
        <div className="flex h-[5px] flex-1 overflow-hidden rounded-full bg-muted">
          {segments.map((item: RemainingItem) => (
            <div
              key={item.accountId}
              className="h-full"
              title={item.label + ": " + formatProUnits(item.value)}
              style={{ width: (100 * item.value) / bar.total + "%", backgroundColor: item.color ?? "var(--muted-foreground)" }}
            />
          ))}
        </div>
        <span className={cn("w-9 text-right font-semibold tabular-nums", percent === 0 && "text-destructive")}>{percent}%</span>
      </div>
      <p
        className="mt-0.5 truncate text-right text-[11px] text-muted-foreground tabular-nums"
        title={bar.nextResetAt ? t("dashboard.remaining.resetsAt", { time: formatDateTimeInline(bar.nextResetAt, dateDisplayFormat) }) : undefined}
      >
        {[
          countdown
            ? t("dashboard.usage.familyNextReset", { time: countdown })
            : null,
          bar.notReported.length > 0 ? t("dashboard.usage.familyNotReportedBy", { names: bar.notReported.join(", ") }) : null,
        ]
          .filter((part): part is string => part !== null)
          .join(" · ")}
      </p>
    </td>
  );
}

/**
 * Remaining Antigravity quota per model family. Google limits the families
 * separately, so every bar is its own plan-weighted pool in Pro units whose
 * segments are the accounts' remaining quota in their chart colours.
 */
export function AntigravityRemainingCard({ title, subtitle, fiveHour, weekly, notes }: AntigravityRemainingCardProps) {
  const { t } = useTranslation();
  const blurred = usePrivacyStore((s) => s.blurred);
  const weeklyByFamily = new Map(weekly.families.map((bar) => [bar.family, bar]));
  const legend = [
    ...new Map(
      [...fiveHour.families, ...weekly.families].flatMap((bar) => bar.items).map((item) => [item.accountId, item]),
    ).values(),
  ];
  return (
    <section
      aria-label={title}
      data-testid="antigravity-remaining-card"
      className="flex min-w-0 flex-col gap-3.5 rounded-xl border bg-card px-[18px] py-4 @min-[44rem]/quota:col-span-2 @min-[74rem]/quota:col-span-1"
    >
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
      </div>
      <table className="w-full border-collapse text-[12.5px] [&_td]:border-b [&_tbody_tr:last-child_td]:border-b-0">
        <thead>
          <tr className="text-[11.5px] text-muted-foreground">
            <th className="border-b pb-1.5 text-left font-medium">{t("dashboard.remaining.modelFamily")}</th>
            <th className="border-b pb-1.5 pl-5 text-right font-medium">{t("dashboard.remaining.fiveHours")}</th>
            <th className="border-b pb-1.5 pl-5 text-right font-medium">{t("dashboard.remaining.weekly")}</th>
          </tr>
        </thead>
        <tbody>
          {fiveHour.families.map((bar) => {
            const weeklyBar = weeklyByFamily.get(bar.family);
            return (
              <tr key={bar.family} data-testid={"antigravity-family-" + bar.family}>
                <td className="py-2 font-medium whitespace-nowrap">{FAMILY_LABELS[bar.family]}</td>
                <FamilyCell bar={bar} />
                {weeklyBar ? <FamilyCell bar={weeklyBar} /> : <td />}
              </tr>
            );
          })}
        </tbody>
      </table>
      {legend.length > 1 ? (
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
          {legend.map((item) => (
            <span key={item.accountId} className="inline-flex min-w-0 items-center gap-1.5">
              <span aria-hidden className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: item.color ?? "var(--muted-foreground)" }} />
              <span className={cn("truncate", blurred && "privacy-blur")}>{item.label}</span>
            </span>
          ))}
        </div>
      ) : null}
      {notes.map((note) => (
        <p key={note} className="text-[11.5px] text-muted-foreground" data-testid="antigravity-quota-note">
          {note}
        </p>
      ))}
    </section>
  );
}
