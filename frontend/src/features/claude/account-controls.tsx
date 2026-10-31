import { useState, type ReactNode } from "react";
import { Clock, KeyRound, Layers, PauseCircle, RefreshCw, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { AccountPauseButton } from "@/components/account-pause-button";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { ClaudePlan, ClaudeQuota, ExtraUsageBadge } from "./account-display";
import { ProviderAccountTrends } from "@/features/accounts/components/provider-account-trends";
import { useClaude } from "./use-claude";
import type { ClaudeAccount } from "./api";
import { useIdentityConfirmation } from "./use-identity-confirmation";
import { ClaudeVersionControls } from "./version-controls";
import { ClaudeCapacitySettings } from "./capacity-settings";
import { ClaudeResetGrants } from "./reset-grants";
import { ModelSelection } from "./model-selection";
import { AccountRoutingPolicyControl } from "@/features/accounts/components/routing-policy";
import { AccountNameEditor } from "@/features/accounts/components/account-name-editor";
import { AccountColorPicker } from "@/features/accounts/components/account-color-picker";
import { AccountNotePanel } from "@/features/accounts/components/account-note-panel";
import { AccountSubscriptionEndPanel } from "@/features/accounts/components/account-subscription-end-panel";
import { AccountActivityCard } from "@/features/accounts/components/account-activity-card";
import {
  DetailBanner,
  DetailCard,
  DetailParts,
  DetailRows,
  ProviderDetail,
  SettingRow,
} from "@/features/accounts/components/provider-detail";
import { useCommonMenuItems } from "@/features/accounts/hooks/use-common-menu-items";
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { useSummaryContext } from "@/features/accounts/hooks/use-summary-context";
import { summarizeEntry } from "@/features/accounts/provider-summary";
import { CredentialImportDialog } from "@/features/accounts/components/credential-import-dialog";
import { ProviderSignInDialog } from "@/features/accounts/components/provider-sign-in-dialog";
import { ReauthenticateMenu } from "@/features/accounts/components/reauthenticate-menu";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import { formatDateTimeInline, formatSlug } from "@/utils/formatters";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";

type Enrollment = { method: "signIn" | "import"; reauth: ClaudeAccount | null };

/** Saved identity shown when re-authenticating; null until the account's next sign-in records it. */
function savedIdentity(account: ClaudeAccount, blurred: boolean): ReactNode {
  if (!account.accountEmail && !account.organizationName) return null;
  return (
    <>
      {account.accountEmail ? (
        <span className={blurred ? "privacy-blur" : undefined}>{account.accountEmail}</span>
      ) : null}
      {account.accountEmail && account.organizationName ? " · " : null}
      {account.organizationName}
    </>
  );
}

export function ClaudeAccountControls({
  account,
  readOnly,
  onCreated,
  children,
}: {
  account: ClaudeAccount | null;
  readOnly: boolean;
  onCreated: (id: string) => void;
  children: (controls: { onSignIn: () => void; onImport: () => void; detail: ReactNode }) => ReactNode;
}) {
  const { t } = useTranslation();
  const api = useClaude();
  const identity = useIdentityConfirmation();
  const blurred = usePrivacyStore((s) => s.blurred);
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [modelAccountId, setModelAccountId] = useState<string | null>(null);
  const busy = Object.values(api).some((mutation) => mutation.isPending);
  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Claude account operation failed",
      );
    }
  }
  function enroll(next: Enrollment) {
    if (readOnly) return;
    // Defer so the menu or chooser releases its pointer lock before the dialog opens.
    requestAnimationFrame(() => setEnrollment(next));
  }
  const reauthAccount = enrollment?.reauth ?? null;
  const reauth = reauthAccount
    ? { name: reauthAccount.name, identity: savedIdentity(reauthAccount, blurred) }
    : undefined;
  const reconnect = (action: () => Promise<ClaudeAccount>) =>
    reauthAccount ? identity.guard(reauthAccount.id, reauthAccount.name, action) : action();
  const detail = account && (
    <ClaudeDetail
      key={account.id}
      account={account}
      busy={busy}
      readOnly={readOnly}
      error={error}
      run={run}
      onModels={() => setModelAccountId(account.id)}
      onSignIn={() => enroll({ method: "signIn", reauth: account })}
      onImport={() => enroll({ method: "import", reauth: account })}
      onDelete={() => setDeleteOpen(true)}
    />
  );
  return (
    <>
      {children({
        onSignIn: () => enroll({ method: "signIn", reauth: null }),
        onImport: () => enroll({ method: "import", reauth: null }),
        detail,
      })}
      {account && modelAccountId === account.id && (
        <ModelSelection
          key={account.id + JSON.stringify(account.state.selections)}
          account={account}
          readOnly={readOnly || busy}
          onClose={() => setModelAccountId(null)}
          onSave={(body) => api.update.mutateAsync({ id: account.id, body })}
        />
      )}
      <ProviderSignInDialog
        provider="claude"
        open={enrollment?.method === "signIn"}
        onOpenChange={(open) => !open && setEnrollment(null)}
        reauth={reauth}
        acknowledgement={t("accounts.signIn.claude.acknowledgement")}
        start={(name) =>
          api.start.mutateAsync({ name, acknowledgeExclusiveRefresh: true, sourceId: reauthAccount?.id })
        }
        complete={(flow, code) => reconnect(() => api.complete.mutateAsync({ state: flow.state, code }))}
        onConnected={onCreated}
      />
      <CredentialImportDialog
        provider="claude"
        open={enrollment?.method === "import"}
        onOpenChange={(open) => !open && setEnrollment(null)}
        reauth={reauth}
        acknowledgement={t("accounts.signIn.claude.acknowledgement")}
        importCredentials={(name, credentials) =>
          reauthAccount
            ? reconnect(() => api.reconnect.mutateAsync({ id: reauthAccount.id, credentials }))
            : api.enroll.mutateAsync({ name, credentials, acknowledgeExclusiveRefresh: true })
        }
        onImported={onCreated}
      />
      {identity.dialog}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Claude account?"
        description="Stored credentials and account-bound continuation ownership will be removed. Existing signed conversations may no longer continue."
        confirmLabel="Delete"
        confirmDisabled={readOnly || busy}
        onConfirm={() => {
          if (account && !readOnly)
            void run(() => api.remove.mutateAsync(account.id));
        }}
      />
    </>
  );
}

