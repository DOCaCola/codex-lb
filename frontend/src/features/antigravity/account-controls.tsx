import { useState, type ReactNode } from "react";
import { BadgeAlert, Clock, KeyRound, Layers, PauseCircle, RefreshCw, ShieldAlert, ShieldCheck, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { AccountPauseButton } from "@/components/account-pause-button";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { ProviderAccountTrends } from "@/features/accounts/components/provider-account-trends";
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
import { ClaudeCapacitySettings } from "@/features/claude/capacity-settings";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { cn } from "@/lib/utils";
import { formatDateTimeInline, formatSlug } from "@/utils/formatters";
import { AntigravityPlan, AntigravityQuota } from "./account-display";
import { AntigravityModelSelection } from "./model-selection";
import { AntigravityVersionControls } from "./version-controls";
import { useAntigravity } from "./use-antigravity";
import type { AntigravityAccount } from "./api";

const HOLD_LABELS: Record<NonNullable<AntigravityAccount["hold"]>, string> = {
  banned: "Google suspended this account",
  misconfigured: "Account setup needs attention",
  location_unsupported: "Antigravity is not available in this account's location",
};

type Enrollment = { method: "signIn" | "import"; reauth: AntigravityAccount | null };

export function AntigravityAccountControls({
  account,
  readOnly,
  onCreated,
  children,
}: {
  account: AntigravityAccount | null;
  readOnly: boolean;
  onCreated: (id: string) => void;
  children: (controls: { onSignIn: () => void; onImport: () => void; detail: ReactNode }) => ReactNode;
}) {
  const api = useAntigravity();
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
      setError(cause instanceof Error ? cause.message : "Antigravity account operation failed");
    }
  }
  function enroll(next: Enrollment) {
    if (readOnly) return;
    // Defer so the menu or chooser releases its pointer lock before the dialog opens.
    requestAnimationFrame(() => setEnrollment(next));
  }
  const reauthAccount = enrollment?.reauth ?? null;
  const reauth = reauthAccount
    ? {
        name: reauthAccount.name,
        identity: reauthAccount.email ? (
          <span className={blurred ? "privacy-blur" : undefined}>{reauthAccount.email}</span>
        ) : null,
      }
    : undefined;
  const detail = account && (
    <AntigravityDetail
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
        <AntigravityModelSelection
          key={account.id + JSON.stringify(account.state.selections)}
          account={account}
          readOnly={readOnly || busy}
          onClose={() => setModelAccountId(null)}
          onSave={(body) => api.update.mutateAsync({ id: account.id, body })}
        />
      )}
      <ProviderSignInDialog
        provider="antigravity"
        open={enrollment?.method === "signIn"}
        onOpenChange={(open) => !open && setEnrollment(null)}
        reauth={reauth}
        start={(name) => api.start.mutateAsync({ name, sourceId: reauthAccount?.id })}
        complete={(flow, code) => api.complete.mutateAsync({ state: flow.state, code })}
        onConnected={onCreated}
      />
      <CredentialImportDialog
        provider="antigravity"
        open={enrollment?.method === "import"}
        onOpenChange={(open) => !open && setEnrollment(null)}
        reauth={reauth}
        importCredentials={(name, credentials) =>
          reauthAccount
            ? api.reconnect.mutateAsync({ id: reauthAccount.id, credentials })
            : api.enroll.mutateAsync({ name, credentials })
        }
        onImported={onCreated}
      />
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Antigravity account?"
        description="Stored credentials and account-bound conversation ownership will be removed. Conversations with signed history on this account may no longer continue."
        confirmLabel="Delete"
        confirmDisabled={readOnly || busy}
        onConfirm={() => {
          if (account && !readOnly) void run(() => api.remove.mutateAsync(account.id));
        }}
      />
    </>
  );
}

