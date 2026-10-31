import { Link } from "react-router-dom";
import { ProviderAccountName } from "@/components/brand/provider-account-name";
import {
  AccountCardAction,
  AccountCardSurface,
} from "@/components/account-surfaces";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { CircleDollarSign, ExternalLink } from "lucide-react";
import {
  CardQuotaGrid,
  QuotaBar,
  QuotaRow,
} from "@/features/accounts/components/quota-display";
import {
  formatPercentNullable,
  formatQuotaResetLabel,
} from "@/utils/formatters";
import { useTranslation } from "react-i18next";
import { usePrivacyStore } from "@/hooks/use-privacy";
import type { ClaudeAccount } from "./api";
import { normalizeStatus } from "@/utils/account-status";

import { claudeStatus } from "./display-values";

export function ClaudeName({ account, color }: { account: ClaudeAccount; color?: string }) {
  const blurred = usePrivacyStore((s) => s.blurred);
  return (
    <ProviderAccountName provider="claude" color={color}>
      <span className={blurred ? "privacy-blur" : undefined}>{account.name}</span>
    </ProviderAccountName>
  );
}

export function ClaudePlan({ account }: { account: ClaudeAccount }) {
  const { t } = useTranslation();
  return (
    <span title={account.state.subscription_error ? t("claude.subscription.retained") : undefined}>
      {t(`claude.subscription.${account.planType}`)}
    </span>
  );
}

const labels = {
  five_hour: "5-hour",
  seven_day: "Weekly",
  seven_day_opus: "Weekly Opus",
  seven_day_sonnet: "Weekly Sonnet",
};
/** Quota windows of a Claude account: every reported window in detail, the 5-hour and weekly windows on a card. */
export function ClaudeQuota({
  account,
  detailed = false,
}: {
  account: ClaudeAccount;
  detailed?: boolean;
}) {
  const windows = account.quota.windows.filter(
    (window) => detailed || window.name === "five_hour" || window.name === "seven_day",
  );
  const content = windows.map((window) => {
    const percent =
      window.utilization === null
        ? null
        : Math.max(0, 100 - window.utilization);
    const label = window.name === "five_hour" ? "5h" : labels[window.name];
    return (
      <div key={window.name} className="space-y-1">
        {detailed ? (
          <QuotaRow label={label} percent={percent} resetAt={window.resetsAt} />
        ) : (
          <QuotaBar
            label={label}
            percent={percent}
            resetLabel={formatQuotaResetLabel(window.resetsAt)}
          />
        )}
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
    );
  });
  if (!detailed)
    return (
      <CardQuotaGrid columns={windows.length > 1 ? 2 : 1}>
        {content}
      </CardQuotaGrid>
    );
  return (
    <div
      className={
        windows.length > 1
          ? "grid grid-cols-1 gap-3 sm:grid-cols-2"
          : "grid grid-cols-1 gap-3"
      }
    >
      {content}
    </div>
  );
}

export function ClaudeAccountCard({ account, color }: { account: ClaudeAccount; color?: string }) {
  const { t } = useTranslation();
  return (
    <AccountCardSurface
      data-testid="claude-account-card"
      title={<ClaudeName account={account} color={color} />}
      subtitle={<>Claude · <ClaudePlan account={account} /></>}
      status={
        <span className="flex items-center gap-2">
          <ExtraUsageBadge account={account} />
          <StatusBadge status={normalizeStatus(claudeStatus(account))} />
        </span>
      }
      actions={
        <AccountCardAction asChild>
          <Link to={`/providers/${encodeURIComponent(account.id)}`}>
            <ExternalLink className="h-3 w-3" />
            {t("common.actions.details")}
          </Link>
        </AccountCardAction>
      }
    >
      <ClaudeQuota account={account} />
    </AccountCardSurface>
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
