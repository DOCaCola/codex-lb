import { User } from "lucide-react";
import { useTranslation } from "react-i18next";

import { isEmailLabel } from "@/components/blur-email";
import { cn } from "@/lib/utils";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { AccountActions } from "@/features/accounts/components/account-actions";
import { AccountColorPicker } from "@/features/accounts/components/account-color-picker";
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { CodexModelControls } from "./codex-model-controls";
import { AccountNameEditor } from "@/features/accounts/components/account-name-editor";
import { ProviderAccountName } from "@/components/brand/provider-account-name";
import { AccountProxyBinding } from "@/features/accounts/components/account-proxy-binding";
import { AccountTokenInfo } from "@/features/accounts/components/account-token-info";
import { AccountUsagePanel } from "@/features/accounts/components/account-usage-panel";
import type {
  AccountCreditPolicy,
  AccountRoutingPolicy,
  AccountSummary,
  AccountUsageResetCredits,
} from "@/features/accounts/schemas";
import { useAccountTrends } from "@/features/accounts/hooks/use-accounts";
import type {
  AccountProxyBindingRequest,
  UpstreamProxyAdmin,
  UpstreamProxyEndpointTestResponse,
} from "@/features/settings/schemas";
import { formatCompactAccountId } from "@/utils/account-identifiers";
import { formatSlug } from "@/utils/formatters";

export type AccountDetailProps = {
  account: AccountSummary | null;
  showAccountId?: boolean;
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
  limitWarmupGloballyEnabled?: boolean;
  onLimitWarmupChange: (accountId: string, enabled: boolean) => void;
  onRoutingPolicyChange: (
    accountId: string,
    routingPolicy: AccountRoutingPolicy,
  ) => void;
  onCreditPolicyChange: (
    accountId: string,
    creditPolicy: AccountCreditPolicy,
  ) => void;
  onSecurityWorkAuthorizedChange: (accountId: string, enabled: boolean) => void;
  upstreamProxyAdmin?: UpstreamProxyAdmin | null;
  onProxyBindingSave?: (accountId: string, payload: AccountProxyBindingRequest) => Promise<unknown>;
  onProxyEndpointTest?: (endpointId: string) => Promise<UpstreamProxyEndpointTestResponse>;
  resetCredits?: AccountUsageResetCredits | null;
  resetCreditsLoading?: boolean;
  resetCreditsUnavailable?: boolean;
};

