import { ExternalLink, Play, RotateCcw, Zap } from "lucide-react";
import {
  CardQuotaGrid,
  QuotaBar,
} from "@/features/accounts/components/quota-display";
import { useTranslation } from "react-i18next";

import { usePrivacyStore } from "@/hooks/use-privacy";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { useSmoothPercent } from "@/hooks/use-smooth-percent";
import { StatusBadge } from "@/components/status-badge";
import {
  AccountCardAction,
  AccountCardNotice,
  AccountCardSurface,
} from "@/components/account-surfaces";
import {
  accountSubscriptionCredits,
  formatCreditValue,
  formatPurchasedCredits,
} from "@/features/dashboard/account-credit-display";
import { cn } from "@/lib/utils";
import type { AccountSummary } from "@/features/dashboard/schemas";
import { formatCompactAccountId } from "@/utils/account-identifiers";
import { normalizeStatus } from "@/utils/account-status";
import {
  formatDateTimeInline,
  formatQuotaResetLabel,
  formatSingleUnitRemaining,
  formatSlug,
} from "@/utils/formatters";

export type AccountAction =
  | "details"
  | "resume"
  | "reauth"
  | "warmup-toggle"
  | "reset-credit";

export type AccountCardProps = {
  account: AccountSummary;
  showAccountId?: boolean;
  readOnly?: boolean;
  onAction?: (account: AccountSummary, action: AccountAction) => void;
};

function formatWarmupWindow(window: string): string {
  return window === "primary" || window === "primary_idle" ? "5h" : "weekly";
}

