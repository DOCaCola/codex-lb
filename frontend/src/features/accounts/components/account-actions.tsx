import {
  Activity,
  Download,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Trash2,
  Zap,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { AccountPauseButton } from "@/components/account-pause-button";
import { AccountRoutingPolicyControl } from "./routing-policy";
import { Switch } from "@/components/ui/switch";
import { usePermission } from "@/features/auth/hooks/use-auth";
import { formatLimitWarmupWindow } from "@/features/accounts/limit-warmup";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import type {
  AccountRoutingPolicy,
  AccountSummary,
} from "@/features/accounts/schemas";
import {
  formatDateTimeInline,
  formatSingleUnitRemaining,
  formatSlug,
} from "@/utils/formatters";

export type AccountActionsProps = {
  account: AccountSummary;
  busy: boolean;
  readOnly?: boolean;
  modelControls?: ReactNode;
  modelAction?: ReactNode;
  onPause: (accountId: string) => void;
  onResume: (accountId: string) => void;
  onProbe: (accountId: string) => void;
  onDelete: (accountId: string) => void;
  onReauth: () => void;
  onExportAuth: (accountId: string) => void;
  onResetCredit: (accountId: string) => void;
  showResetCreditExpiryBadge?: boolean;
  /** Unknown while settings load; the hint appears only once the global switch is known to be off. */
  limitWarmupGloballyEnabled?: boolean;
  onSecurityWorkAuthorizedChange: (accountId: string, enabled: boolean) => void;
  onLimitWarmupChange: (accountId: string, enabled: boolean) => void;
  onRoutingPolicyChange: (
    accountId: string,
    routingPolicy: AccountRoutingPolicy,
  ) => void;
};

export function AccountActions({
  account,
  busy,
  readOnly = false,
  modelControls,
  modelAction,
  onPause,
  onResume,
  onProbe,
  onDelete,
  onReauth,
  onExportAuth,
  onResetCredit,
  showResetCreditExpiryBadge = true,
  limitWarmupGloballyEnabled,
  onSecurityWorkAuthorizedChange,
  onLimitWarmupChange,
  onRoutingPolicyChange,
}: AccountActionsProps) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  // Credential export is its own permission (`accounts:export`), not part of account writes.
  const canExport = usePermission("accounts:export");
  const showOperatorRecoveryAction =
    account.status === "reauth_required" || account.status === "deactivated";
  // A deactivated account can be returned to active directly: the reactivate
  // endpoint clears the deactivation reason and only refuses
  // `reauth_required`, where the stored refresh token really is unusable.
  const canResume = account.status === "paused" || account.status === "deactivated";
  const probeDisabled =
    busy || readOnly || account.status === "paused" || showOperatorRecoveryAction;
  const resetCountdown = showResetCreditExpiryBadge && account.resetCreditNearestExpiresAt
    ? formatSingleUnitRemaining(account.resetCreditNearestExpiresAt)
    : null;
  const availableResetCredits = account.availableResetCredits ?? 0;
  const hasResetCredits = availableResetCredits > 0;
  const resetCreditDisabled =
    busy ||
    readOnly ||
    account.status === "paused" ||
    showOperatorRecoveryAction;
  const warmup = account.limitWarmup;
  const warmupDetail = warmup
    ? `${formatSlug(warmup.status)} | ${formatLimitWarmupWindow(warmup.window)} | ${formatSlug(warmup.model)} | ${formatDateTimeInline(warmup.completedAt ?? warmup.attemptedAt, dateDisplayFormat)}`
    : t("accounts.listItem.noAttempts");
  const warmupId = `limit-warmup-${account.accountId}`;

  return (
    <div className="space-y-3 border-t pt-4">
      {modelControls}
      {!showOperatorRecoveryAction ? (
        <AccountRoutingPolicyControl
          policy={account.routingPolicy ?? "normal"}
          disabled={busy || readOnly}
          onChange={(policy) => onRoutingPolicyChange(account.accountId, policy)}
        />
      ) : null}

      <label
        htmlFor={`security-work-authorized-${account.accountId}`}
        className="flex min-w-0 items-center justify-between gap-3 rounded-md border px-3 py-2"
      >
        <span className="flex min-w-0 items-center gap-2 text-xs font-medium">
          <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate">{t("accounts.actions.trustedAccess")}</span>
        </span>
        <Switch
          id={`security-work-authorized-${account.accountId}`}
          className="shrink-0"
          checked={account.securityWorkAuthorized ?? false}
          disabled={busy || readOnly}
          onCheckedChange={(checked) =>
            onSecurityWorkAuthorizedChange(account.accountId, checked)
          }
        />
      </label>

      <div className="flex min-w-0 items-center justify-between gap-3 rounded-md border px-3 py-2">
        <div className="min-w-0">
          <label htmlFor={warmupId} className="flex min-w-0 items-center gap-2 text-xs font-medium">
            <Zap className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span className="truncate">{t("settings.routing.limitWarmup.label")}</span>
          </label>
          <p id={`${warmupId}-detail`} className="mt-0.5 truncate pl-5.5 text-[11px] text-muted-foreground">
            {warmupDetail}
          </p>
          {limitWarmupGloballyEnabled === false ? (
            <p className="mt-0.5 pl-5.5 text-[11px] text-amber-600 dark:text-amber-400">
              {t("accounts.actions.limitWarmupGloballyOff")}{" "}
              <Link to="/settings" className="underline underline-offset-2 hover:text-foreground">
                {t("nav.settings")}
              </Link>
            </p>
          ) : null}
        </div>
        <Switch
          id={warmupId}
          className="shrink-0"
          aria-describedby={`${warmupId}-detail`}
          aria-label={t("accounts.actions.limitWarmupFor", {
            account: account.alias?.trim() || account.displayName || account.email,
          })}
          checked={account.limitWarmupEnabled}
          disabled={busy || readOnly}
          onCheckedChange={(checked) => onLimitWarmupChange(account.accountId, checked)}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {(canResume || !showOperatorRecoveryAction) && <AccountPauseButton
          paused={canResume}
          disabled={busy || readOnly}
          onClick={() => canResume ? onResume(account.accountId) : onPause(account.accountId)}
        />}

        {modelAction}

        {showOperatorRecoveryAction ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs"
            onClick={onReauth}
            disabled={busy || readOnly}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {t("common.actions.reauthenticate")}
          </Button>
        ) : null}

        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-xs"
          onClick={() => onProbe(account.accountId)}
          disabled={probeDisabled}
        >
          <Activity className="h-3.5 w-3.5" />
          {t("accounts.actions.forceProbe")}
        </Button>

        {canExport ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs"
            onClick={() => onExportAuth(account.accountId)}
            disabled={busy || readOnly}
          >
            <Download className="h-3.5 w-3.5" />
            {t("common.actions.export")}
          </Button>
        ) : null}

        {hasResetCredits ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="relative h-8 gap-1.5 pr-8 text-xs"
            onClick={() => onResetCredit(account.accountId)}
            disabled={resetCreditDisabled}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            {t("accounts.actions.resetWithCount", { count: availableResetCredits })}
            {resetCountdown ? (
              <span
                aria-hidden="true"
                className={[
                  "pointer-events-none absolute -top-1 right-1 text-[10px] tabular-nums",
                  resetCountdown.expiringSoon
                    ? "text-destructive"
                    : "text-muted-foreground",
                ].join(" ")}
              >
                {resetCountdown.label}
              </span>
            ) : null}
          </Button>
        ) : null}

        <Button
          type="button"
          size="sm"
          variant="destructive"
          className="h-8 gap-1.5 text-xs"
          onClick={() => onDelete(account.accountId)}
          disabled={busy || readOnly}
        >
          <Trash2 className="h-3.5 w-3.5" />
          {t("common.actions.delete")}
        </Button>
      </div>
    </div>
  );
}
