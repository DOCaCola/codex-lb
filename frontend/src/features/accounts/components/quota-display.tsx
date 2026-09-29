import { Clock } from "lucide-react";
import { useTranslation } from "react-i18next";
import { MiniQuotaBar } from "@/components/mini-quota-bar";
import { cn } from "@/lib/utils";
import { quotaBarColor, quotaBarTrack } from "@/utils/account-status";
import { formatPercentNullable, formatQuotaResetLabel } from "@/utils/formatters";

export function QuotaBar({
  label,
  percent,
  resetLabel,
}: {
  label: string;
  percent: number | null;
  resetLabel: string;
}) {
  const clamped = percent === null ? 0 : Math.max(0, Math.min(100, percent));
  const hasPercent = percent !== null;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span
          className={cn(
            "tabular-nums font-medium",
            !hasPercent
              ? "text-muted-foreground"
              : clamped >= 70
                ? "text-emerald-600 dark:text-emerald-400"
                : clamped >= 30
                  ? "text-amber-600 dark:text-amber-400"
                  : "text-red-600 dark:text-red-400",
          )}
        >
          {formatPercentNullable(percent, 1)}
        </span>
      </div>
      <div className={cn("h-1.5 w-full overflow-hidden rounded-full", quotaBarTrack(clamped))}>
        <div
          className={cn("h-full rounded-full transition-colors duration-500 ease-out", quotaBarColor(clamped))}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
        <Clock className="h-3 w-3 shrink-0" />
        <span>{resetLabel}</span>
      </div>
    </div>
  );
}


export function QuotaRow({
  label,
  percent,
  resetAt,
}: {
  label: string;
  percent: number | null;
  resetAt: string | null | undefined;
}) {
  const { t } = useTranslation();
  const clamped = percent === null ? 0 : Math.max(0, Math.min(100, percent));
  const hasPercent = percent !== null;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium">{t("accounts.usage.remainingLabel", { label })}</span>
        <span
          className={cn(
            "tabular-nums font-medium",
            !hasPercent
              ? "text-muted-foreground"
              : clamped >= 70
                ? "text-emerald-600 dark:text-emerald-400"
                : clamped >= 30
                  ? "text-amber-600 dark:text-amber-400"
                  : "text-red-600 dark:text-red-400",
          )}
        >
          {formatPercentNullable(percent, 1)}
        </span>
      </div>
      <div className={cn("h-1.5 w-full overflow-hidden rounded-full", quotaBarTrack(clamped))}>
        <div
          className={cn("h-full rounded-full transition-colors duration-500 ease-out", quotaBarColor(clamped))}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Clock className="h-3 w-3 shrink-0" />
        <span>{t("accounts.usage.resetAt", { label: formatQuotaResetLabel(resetAt ?? null) })}</span>
      </div>
    </div>
  );
}


export function MiniQuotaRow({
  label,
  percent,
  resetAt,
}: {
  label: string;
  percent: number | null;
  resetAt: string | null | undefined;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-muted-foreground">{label}</span>
        <span className="tabular-nums font-medium">
          {formatPercentNullable(percent, 1)}
        </span>
      </div>
      <MiniQuotaBar
        aria-label={t("accounts.listItem.quotaRemainingAria", { label })}
        percent={percent}
        testId={`mini-quota-track-${label.toLowerCase()}`}
      />
      <div className="text-[10px] text-muted-foreground">
        {formatMiniQuotaResetLabel(resetAt ?? null, t)}
      </div>
    </div>
  );
}

function formatMiniQuotaResetLabel(resetAt: string | null, t: ReturnType<typeof useTranslation>["t"]): string {
  const label = formatQuotaResetLabel(resetAt);
  return label.startsWith("Reset ") ? label : t("accounts.listItem.resetAt", { label });
}