/** Account page of an Antigravity account. */
function AntigravityDetail({
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
  account: AntigravityAccount;
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
  const api = useAntigravity();
  const blurred = usePrivacyStore((s) => s.blurred);
  const accountColors = useAccountColorHexes();
  const dateFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
  const summary = summarizeEntry({ kind: "antigravity", account }, useSummaryContext());
  const commonMenu = useCommonMenuItems(account.id, summary.logsAccountId);
  const color = accountColors.modelSources.get(account.id);
  const disabled = readOnly || busy;
  const metadata = account.state.metadata;
  const update = (body: Parameters<typeof api.update.mutateAsync>[0]["body"]) =>
    run(() => api.update.mutateAsync({ id: account.id, body }));
  const reauthenticate = <ReauthenticateMenu disabled={disabled} onSignIn={onSignIn} onImport={onImport} />;
  const banner = account.hold ? (
    <DetailBanner
      tone="bad"
      icon={<ShieldAlert />}
      action={
        <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={disabled} onClick={() => void update({ clearHold: true })}>
          <ShieldCheck className="h-3.5 w-3.5" />
          Clear hold
        </Button>
      }
    >
      <p className="font-medium text-destructive">{HOLD_LABELS[account.hold]}</p>
      {account.holdReason && <p className="text-xs text-muted-foreground">{account.holdReason}</p>}
      <p className="text-xs text-muted-foreground">
        Routing skips this account until the hold is cleared. Clear it only after resolving the cause.
      </p>
    </DetailBanner>
  ) : summary.status === "reauth" ? (
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
  const errors = [error, metadata?.account?.error, metadata?.catalog?.error, metadata?.quota?.error].filter(Boolean);
  return (
    <ProviderDetail
      accountId={account.id}
      data-testid="antigravity-account-detail"
      provider="antigravity"
      color={color}
      name={
        <AccountNameEditor
          value={account.name}
          labels={{ edit: "Rename account", input: "Account name", save: "Save name", cancel: "Cancel" }}
          disabled={disabled}
          accessory={<AccountColorPicker target={{ modelSourceId: account.id }} disabled={disabled} />}
          onSave={(value) => update({ name: value ?? account.name })}
        >
          <span className={cn(blurred && "privacy-blur")}>{account.name}</span>
        </AccountNameEditor>
      }
      plan={<AntigravityPlan account={account} />}
      planKey={summary.planKey}
      status={summary.status}
      subline={[
        account.email ? <span className={cn(blurred && "privacy-blur")}>{account.email}</span> : null,
        summary.models,
      ]}
      actions={
        <>
          <AccountPauseButton
            paused={!account.isEnabled}
            disabled={disabled || (!account.isEnabled && account.hold !== null)}
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
        <>
          {account.state.verification && (
            <DetailBanner tone="warn" icon={<BadgeAlert />}>
              <p className="font-medium">Google asked to verify this account</p>
              <p className="text-xs text-muted-foreground">
                Observed {formatDateTimeInline(account.state.verification.observed_at, dateFormat)}. Requests pause
                briefly after each challenge.
                {account.state.verification.url && (
                  <>
                    {" "}
                    <a href={account.state.verification.url} target="_blank" rel="noopener noreferrer" className="underline">
                      Open verification
                    </a>
                  </>
                )}
              </p>
            </DetailBanner>
          )}
          {errors.map((message, index) => (
            <p key={index} role="alert" className="text-sm text-destructive">
              {message}
            </p>
          ))}
        </>
      }
      main={
        <>
          <DetailCard title={t("accounts.usage.title")} data-testid="account-usage">
            <div className="min-w-0 space-y-4">
              <AntigravityQuota account={account} detailed />
              <ProviderAccountTrends provider="antigravity" accountId={account.id} embedded />
              <p className="text-xs text-muted-foreground">
                Quota readings are provider-reported per model family. Recorded API-equivalent costs are not subscription
                charges.
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
                {
                  label: "Google account",
                  value: <span className={blurred ? "privacy-blur" : undefined}>{account.email}</span>,
                },
                { label: "Project", value: account.projectId ?? "Not assigned" },
                { label: "Access token expires", value: formatDateTimeInline(account.expiresAt, dateFormat) },
                { label: "Catalog updated", value: formatDateTimeInline(metadata?.catalog?.updated_at ?? null, dateFormat) },
                { label: "Quota updated", value: formatDateTimeInline(metadata?.quota?.updated_at ?? null, dateFormat) },
                ...account.cooldowns.map((cooldown) => ({
                  label: "Cooldown " + cooldown.scope.replace(/^(family|model):/, ""),
                  value: formatSlug(cooldown.reason) + " until " + formatDateTimeInline(cooldown.until, dateFormat),
                })),
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
          <DetailCard title={t("providers.detail.antigravityIdentity")} hint={t("providers.detail.allAntigravityAccounts")}>
            <AntigravityVersionControls readOnly={readOnly} />
          </DetailCard>
        </>
      }
    />
  );
}
