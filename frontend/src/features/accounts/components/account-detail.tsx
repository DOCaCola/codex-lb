import { Activity, Clock, Download, KeyRound, PauseCircle, RefreshCw, RotateCcw, ShieldCheck, Trash2, Zap } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { AccountPauseButton } from "@/components/account-pause-button";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { cn } from "@/lib/utils";
import { usePermission } from "@/features/auth/hooks/use-auth";
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { AccountActivityCard } from "@/features/accounts/components/account-activity-card";
import { AccountColorPicker } from "@/features/accounts/components/account-color-picker";
import { AccountNameEditor } from "@/features/accounts/components/account-name-editor";
import { AccountNotePanel } from "@/features/accounts/components/account-note-panel";
import { AccountProxyBinding } from "@/features/accounts/components/account-proxy-binding";
import { AccountSubscriptionEndPanel } from "@/features/accounts/components/account-subscription-end-panel";
import { AccountUsagePanel } from "@/features/accounts/components/account-usage-panel";
import { CodexModelControls } from "@/features/accounts/components/codex-model-controls";
import { AccountCreditPolicyControl } from "@/features/accounts/components/credit-policy";
import {
  DetailBanner,
  DetailCard,
  DetailParts,
  DetailRows,
  ProviderDetail,
  SettingRow,
  type DetailMenuItem,
} from "@/features/accounts/components/provider-detail";
import { useCommonMenuItems } from "@/features/accounts/hooks/use-common-menu-items";
import { AccountRoutingPolicyControl } from "@/features/accounts/components/routing-policy";
import { useAccountTrends } from "@/features/accounts/hooks/use-accounts";
import { useSummaryContext } from "@/features/accounts/hooks/use-summary-context";
import { formatLimitWarmupWindow } from "@/features/accounts/limit-warmup";
import { summarizeEntry } from "@/features/accounts/provider-summary";
import type {
  AccountCreditPolicy,
  AccountRoutingPolicy,
  AccountSummary,
  AccountUsageResetCredits,
} from "@/features/accounts/schemas";
import type {
  AccountProxyBindingRequest,
  UpstreamProxyAdmin,
  UpstreamProxyEndpointTestResponse,
} from "@/features/settings/schemas";
import { formatCompactAccountId } from "@/utils/account-identifiers";
import {
  formatAccessTokenLabel,
  formatDateTimeInline,
  formatIdTokenLabel,
  formatRefreshTokenLabel,
  formatTimeRemaining,
  formatSlug,
} from "@/utils/formatters";

export type AccountDetailProps = {
  account: AccountSummary;
  busy: boolean;
  readOnly?: boolean;
  onPause: (accountId: string) => void;
  onResume: (accountId: string) => void;
  onProbe: (accountId: string) => void;
  onResetUsage: (accountId: string) => void;
  onSetAlias: (accountId: string, alias: string | null) => Promise<unknown>;
  onDelete: (accountId: string) => void;
  onReauth: () => void;
  onExportAuth: (accountId: string) => void;
  onResetCredit: (accountId: string) => void;
  showResetCreditExpiryBadge?: boolean;
  /** Unknown while settings load; the hint appears only once the global switch is known to be off. */
  limitWarmupGloballyEnabled?: boolean;
  onLimitWarmupChange: (accountId: string, enabled: boolean) => void;
  onRoutingPolicyChange: (accountId: string, routingPolicy: AccountRoutingPolicy) => void;
  onCreditPolicyChange: (accountId: string, creditPolicy: AccountCreditPolicy) => void;
  onSecurityWorkAuthorizedChange: (accountId: string, enabled: boolean) => void;
  upstreamProxyAdmin?: UpstreamProxyAdmin | null;
  onProxyBindingSave?: (accountId: string, payload: AccountProxyBindingRequest) => Promise<unknown>;
  onProxyEndpointTest?: (endpointId: string) => Promise<UpstreamProxyEndpointTestResponse>;
  resetCredits?: AccountUsageResetCredits | null;
  resetCreditsLoading?: boolean;
  resetCreditsUnavailable?: boolean;
};

