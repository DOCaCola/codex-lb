import { Badge } from "@/components/ui/badge";
import { CircleDollarSign } from "lucide-react";
import { QuotaRow } from "@/features/accounts/components/quota-display";
import { formatPercentNullable } from "@/utils/formatters";
import { useTranslation } from "react-i18next";
import type { ClaudeAccount } from "./api";

export function ClaudePlan({ account }: { account: ClaudeAccount }) {
  const { t } = useTranslation();
  return (
    <span title={account.state.subscription_error ? t("claude.subscription.retained") : undefined}>
      {t(`claude.subscription.${account.planType}`)}
    </span>
  );
}

const labels = {
  five_hour: "5h",
  seven_day: "Weekly",
  seven_day_opus: "Weekly Opus",
  seven_day_sonnet: "Weekly Sonnet",
};
/** Every quota window a Claude account reports. */
export function ClaudeQuota({ account }: { account: ClaudeAccount }) {
  const windows = account.quota.windows;
  return (
    <div
      className={
        windows.length > 1
          ? "grid grid-cols-1 gap-3 sm:grid-cols-2"
          : "grid grid-cols-1 gap-3"
      }
    >
      {windows.map((window) => (
        <div key={window.name} className="space-y-1">
          <QuotaRow
            label={labels[window.name]}
            percent={window.utilization === null ? null : Math.max(0, 100 - window.utilization)}
            resetAt={window.resetsAt}
          />
          {(window.freshness !== "fresh" ||
            (window.utilization !== null && window.utilization > 100)) && (
            <p className="text-[10px] text-muted-foreground">
              {window.utilization === null
                ? "Unknown"
                : window.utilization > 100
                  ? `${formatPercentNullable(window.utilization, 1)} used`
                  : null}
              {window.freshness === "stale" && " · stale"}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

export function ExtraUsageBadge({ account }: { account: ClaudeAccount }) {
  const { t } = useTranslation();
  if (!account.extraUsageEnabled) return null;
  return (
    <Badge
      variant="outline"
      title={t("claude.extraUsage.title")}
      className="shrink-0 gap-1 border-amber-300 bg-amber-50 px-1.5 text-[11px] text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300"
    >
      <CircleDollarSign className="h-3 w-3" aria-hidden="true" />
      {t("claude.extraUsage.badge")}
    </Badge>
  );
}
