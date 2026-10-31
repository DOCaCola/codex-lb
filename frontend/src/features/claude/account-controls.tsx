import { useState, type ReactNode } from "react";
import { Layers, RefreshCw, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { AccountPauseButton } from "@/components/account-pause-button";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { ClaudeName, ClaudePlan, ClaudeQuota } from "./account-display";
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
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { AccountInfoPanel } from "@/features/accounts/components/account-info-panel";
import { CredentialImportDialog } from "@/features/accounts/components/credential-import-dialog";
import { ProviderSignInDialog } from "@/features/accounts/components/provider-sign-in-dialog";
import { ReauthenticateMenu } from "@/features/accounts/components/reauthenticate-menu";
import { usePrivacyStore } from "@/hooks/use-privacy";
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
  const accountColors = useAccountColorHexes();
  const dateFormat = useDateDisplayFormatStore(
    (state) => state.dateDisplayFormat,
  );
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
    <section className="animate-fade-in-up min-w-0 space-y-4 rounded-xl border bg-card p-4 sm:p-5">
      <div>
        <AccountNameEditor
          key={account.id}
          value={account.name}
          labels={{
            edit: "Rename account",
            input: "Account name",
            save: "Save name",
            cancel: "Cancel",
          }}
          disabled={readOnly || busy}
          accessory={<AccountColorPicker target={{ modelSourceId: account.id }} disabled={readOnly || busy} />}
          onSave={(name) =>
            run(() =>
              api.update.mutateAsync({
                id: account.id,
                body: { name: name ?? account.name },
              }),
            )
          }
        >
          <ClaudeName account={account} color={accountColors.modelSources.get(account.id)} />
        </AccountNameEditor>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Claude | <ClaudePlan account={account} /> |{" "}
          {account.state.all_models
            ? "All models"
            : `${account.state.selections.length} ${account.state.selections.length === 1 ? "model" : "models"} selected`}
        </p>
      </div>
      {[error, account.state.catalog_error, account.state.usage_error, account.state.subscription_error]
        .filter(Boolean)
        .map((message, index) => (
          <p key={index} role="alert" className="text-sm text-destructive">
            {message}
          </p>
        ))}
      <section className="min-w-0 space-y-4 rounded-lg border bg-muted/30 p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Usage
        </h3>
        <ClaudeQuota account={account} detailed />
        <ClaudeResetGrants
          key={account.id}
          accountId={account.id}
          readOnly={readOnly}
        />
        <ProviderAccountTrends
          provider="claude"
          accountId={account.id}
          embedded
        />
      </section>
      <p className="text-xs text-muted-foreground">
        Quota observations are provider-reported. Recorded API-equivalent costs
        are not subscription charges. OAuth acceptance and included-plan billing
        require live qualification.
      </p>
      <AccountInfoPanel
        title="Monitoring"
        rows={[
          { label: "Status", value: formatSlug(account.credentialStatus) },
          {
            label: "Access token expires",
            value: formatDateTimeInline(account.expiresAt, dateFormat),
          },
          {
            label: "Catalog updated",
            value: formatDateTimeInline(
              account.state.catalog_updated_at,
              dateFormat,
            ),
          },
          {
            label: "Usage updated",
            value: formatDateTimeInline(
              account.state.usage_updated_at,
              dateFormat,
            ),
          },
        ]}
      />
      <details className="min-w-0 rounded-lg border bg-muted/30 p-4">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Provider settings
        </summary>
        <div className="mt-4 space-y-4">
          <ClaudeCapacitySettings
            key={`${account.id}:${account.maxConcurrency}`}
            value={account.maxConcurrency}
            readOnly={readOnly}
            onSave={(maxConcurrency) =>
              api.update.mutateAsync({
                id: account.id,
                body: { maxConcurrency },
              })
            }
          />
          <ClaudeVersionControls readOnly={readOnly} />
        </div>
      </details>
      <AccountNotePanel target={{ modelSourceId: account.id }} readOnly={readOnly} />
      <AccountSubscriptionEndPanel target={{ modelSourceId: account.id }} readOnly={readOnly} />
      {/* Actions last, matching the Codex account detail. */}
      <div className="space-y-3 border-t pt-4">
        <AccountRoutingPolicyControl
          policy={account.routingPolicy}
          disabled={readOnly || busy}
          onChange={(routingPolicy) =>
            void run(() =>
              api.update.mutateAsync({
                id: account.id,
                body: { routingPolicy },
              }),
            )
          }
        />
        <div className="flex flex-wrap gap-2">
          <AccountPauseButton
            paused={!account.isEnabled}
            disabled={readOnly || busy}
            onClick={() =>
              void run(() =>
                api.update.mutateAsync({
                  id: account.id,
                  body: { isEnabled: !account.isEnabled },
                }),
              )
            }
          />
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs"
            disabled={readOnly || busy}
            onClick={() => setModelAccountId(account.id)}
          >
            <Layers className="h-3.5 w-3.5" />
            Models (
            {account.state.all_models ? "All" : account.state.selections.length}
            )
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
            aria-label="Delete Claude account"
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