export function AccountCard({
  account,
  showAccountId = false,
  readOnly = false,
  onAction,
}: AccountCardProps) {
  const { t } = useTranslation();
  const blurred = usePrivacyStore((s) => s.blurred);
  const dateDisplayFormat = useDateDisplayFormatStore(
    (s) => s.dateDisplayFormat,
  );
  const status = normalizeStatus(account.status);
  const primaryState = useSmoothPercent(
    account.usage?.primaryRemainingPercent ?? null,
  );
  const secondaryState = useSmoothPercent(
    account.usage?.secondaryRemainingPercent ?? null,
  );
  const monthlyState = useSmoothPercent(
    account.usage?.monthlyRemainingPercent ?? null,
  );
  const primaryRemaining = primaryState.percent;
  const secondaryRemaining = secondaryState.percent;
  const monthlyRemaining = monthlyState.percent;
  const hasPrimaryWindow =
    account.windowMinutesPrimary != null || primaryState.everKnown;
  const hasSecondaryWindow =
    account.windowMinutesSecondary != null || secondaryState.everKnown;
  const hasMonthlyWindow =
    account.windowMinutesMonthly != null || monthlyState.everKnown;
  const weeklyOnly = !hasPrimaryWindow && hasSecondaryWindow;
  const monthlyOnly =
    hasMonthlyWindow && !hasPrimaryWindow && !hasSecondaryWindow;
  const subscriptionCreditsLabel = formatCreditValue(
    accountSubscriptionCredits(account),
  );
  const purchasedCreditsLabel = formatPurchasedCredits(
    account,
    t("common.states.unlimited"),
  );

  const primaryReset = formatQuotaResetLabel(account.resetAtPrimary ?? null);
  const secondaryReset = formatQuotaResetLabel(
    account.resetAtSecondary ?? null,
  );
  const monthlyReset = formatQuotaResetLabel(account.resetAtMonthly ?? null);

  const title = account.displayName || account.email;
  const compactId = formatCompactAccountId(account.accountId);
  const planLabel = formatSlug(account.planType);
  const emailSubtitle =
    account.displayName && account.displayName !== account.email
      ? account.email
      : null;
  const idSuffix = showAccountId ? ` | ID ${compactId}` : "";
  const warmupStatus = account.limitWarmupEnabled
    ? t("accounts.listItem.warmupOn")
    : t("accounts.listItem.warmupOff");
  const warmupToggleLabel = account.limitWarmupEnabled
    ? t("dashboard.accounts.disableWarmupFor", { account: title })
    : t("dashboard.accounts.enableWarmupFor", { account: title });
  const warmupDetail = account.limitWarmup
    ? `${formatSlug(account.limitWarmup.status)} | ${formatWarmupWindow(account.limitWarmup.window)} | ${formatSlug(account.limitWarmup.model)} | ${formatDateTimeInline(account.limitWarmup.completedAt ?? account.limitWarmup.attemptedAt, dateDisplayFormat)}`
    : t("accounts.listItem.noAttempts");
  const availableResetCredits = account.availableResetCredits ?? 0;
  const hasResetCredits = availableResetCredits > 0;
  const resetCreditDisabled =
    readOnly ||
    status === "paused" ||
    status === "reauth" ||
    status === "deactivated";
  const resetCountdown = account.resetCreditNearestExpiresAt
    ? formatSingleUnitRemaining(account.resetCreditNearestExpiresAt)
    : null;
  const resetButtonTitle = resetCreditDisabled
    ? status === "paused"
      ? t("dashboard.accounts.resetCreditTitles.resumeRequired")
      : status === "reauth" || status === "deactivated"
        ? t("dashboard.accounts.resetCreditTitles.reauthRequired")
        : t("dashboard.accounts.resetCreditTitles.unavailable")
    : resetCountdown
      ? t("dashboard.accounts.resetCreditTitles.withCountdown", {
          count: availableResetCredits,
          countdown: resetCountdown.label,
        })
      : t("dashboard.accounts.resetWithCount", {
          count: availableResetCredits,
        });

  const actions = (
    <>
      <AccountCardAction
        type="button"
        onClick={() => onAction?.(account, "details")}
      >
        <ExternalLink className="h-3 w-3" />
        {t("common.actions.details")}
      </AccountCardAction>
      {hasResetCredits ? (
        <AccountCardAction
          type="button"
          className="relative pr-8"
          title={resetButtonTitle}
          disabled={resetCreditDisabled}
          onClick={() => onAction?.(account, "reset-credit")}
        >
          <RotateCcw className="h-3 w-3" />
          {t("dashboard.accounts.resetWithCount", {
            count: availableResetCredits,
          })}
          {resetCountdown ? (
            <span
              aria-hidden="true"
              className={cn(
                "pointer-events-none absolute -top-1 right-1 text-[10px] tabular-nums",
                resetCountdown.expiringSoon
                  ? "text-destructive"
                  : "text-muted-foreground",
              )}
            >
              {resetCountdown.label}
            </span>
          ) : null}
        </AccountCardAction>
      ) : null}
      {(status === "paused" || status === "deactivated") && (
        <AccountCardAction
          type="button"
          className="text-emerald-600 hover:bg-emerald-500/10 hover:text-emerald-700 dark:text-emerald-400 dark:hover:text-emerald-300"
          disabled={readOnly}
          onClick={() => onAction?.(account, "resume")}
        >
          <Play className="h-3 w-3" />
          {t("common.actions.resume")}
        </AccountCardAction>
      )}
      {(status === "reauth" || status === "deactivated") && (
        <AccountCardAction
          type="button"
          className="text-amber-600 hover:bg-amber-500/10 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
          disabled={readOnly}
          onClick={() => onAction?.(account, "reauth")}
        >
          <RotateCcw className="h-3 w-3" />
          {t("common.actions.reauthenticateShort")}
        </AccountCardAction>
      )}
    </>
  );

  return (
    <AccountCardSurface
      data-testid="codex-account-card"
      title={blurred ? <span className="privacy-blur">{title}</span> : title}
      subtitle={
        <>
          {planLabel}
          {!emailSubtitle ? idSuffix : ""}
        </>
      }
      description={
        emailSubtitle ? (
          <>
            <span className={blurred ? "privacy-blur" : undefined}>
              {emailSubtitle}
            </span>
            {idSuffix}
          </>
        ) : undefined
      }
      descriptionTitle={
        showAccountId
          ? t("accounts.detail.accountIdTitle", {
              accountId: account.accountId,
            })
          : undefined
      }
      status={<StatusBadge status={status} />}
      actions={actions}
    >
      {/* Quota bars */}
      <CardQuotaGrid columns={weeklyOnly || monthlyOnly ? 1 : 2}>
        {monthlyOnly ? (
          <QuotaBar
            label={t("common.time.monthly")}
            percent={monthlyRemaining}
            resetLabel={monthlyReset}
          />
        ) : (
          <>
            {!weeklyOnly && (
              <QuotaBar
                label="5h"
                percent={primaryRemaining}
                resetLabel={primaryReset}
              />
            )}
            <QuotaBar
              label={t("common.time.weekly")}
              percent={secondaryRemaining}
              resetLabel={secondaryReset}
            />
          </>
        )}
      </CardQuotaGrid>

      <AccountCardNotice>
        <div className="min-w-0">
          <p className="font-medium">{warmupStatus}</p>
          <p className="truncate text-[11px] text-muted-foreground">
            {warmupDetail}
          </p>
        </div>
        <AccountCardAction
          type="button"
          className={cn(
            account.limitWarmupEnabled
              ? "text-primary hover:bg-primary/10 hover:text-primary"
              : "text-muted-foreground hover:text-foreground",
          )}
          aria-label={warmupToggleLabel}
          disabled={readOnly}
          onClick={() => onAction?.(account, "warmup-toggle")}
        >
          <Zap className="h-3 w-3" aria-hidden="true" />
          {account.limitWarmupEnabled
            ? t("common.states.on")
            : t("common.states.off")}
        </AccountCardAction>
      </AccountCardNotice>

      <div className="grid gap-1 text-xs text-muted-foreground">
        <p>
          {t("dashboard.accounts.subscriptionCredits")}:{" "}
          <span className="font-medium tabular-nums text-foreground">
            {subscriptionCreditsLabel}
          </span>
        </p>
        <p>
          {t("dashboard.accounts.purchasedCredits")}:{" "}
          <span className="font-medium tabular-nums text-foreground">
            {purchasedCreditsLabel}
          </span>
        </p>
      </div>
    </AccountCardSurface>
  );
}