/** Account page of a Codex account. */
export function AccountDetail({
  account,
  busy,
  readOnly = false,
  onPause,
  onResume,
  onProbe,
  onResetUsage,
  onSetAlias,
  onDelete,
  onReauth,
  onExportAuth,
  onResetCredit,
  showResetCreditExpiryBadge = true,
  limitWarmupGloballyEnabled,
  onLimitWarmupChange,
  onRoutingPolicyChange,
  onCreditPolicyChange,
  onSecurityWorkAuthorizedChange,
  upstreamProxyAdmin = null,
  onProxyBindingSave,
  onProxyEndpointTest,
  resetCredits = null,
  resetCreditsLoading = false,
  resetCreditsUnavailable = false,
}: AccountDetailProps) {
  const { t } = useTranslation();
  const { data: trends } = useAccountTrends(account.accountId);
  const accountColors = useAccountColorHexes();
  const blurred = usePrivacyStore((s) => s.blurred);
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  // Credential export is its own permission (accounts:export), not part of account writes.
  const canExport = usePermission("accounts:export");
  const summary = summarizeEntry({ kind: "codex", account }, useSummaryContext());
  const commonMenu = useCommonMenuItems(account.accountId, summary.logsAccountId);
  const color = accountColors.accounts.get(account.accountId);
  const disabled = busy || readOnly;

  const recovery = account.status === "reauth_required" || account.status === "deactivated";
  // A deactivated account can be returned to active directly: the reactivate
  // endpoint clears the deactivation reason and only refuses reauth_required,
  // where the stored refresh token really is unusable.
  const canResume = account.status === "paused" || account.status === "deactivated";
  const paused = account.status === "paused";
  const limitReached = summary.status === "limited" || summary.status === "exceeded";
  const availableResetCredits = account.availableResetCredits ?? 0;
  const resetCountdown =
    showResetCreditExpiryBadge && account.resetCreditNearestExpiresAt
      ? formatTimeRemaining(account.resetCreditNearestExpiresAt)
      : null;
  const resetCreditDisabled = disabled || paused || recovery;
  const usageResetDisabled = disabled || paused || recovery || (resetCredits?.availableCount ?? 0) <= 0;

  const resetButton =
    availableResetCredits > 0 ? (
      <Button
        type="button"
        size="sm"
        variant="outline"
        className={cn("relative h-8 gap-1.5 text-xs", resetCountdown && "pr-8")}
        onClick={() => onResetCredit(account.accountId)}
        disabled={resetCreditDisabled}
      >
        <RotateCcw className="h-3.5 w-3.5" />
        {t("accounts.actions.resetWithCount", { count: availableResetCredits })}
        {resetCountdown ? (
          <span
            aria-hidden="true"
            className={cn(
              "pointer-events-none absolute -top-1 right-1 text-[10px] tabular-nums",
              resetCountdown.expiringSoon ? "text-destructive" : "text-muted-foreground",
            )}
          >
            {resetCountdown.label}
          </span>
        ) : null}
      </Button>
    ) : null;
  const reauthButton = (
    <Button type="button" size="sm" variant="outline" className="h-8 gap-1.5 text-xs" onClick={onReauth} disabled={disabled}>
      <RefreshCw className="h-3.5 w-3.5" />
      {t("common.actions.reauthenticate")}
    </Button>
  );

  const banner = recovery ? (
    <DetailBanner tone="bad" icon={<KeyRound />} action={reauthButton}>
      {t("providers.banner.recovery")}
    </DetailBanner>
  ) : paused ? (
    <DetailBanner tone="off" icon={<PauseCircle />}>
      {t("providers.banner.paused")}
    </DetailBanner>
  ) : limitReached ? (
    <DetailBanner tone={summary.tone === "bad" ? "bad" : "warn"} icon={<Clock />} action={resetButton}>
      {summary.notice?.text ?? t("providers.banner.limited")}
    </DetailBanner>
  ) : null;

  const menu: DetailMenuItem[] = [
    ...(canExport
      ? [
          {
            key: "export",
            label: t("providers.detail.exportCredentials"),
            icon: <Download />,
            disabled,
            onSelect: () => onExportAuth(account.accountId),
          },
        ]
      : []),
    ...commonMenu,
    {
      key: "delete",
      label: t("providers.detail.deleteAccount"),
      icon: <Trash2 />,
      destructive: true,
      disabled,
      onSelect: () => onDelete(account.accountId),
    },
  ];

  const workspaceLabel =
    account.chatgptAccountId || account.workspaceLabel || account.workspaceId || t("accounts.detail.unknownWorkspace");
  const compactId = formatCompactAccountId(account.accountId);
  const warmup = account.limitWarmup;
  const warmupDetail = warmup
    ? [
        formatSlug(warmup.status),
        formatLimitWarmupWindow(warmup.window),
        formatSlug(warmup.model),
        formatDateTimeInline(warmup.completedAt ?? warmup.attemptedAt, dateDisplayFormat),
      ].join(" | ")
    : t("accounts.listItem.noAttempts");
  const warmupId = "limit-warmup-" + account.accountId;
  const trustedAccessId = "security-work-authorized-" + account.accountId;

  return (
    <ProviderDetail
      key={account.accountId}
      accountId={account.accountId}
      data-testid="codex-account-detail"
      provider="codex"
      color={color}
      name={
        <AccountNameEditor
          key={account.accountId}
          value={account.alias ?? ""}
          inputId="account-alias"
          labels={{
            edit: t("accounts.detail.editAlias"),
            input: t("accounts.detail.aliasLabel"),
            save: t("accounts.detail.saveAlias"),
            cancel: t("common.cancel"),
          }}
          placeholder={t("accounts.detail.aliasPlaceholder")}
          help={t("accounts.detail.aliasHelp")}
          allowEmpty
          disabled={disabled}
          accessory={<AccountColorPicker target={{ accountId: account.accountId }} disabled={disabled} />}
          onSave={(value) => onSetAlias(account.accountId, value)}
        >
          <span className={cn(summary.blurName && blurred && "privacy-blur")}>{summary.name}</span>
        </AccountNameEditor>
      }
      plan={summary.plan}
      planKey={summary.planKey}
      status={summary.status}
      subline={[
        summary.subtitle ? <span className={cn(blurred && "privacy-blur")}>{summary.subtitle}</span> : null,
        account.seatType ? workspaceLabel + " · " + formatSlug(account.seatType) : workspaceLabel,
        <span title={t("accounts.detail.accountIdTitle", { accountId: account.accountId })}>ID {compactId}</span>,
      ]}
      actions={
        <>
          {canResume || !recovery ? (
            <AccountPauseButton
              paused={canResume}
              disabled={disabled}
              onClick={() => (canResume ? onResume(account.accountId) : onPause(account.accountId))}
            />
          ) : null}
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs"
            onClick={() => onProbe(account.accountId)}
            disabled={disabled || paused || recovery}
          >
            <Activity className="h-3.5 w-3.5" />
            {t("accounts.actions.forceProbe")}
          </Button>
          {limitReached && !recovery && !paused ? null : resetButton}
        </>
      }
      menu={menu}
      banner={banner}
      main={
        <>
          <DetailCard title={t("accounts.usage.title")} data-testid="account-usage">
            <AccountUsagePanel
              account={account}
              trends={trends}
              resetCredits={resetCredits}
              resetCreditsLoading={resetCreditsLoading}
              resetCreditsUnavailable={resetCreditsUnavailable}
              resetDisabled={usageResetDisabled}
              onReset={onResetUsage}
            />
          </DetailCard>
          <AccountActivityCard activityKey={summary.activityKey} logsAccountId={summary.logsAccountId} color={color} />
        </>
      }
      side={
        <>
          <DetailCard title={t("accounts.tokenInfo.title")} action={recovery ? null : reauthButton}>
            <DetailRows
              rows={[
                { label: t("accounts.tokenInfo.access"), value: formatAccessTokenLabel(account.auth) },
                { label: t("accounts.tokenInfo.refresh"), value: formatRefreshTokenLabel(account.auth) },
                { label: t("accounts.tokenInfo.idToken"), value: formatIdTokenLabel(account.auth) },
              ]}
            />
          </DetailCard>
          <DetailCard title={t("providers.detail.details")}>
            <DetailParts>
              <AccountNotePanel target={{ accountId: account.accountId }} readOnly={readOnly} />
              <AccountSubscriptionEndPanel target={{ accountId: account.accountId }} readOnly={readOnly} />
            </DetailParts>
          </DetailCard>
        </>
      }
      settings={
        <>
          <DetailCard title={t("providers.detail.routing")}>
            <CodexModelControls key={account.accountId} accountId={account.accountId} name={summary.name} disabled={disabled}>
              {({ mode, action }) => (
                <DetailParts>
                  {!recovery ? (
                    <AccountRoutingPolicyControl
                      policy={account.routingPolicy ?? "normal"}
                      disabled={disabled}
                      onChange={(policy) => onRoutingPolicyChange(account.accountId, policy)}
                    />
                  ) : null}
                  {!recovery ? (
                    <AccountCreditPolicyControl
                      policy={account.creditPolicy}
                      disabled={disabled}
                      onChange={(policy) => onCreditPolicyChange(account.accountId, policy)}
                    />
                  ) : null}
                  <SettingRow
                    label={t("settings.routing.limitWarmup.label")}
                    htmlFor={warmupId}
                    icon={<Zap className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
                    description={
                      <>
                        <p id={warmupId + "-detail"}>{warmupDetail}</p>
                        {limitWarmupGloballyEnabled === false ? (
                          <p className="text-amber-600 dark:text-amber-400">
                            {t("accounts.actions.limitWarmupGloballyOff")}{" "}
                            <Link to="/settings" className="underline underline-offset-2 hover:text-foreground">
                              {t("nav.settings")}
                            </Link>
                          </p>
                        ) : null}
                      </>
                    }
                    control={
                      <Switch
                        id={warmupId}
                        aria-describedby={warmupId + "-detail"}
                        aria-label={t("accounts.actions.limitWarmupFor", { account: summary.name })}
                        checked={account.limitWarmupEnabled}
                        disabled={disabled}
                        onCheckedChange={(checked) => onLimitWarmupChange(account.accountId, checked)}
                      />
                    }
                  />
                  <SettingRow
                    label={t("accounts.actions.trustedAccess")}
                    htmlFor={trustedAccessId}
                    icon={<ShieldCheck className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
                    control={
                      <Switch
                        id={trustedAccessId}
                        checked={account.securityWorkAuthorized ?? false}
                        disabled={disabled}
                        onCheckedChange={(checked) => onSecurityWorkAuthorizedChange(account.accountId, checked)}
                      />
                    }
                  />
                  <SettingRow label={t("providers.detail.models")} control={action}>
                    {mode}
                  </SettingRow>
                </DetailParts>
              )}
            </CodexModelControls>
          </DetailCard>
          {onProxyBindingSave ? (
            <AccountProxyBinding
              account={account}
              admin={upstreamProxyAdmin}
              busy={busy}
              readOnly={readOnly}
              onSave={onProxyBindingSave}
              onTestEndpoint={onProxyEndpointTest}
            />
          ) : null}
        </>
      }
    />
  );
}
