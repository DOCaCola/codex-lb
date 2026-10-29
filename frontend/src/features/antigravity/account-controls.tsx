import { useState, type ReactNode } from "react";
import { Layers, LogIn, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { AccountPauseButton } from "@/components/account-pause-button";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ProviderAccountTrends } from "@/features/accounts/components/provider-account-trends";
import { AccountRoutingPolicyControl } from "@/features/accounts/components/routing-policy";
import { AccountNameEditor } from "@/features/accounts/components/account-name-editor";
import { AccountColorPicker } from "@/features/accounts/components/account-color-picker";
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { AccountInfoPanel } from "@/features/accounts/components/account-info-panel";
import { ClaudeCapacitySettings } from "@/features/claude/capacity-settings";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { formatDateTimeInline, formatSlug } from "@/utils/formatters";
import { AntigravityName, AntigravityPlan, AntigravityQuota } from "./account-display";
import { modelSummary } from "./display-values";
import { AntigravityModelSelection } from "./model-selection";
import { AntigravityVersionControls } from "./version-controls";
import { useAntigravity } from "./use-antigravity";
import type { AntigravityAccount, OAuthStarted } from "./api";

const HOLD_LABELS: Record<NonNullable<AntigravityAccount["hold"]>, string> = {
  banned: "Google suspended this account",
  misconfigured: "Account setup needs attention",
  location_unsupported: "Antigravity is not available in this account's location",
};

async function readCredentialFile(file: File): Promise<unknown> {
  if (file.size > 1024 * 1024) throw new Error("Credential file exceeds 1 MB");
  try {
    return JSON.parse(await file.text());
  } catch {
    throw new Error("Credential file must contain valid JSON");
  }
}

export function AntigravityAccountControls({
  account,
  readOnly,
  onCreated,
  children,
}: {
  account: AntigravityAccount | null;
  readOnly: boolean;
  onCreated: (id: string) => void;
  children: (controls: { onAdd: () => void; detail: ReactNode }) => ReactNode;
}) {
  const api = useAntigravity();
  const accountColors = useAccountColorHexes();
  const blurred = usePrivacyStore((s) => s.blurred);
  const dateFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
  const [open, setOpen] = useState(false);
  const [reconnectId, setReconnectId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [flow, setFlow] = useState<OAuthStarted | null>(null);
  const [code, setCode] = useState("");
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
  function close() {
    setOpen(false);
    setReconnectId(null);
    setFile(null);
    setCode("");
    setFlow(null);
    setName("");
  }
  function created(result: AntigravityAccount) {
    close();
    onCreated(result.id);
  }
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
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs"
            disabled={readOnly || busy}
            onClick={() => {
              setReconnectId(account.id);
              setName(account.name);
              setError(null);
              setOpen(true);
            }}
          >
            <LogIn className="h-3.5 w-3.5" />
            Reconnect
          </Button>
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
        onAdd: () => {
          if (!readOnly) {
            setError(null);
            setOpen(true);
          }
        },
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
      <Dialog
        open={open}
        onOpenChange={(value) => {
          if (!busy && !value) close();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{reconnectId ? "Reconnect Antigravity account" : "Add Antigravity account"}</DialogTitle>
            <DialogDescription>
              Sign in with Google or import an Antigravity credential file (agy, OmniRoute or CLIProxyAPI). Only the
              refresh token is used; credentials are encrypted and never displayed.
            </DialogDescription>
          </DialogHeader>
          <label className="space-y-1 text-sm">
            Account name
            <Input value={name} disabled={busy || !!flow || !!reconnectId} onChange={(event) => setName(event.target.value)} />
          </label>
          {reconnectId && (
            <p className="text-xs text-muted-foreground">
              Reconnect with the same Google account. Its settings, statistics and conversation ownership are kept.
            </p>
          )}
          {flow ? (
            <div className="space-y-3">
              <a href={flow.authorizationUrl} target="_blank" rel="noopener noreferrer" className="text-sm underline">
                Open Google sign-in
              </a>
              <p className="text-xs text-muted-foreground">
                After signing in, paste the full antigravity.google callback URL or its code. Expires{" "}
                {formatDateTimeInline(flow.expiresAt, dateFormat)}.
              </p>
              <Input
                aria-label="Callback URL or authorization code"
                type="password"
                value={code}
                onChange={(event) => setCode(event.target.value)}
              />
              <Button
                disabled={readOnly || busy || !code.trim()}
                onClick={() =>
                  void run(async () => created(await api.complete.mutateAsync({ state: flow.state, code: code.trim() })))
                }
              >
                Complete sign-in
              </Button>
            </div>
          ) : (
            <>
              <Button
                disabled={readOnly || busy || !name.trim()}
                onClick={() =>
                  void run(async () =>
                    setFlow(await api.start.mutateAsync({ name: name.trim(), sourceId: reconnectId ?? undefined })),
                  )
                }
              >
                Sign in with Google
              </Button>
              <label className="space-y-1 text-sm">
                Or import a credential file
                <Input
                  type="file"
                  accept=".json,application/json"
                  disabled={busy}
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
              </label>
              <Button
                variant="outline"
                disabled={readOnly || busy || !file || !name.trim()}
                onClick={() =>
                  void run(async () => {
                    if (!file) return;
                    const credentials = await readCredentialFile(file);
                    created(
                      reconnectId
                        ? await api.reconnect.mutateAsync({ id: reconnectId, credentials })
                        : await api.enroll.mutateAsync({ name: name.trim(), credentials }),
                    );
                  })
                }
              >
                Import credentials
              </Button>
            </>
          )}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </DialogContent>
      </Dialog>
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