export function AccountDetail({
  account,
  showAccountId = false,
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
  const { data: trends } = useAccountTrends(account?.accountId ?? null);
  const accountColors = useAccountColorHexes();
  const blurred = usePrivacyStore((s) => s.blurred);

  if (!account) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed p-12">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
          <User className="h-5 w-5 text-muted-foreground" />
        </div>
        <p className="mt-3 text-sm font-medium text-muted-foreground">
          {t("accounts.detail.emptyTitle")}
        </p>
        <p className="mt-1 text-xs text-muted-foreground/70">
          {t("accounts.detail.emptyDescription")}
        </p>
      </div>
    );
  }

  const aliasLabel = account.alias?.trim() ?? "";
  const localLabel = aliasLabel || account.displayName || account.email;
  const labelIsEmail = !aliasLabel && isEmailLabel(localLabel, account.email);
  const compactId = formatCompactAccountId(account.accountId);
  const emailSubtitle =
    aliasLabel || (account.displayName && account.displayName !== account.email)
      ? account.email
      : null;
  const idSuffix = showAccountId ? ` (${compactId})` : "";
  const workspaceLabel = account.chatgptAccountId || account.workspaceLabel || account.workspaceId || t("accounts.detail.unknownWorkspace");
  const seatLabel = account.seatType ? ` | ${formatSlug(account.seatType)}` : "";
  const operatorRecoveryAction =
    account.status === "reauth_required" || account.status === "deactivated";
  const usageResetDisabled =
    busy || readOnly || account.status === "paused" || operatorRecoveryAction || (resetCredits?.availableCount ?? 0) <= 0;

  return (
    <div
      key={account.accountId}
      className="animate-fade-in-up min-w-0 space-y-4 rounded-xl border bg-card p-4 sm:p-5"
    >
      {/* Account header */}
      <div>
        <AccountNameField
          key={account.accountId}
          accountId={account.accountId}
          color={accountColors.accounts.get(account.accountId)}
          alias={account.alias ?? null}
          localLabel={localLabel}
          labelIsEmail={labelIsEmail}
          idSuffix={emailSubtitle ? "" : idSuffix}
          blurred={blurred}
          busy={busy}
          readOnly={readOnly}
          onSetAlias={onSetAlias}
        />
        {emailSubtitle ? (
          <p
            className="mt-0.5 text-xs text-muted-foreground"
            title={
              showAccountId ? t("accounts.detail.accountIdTitle", { accountId: account.accountId }) : undefined
            }
          >
            <span className={blurred ? "privacy-blur" : ""}>
              {emailSubtitle}
            </span>
            {showAccountId ? ` | ID ${compactId}` : ""}
          </p>
        ) : null}
        <p className="mt-0.5 text-xs text-muted-foreground">
          {workspaceLabel} | {formatSlug(account.planType)}{seatLabel}
        </p>
      </div>

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
      <AccountUsagePanel
        account={account}
        trends={trends}
        resetCredits={resetCredits}
        resetCreditsLoading={resetCreditsLoading}
        resetCreditsUnavailable={resetCreditsUnavailable}
        resetDisabled={usageResetDisabled}
        onReset={onResetUsage}
      />
      <AccountTokenInfo account={account} />
      <CodexModelControls key={account.accountId} accountId={account.accountId} name={localLabel} disabled={busy || readOnly}>
        {({ mode, action }) => (
          <AccountActions
            modelControls={mode}
            modelAction={action}
            account={account}
            busy={busy}
            readOnly={readOnly}
            onPause={onPause}
            onResume={onResume}
            onProbe={onProbe}
            onDelete={onDelete}
            onReauth={onReauth}
            onExportAuth={onExportAuth}
            onResetCredit={onResetCredit}
            showResetCreditExpiryBadge={showResetCreditExpiryBadge}
            limitWarmupGloballyEnabled={limitWarmupGloballyEnabled}
            onLimitWarmupChange={onLimitWarmupChange}
            onRoutingPolicyChange={onRoutingPolicyChange}
            onCreditPolicyChange={onCreditPolicyChange}
            onSecurityWorkAuthorizedChange={onSecurityWorkAuthorizedChange}
          />
        )}
      </CodexModelControls>
    </div>
  );
}

type AccountNameFieldProps = {
  accountId: string;
  color: string | undefined;
  alias: string | null;
  localLabel: string;
  labelIsEmail: boolean;
  idSuffix: string;
  blurred: boolean;
  busy: boolean;
  readOnly: boolean;
  onSetAlias: (accountId: string, alias: string | null) => Promise<unknown>;
};

function AccountNameField({
  accountId,
  color,
  alias,
  localLabel,
  labelIsEmail,
  idSuffix,
  blurred,
  busy,
  readOnly,
  onSetAlias,
}: AccountNameFieldProps) {
  const { t } = useTranslation();
  return (
    <AccountNameEditor
      value={alias ?? ""}
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
      disabled={busy || readOnly}
      accessory={<AccountColorPicker target={{ accountId }} disabled={busy || readOnly} />}
      onSave={(value) => onSetAlias(accountId, value)}
    >
      <ProviderAccountName provider="codex" color={color}>
        {labelIsEmail ? <span className={cn(blurred && "privacy-blur")}>{localLabel}</span> : localLabel}
        {idSuffix}
      </ProviderAccountName>
    </AccountNameEditor>
  );
}