/** Account page of a Claude account. */
function ClaudeDetail({
  account,
  busy,
  readOnly,
  error,
  run,
  onModels,
  onSignIn,
  onImport,
  onDelete,
}: {
  account: ClaudeAccount;
  busy: boolean;
  readOnly: boolean;
  error: string | null;
  run: (action: () => Promise<unknown>) => Promise<void>;
  onModels: () => void;
  onSignIn: () => void;
  onImport: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  const api = useClaude();
  const blurred = usePrivacyStore((s) => s.blurred);
  const accountColors = useAccountColorHexes();
  const dateFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
  const summary = summarizeEntry({ kind: "claude", account }, useSummaryContext());
  const commonMenu = useCommonMenuItems(account.id, summary.logsAccountId);
  const color = accountColors.modelSources.get(account.id);
  const disabled = readOnly || busy;
  const update = (body: Parameters<typeof api.update.mutateAsync>[0]["body"]) =>
    run(() => api.update.mutateAsync({ id: account.id, body }));
  const reauthenticate = <ReauthenticateMenu disabled={disabled} onSignIn={onSignIn} onImport={onImport} />;
  const banner =
    summary.status === "reauth" ? (
      <DetailBanner tone="bad" icon={<KeyRound />} action={reauthenticate}>
        {t("providers.banner.recovery")}
      </DetailBanner>
    ) : summary.status === "paused" ? (
      <DetailBanner tone="off" icon={<PauseCircle />}>
        {t("providers.banner.paused")}
      </DetailBanner>
    ) : summary.status === "limited" || summary.status === "exceeded" ? (
      <DetailBanner tone={summary.tone === "bad" ? "bad" : "warn"} icon={<Clock />}>
        {summary.notice?.text ?? t("providers.banner.limited")}
      </DetailBanner>
    ) : null;
  const errors = [error, account.state.catalog_error, account.state.usage_error, account.state.subscription_error].filter(Boolean);
  return (
    <ProviderDetail
      accountId={account.id}
      data-testid="claude-account-detail"
      provider="claude"
      color={color}
      name={
        <AccountNameEditor
          value={account.name}
          labels={{
            edit: "Rename account",
            input: "Account name",
            save: "Save name",
            cancel: "Cancel",
          }}
          disabled={disabled}
          accessory={<AccountColorPicker target={{ modelSourceId: account.id }} disabled={disabled} />}
          onSave={(name) => update({ name: name ?? account.name })}
        >
          <span className={cn(blurred && "privacy-blur")}>{account.name}</span>
        </AccountNameEditor>
      }
      plan={<ClaudePlan account={account} />}
      planKey={summary.planKey}
      status={summary.status}
      badges={<ExtraUsageBadge account={account} />}
      subline={[
        account.accountEmail ? <span className={cn(blurred && "privacy-blur")}>{account.accountEmail}</span> : null,
        account.organizationName,
        summary.models,
      ]}
      actions={
        <>
          <AccountPauseButton
            paused={!account.isEnabled}
            disabled={disabled}
            onClick={() => void update({ isEnabled: !account.isEnabled })}
          />
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs"
            disabled={disabled}
            onClick={() => void run(() => api.refresh.mutateAsync(account.id))}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {t("providers.detail.checkLimits")}
          </Button>
        </>
      }
      menu={[
        ...commonMenu,
        {
          key: "delete",
          label: t("providers.detail.deleteAccount"),
          icon: <Trash2 />,
          destructive: true,
          disabled,
          onSelect: onDelete,
        },
      ]}
      banner={banner}
      alerts={
        errors.length > 0 ? (
          <div className="space-y-1">
            {errors.map((message, index) => (
              <p key={index} role="alert" className="text-sm text-destructive">
                {message}
              </p>
            ))}
          </div>
        ) : null
      }
      main={
        <>
          <DetailCard title={t("accounts.usage.title")} data-testid="account-usage">
            <div className="min-w-0 space-y-4">
              <ClaudeQuota account={account} />
              <ClaudeResetGrants accountId={account.id} readOnly={readOnly} />
              <ProviderAccountTrends provider="claude" accountId={account.id} embedded />
              <p className="text-xs text-muted-foreground">
                Quota observations are provider-reported. Recorded API-equivalent costs
                are not subscription charges. OAuth acceptance and included-plan billing
                require live qualification.
              </p>
            </div>
          </DetailCard>
          <AccountActivityCard activityKey={summary.activityKey} logsAccountId={summary.logsAccountId} color={color} />
        </>
      }
      side={
        <>
          <DetailCard title={t("providers.detail.signIn")} action={summary.status === "reauth" ? null : reauthenticate}>
            <DetailRows
              rows={[
                { label: "Status", value: formatSlug(account.credentialStatus) },
                { label: "Access token expires", value: formatDateTimeInline(account.expiresAt, dateFormat) },
                { label: "Catalog updated", value: formatDateTimeInline(account.state.catalog_updated_at, dateFormat) },
                { label: "Usage updated", value: formatDateTimeInline(account.state.usage_updated_at, dateFormat) },
              ]}
            />
          </DetailCard>
          <DetailCard title={t("providers.detail.details")}>
            <DetailParts>
              <AccountNotePanel target={{ modelSourceId: account.id }} readOnly={readOnly} />
              <AccountSubscriptionEndPanel target={{ modelSourceId: account.id }} readOnly={readOnly} />
            </DetailParts>
          </DetailCard>
        </>
      }
      settings={
        <>
          <DetailCard title={t("providers.detail.routing")}>
            <DetailParts>
              <AccountRoutingPolicyControl
                policy={account.routingPolicy}
                disabled={disabled}
                onChange={(routingPolicy) => void update({ routingPolicy })}
              />
              <SettingRow
                label={t("providers.detail.models")}
                control={
                  <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={disabled} onClick={onModels}>
                    <Layers className="h-3.5 w-3.5" />
                    Models ({account.state.all_models ? "All" : account.state.selections.length})
                  </Button>
                }
              />
              <ClaudeCapacitySettings
                key={account.id + ":" + account.maxConcurrency}
                value={account.maxConcurrency}
                readOnly={readOnly}
                onSave={(maxConcurrency) => api.update.mutateAsync({ id: account.id, body: { maxConcurrency } })}
              />
            </DetailParts>
          </DetailCard>
          <DetailCard title={t("providers.detail.claudeVersion")} hint={t("providers.detail.allClaudeAccounts")}>
            <ClaudeVersionControls readOnly={readOnly} />
          </DetailCard>
        </>
      }
    />
  );
}
