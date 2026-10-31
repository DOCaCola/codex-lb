import { useState, type ReactNode } from "react";
import { Layers, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { AccountPauseButton } from "@/components/account-pause-button";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { ProviderAccountTrends } from "@/features/accounts/components/provider-account-trends";
import { AccountRoutingPolicyControl } from "@/features/accounts/components/routing-policy";
import { AccountNameEditor } from "@/features/accounts/components/account-name-editor";
import { AccountColorPicker } from "@/features/accounts/components/account-color-picker";
import { AccountNotePanel } from "@/features/accounts/components/account-note-panel";
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { AccountInfoPanel } from "@/features/accounts/components/account-info-panel";
import { CredentialImportDialog } from "@/features/accounts/components/credential-import-dialog";
import { ProviderSignInDialog } from "@/features/accounts/components/provider-sign-in-dialog";
import { ReauthenticateMenu } from "@/features/accounts/components/reauthenticate-menu";
import { ClaudeCapacitySettings } from "@/features/claude/capacity-settings";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { formatDateTimeInline, formatSlug } from "@/utils/formatters";
import { AntigravityName, AntigravityPlan, AntigravityQuota } from "./account-display";
import { modelSummary } from "./display-values";
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
  const accountColors = useAccountColorHexes();
  const blurred = usePrivacyStore((s) => s.blurred);
  const dateFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
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
  const update = (body: Parameters<typeof api.update.mutateAsync>[0]["body"]) =>
    account ? run(() => api.update.mutateAsync({ id: account.id, body })) : Promise.resolve();
  const metadata = account?.state.metadata;
  const detail = account && (
    <section className="animate-fade-in-up min-w-0 space-y-4 rounded-xl border bg-card p-4 sm:p-5">
      <div>
        <AccountNameEditor
          key={account.id}
          value={account.name}
          labels={{ edit: "Rename account", input: "Account name", save: "Save name", cancel: "Cancel" }}
          disabled={readOnly || busy}
          accessory={<AccountColorPicker target={{ modelSourceId: account.id }} disabled={readOnly || busy} />}
          onSave={(value) => update({ name: value ?? account.name })}
        >
          <AntigravityName account={account} color={accountColors.modelSources.get(account.id)} />
        </AccountNameEditor>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Antigravity | <AntigravityPlan account={account} /> | {modelSummary(account)}
        </p>
      </div>
      {account.hold && (
        <div role="alert" className="space-y-1 rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm">
          <p className="font-medium text-destructive">{HOLD_LABELS[account.hold]}</p>
          {account.holdReason && <p className="text-xs text-muted-foreground">{account.holdReason}</p>}
          <p className="text-xs text-muted-foreground">
            Routing skips this account until the hold is cleared. Clear it only after resolving the cause.
          </p>
        </div>
      )}
      {account.state.verification && (
        <div role="alert" className="space-y-1 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-500/30 dark:bg-amber-500/10">
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
        </div>
      )}
      {[error, metadata?.account?.error, metadata?.catalog?.error, metadata?.quota?.error]
        .filter(Boolean)
        .map((message, index) => (
          <p key={index} role="alert" className="text-sm text-destructive">
            {message}
          </p>
        ))}
      <AccountNotePanel target={{ modelSourceId: account.id }} readOnly={readOnly} />
      <section className="min-w-0 space-y-4 rounded-lg border bg-muted/30 p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Usage</h3>
        <AntigravityQuota account={account} detailed />
        <ProviderAccountTrends provider="antigravity" accountId={account.id} embedded />
      </section>
      <p className="text-xs text-muted-foreground">
        Quota readings are provider-reported per model family. Recorded API-equivalent costs are not subscription
        charges.
      </p>
      <AccountInfoPanel
        title="Monitoring"
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
      <details className="min-w-0 rounded-lg border bg-muted/30 p-4">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Provider settings
        </summary>
        <div className="mt-4 space-y-4">
          <ClaudeCapacitySettings
            key={account.id + ":" + account.maxConcurrency}
            value={account.maxConcurrency}
            readOnly={readOnly}
            onSave={(maxConcurrency) => api.update.mutateAsync({ id: account.id, body: { maxConcurrency } })}
          />
          <AntigravityVersionControls readOnly={readOnly} />
        </div>
      </details>
      {/* Actions last, matching the Codex account detail. */}
      <div className="space-y-3 border-t pt-4">
        <AccountRoutingPolicyControl
          policy={account.routingPolicy}
          disabled={readOnly || busy}
          onChange={(routingPolicy) => void update({ routingPolicy })}
        />
        <div className="flex flex-wrap gap-2">
          <AccountPauseButton
            paused={!account.isEnabled}
            disabled={readOnly || busy || (!account.isEnabled && account.hold !== null)}
            onClick={() => void update({ isEnabled: !account.isEnabled })}
          />
          {account.hold && (
            <Button
              size="sm"
              variant="outline"
              className="h-8 gap-1.5 text-xs"
              disabled={readOnly || busy}
              onClick={() => void update({ clearHold: true })}
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              Clear hold
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs"
            disabled={readOnly || busy}
            onClick={() => setModelAccountId(account.id)}
          >
            <Layers className="h-3.5 w-3.5" />
            Models ({account.state.all_models ? "All" : account.state.selections.length})
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs"
            disabled={readOnly || busy}
            onClick={() => void run(() => api.refresh.mutateAsync(account.id))}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
          <ReauthenticateMenu
            disabled={readOnly || busy}
            onSignIn={() => enroll({ method: "signIn", reauth: account })}
            onImport={() => enroll({ method: "import", reauth: account })}
          />
          <Button
            size="sm"
            variant="destructive"
            className="h-8 gap-1.5 text-xs"
            aria-label="Delete Antigravity account"
            disabled={readOnly || busy}
            onClick={() => setDeleteOpen(true)}
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </Button>
        </div>
      </div>
    </section>
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
