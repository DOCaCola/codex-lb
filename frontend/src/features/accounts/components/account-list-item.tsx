import { ShieldCheck } from "lucide-react";
import { ProviderAccountName } from "@/components/brand/provider-account-name";
import { MiniQuotaRow } from "./quota-display";
import { RoutingPolicyBadge } from "./routing-policy";
import { useTranslation } from "react-i18next";

import { AccountSelectionSurface } from "@/components/account-surfaces";
import { cn } from "@/lib/utils";
import { isEmailLabel } from "@/components/blur-email";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { useAccountQuotaDisplayStore } from "@/hooks/use-account-quota-display";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { useSmoothPercent } from "@/hooks/use-smooth-percent";
import { StatusBadge } from "@/components/status-badge";
import type {
  AccountRoutingPolicy,
  AccountSummary,
} from "@/features/accounts/schemas";
import { normalizeStatus } from "@/utils/account-status";
import { formatCompactAccountId } from "@/utils/account-identifiers";
import {
  formatDateTimeInline,
  formatSlug,
} from "@/utils/formatters";

export type AccountListItemProps = {
  account: AccountSummary;
  selected: boolean;
  showAccountId?: boolean;
  showResetCreditBadge?: boolean;
  onSelect: (accountId: string) => void;
};

export function AccountListItem({
  account,
  selected,
  showAccountId = false,
  showResetCreditBadge = true,
  onSelect,
}: AccountListItemProps) {
  const { t } = useTranslation();
  const blurred = usePrivacyStore((s) => s.blurred);
  const quotaDisplay = useAccountQuotaDisplayStore((s) => s.quotaDisplay);
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  const status = normalizeStatus(account.status);
  const title = account.displayName || account.email;
  const titleIsEmail = isEmailLabel(title, account.email);
  const emailSubtitle = account.displayName && account.displayName !== account.email
    ? account.email
    : null;
  const workspaceLabel = account.chatgptAccountId || account.workspaceLabel || account.workspaceId || t("accounts.detail.unknownWorkspace");
  const seatLabel = account.seatType ? ` | ${formatSlug(account.seatType)}` : "";
  const slotSubtitle = `${formatSlug(account.planType)} | ${workspaceLabel}${seatLabel}`;
  const idSuffix = showAccountId ? ` | ID ${formatCompactAccountId(account.accountId)}` : "";
  const primaryState = useSmoothPercent(account.usage?.primaryRemainingPercent ?? null);
  const secondaryState = useSmoothPercent(account.usage?.secondaryRemainingPercent ?? null);
  const monthlyState = useSmoothPercent(account.usage?.monthlyRemainingPercent ?? null);
  const primary = primaryState.percent;
  const secondary = secondaryState.percent;
  const monthly = monthlyState.percent;
  const hasPrimaryWindow =
    account.windowMinutesPrimary != null ||
    primary !== null ||
    account.resetAtPrimary != null ||
    primaryState.everKnown;
  const hasSecondaryWindow =
    account.windowMinutesSecondary != null ||
    secondary !== null ||
    account.resetAtSecondary != null ||
    secondaryState.everKnown;
  const hasMonthlyWindow =
    account.windowMinutesMonthly != null ||
    monthly !== null ||
    account.resetAtMonthly != null ||
    monthlyState.everKnown;
  const monthlyOnly = hasMonthlyWindow && !hasPrimaryWindow && !hasSecondaryWindow;
  const showMonthlyRow = monthlyOnly;
  const showPrimaryRow =
    !monthlyOnly && hasPrimaryWindow && (quotaDisplay !== "weekly" || !hasSecondaryWindow);
  const showSecondaryRow =
    !monthlyOnly && hasSecondaryWindow && (quotaDisplay !== "5h" || !hasPrimaryWindow);
  const visibleQuotaRows = Number(showPrimaryRow) + Number(showSecondaryRow) + Number(showMonthlyRow);
  const showRoutingPolicy = status !== "reauth" && status !== "deactivated";
  const warmupLabel = account.limitWarmupEnabled ? t("accounts.listItem.warmupOn") : t("accounts.listItem.warmupOff");
  const warmupMeta = account.limitWarmup
    ? `${formatSlug(account.limitWarmup.status)} | ${formatSlug(account.limitWarmup.model)} | ${formatDateTimeInline(account.limitWarmup.completedAt ?? account.limitWarmup.attemptedAt, dateDisplayFormat)}`
    : t("accounts.listItem.noAttempts");
  const availableResetCredits = account.availableResetCredits ?? 0;
  const resetBadgeLabel = availableResetCredits > 99 ? "99+" : String(availableResetCredits);
  const statusEligibilityHint = status === "active" ? t("accounts.listItem.statusActiveHint") : undefined;

  return (
    <AccountSelectionSurface
      selected={selected}
      // Native title on the focusable row doubles as the accessible
      // description, so keyboard and screen-reader users get the
      // status-vs-eligibility hint without hovering the badge.
      title={statusEligibilityHint}
      onClick={() => onSelect(account.accountId)}
    >
      {showResetCreditBadge && availableResetCredits > 0 ? (
        <span className="absolute -top-1 -right-1 grid h-5 min-w-[1.25rem] place-items-center rounded-full bg-primary px-1 text-[10px] font-medium text-primary-foreground">
          {resetBadgeLabel}
        </span>
      ) : null}
      <div className="flex items-start gap-2.5">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">
            <ProviderAccountName provider="codex">
            {titleIsEmail && blurred ? (
              <span className="privacy-blur">{title}</span>
            ) : (
              title
            )}
            </ProviderAccountName>
          </p>
          <p className="truncate text-xs text-muted-foreground" title={showAccountId ? t("accounts.detail.accountIdTitle", { accountId: account.accountId }) : undefined}>
            {emailSubtitle ? <><span className={blurred ? "privacy-blur" : undefined}>{emailSubtitle}</span> | {slotSubtitle}{idSuffix}</> : <>{slotSubtitle}{idSuffix}</>}
          </p>
        </div>
        {showRoutingPolicy ? (
          <RoutingPolicyBadge
            policy={account.routingPolicy as AccountRoutingPolicy | undefined}
          />
        ) : null}
        {account.securityWorkAuthorized === true ? (
          <ShieldCheck
            className="h-3.5 w-3.5 text-emerald-600"
            aria-label={t("accounts.actions.trustedAccess")}
          />
        ) : null}
        <StatusBadge status={status} title={statusEligibilityHint} />
      </div>
      <div
        className={cn(
          "mt-2 grid gap-2",
          visibleQuotaRows > 1 ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-1",
        )}
      >
        {showMonthlyRow ? (
          <MiniQuotaRow
            label={t("common.quota.monthly")}
            percent={monthly}
            resetAt={account.resetAtMonthly}
          />
        ) : null}
        {showPrimaryRow ? (
          <MiniQuotaRow
            label="5h"
            percent={primary}
            resetAt={account.resetAtPrimary}
          />
        ) : null}
        {showSecondaryRow ? (
          <MiniQuotaRow
            label={t("common.quota.weekly")}
            percent={secondary}
            resetAt={account.resetAtSecondary}
          />
        ) : null}
      </div>
      <div className="mt-2 flex min-w-0 items-center justify-between gap-2 text-[10px] text-muted-foreground">
        <span className="shrink-0">{warmupLabel}</span>
        <span className="min-w-0 truncate">{warmupMeta}</span>
      </div>
    </AccountSelectionSurface>
  );
}
