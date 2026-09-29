import { useState, type ReactNode } from "react";
import { RefreshCw, Trash2 } from "lucide-react";
import { AccountPauseButton } from "@/components/account-pause-button";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { ClaudeName, ClaudeQuota } from "./account-display";
import { ProviderAccountTrends } from "@/features/accounts/components/provider-account-trends";
import { useClaude } from "./use-claude";
import type { ClaudeAccount, OAuthStarted } from "./api";
import { ClaudeVersionControls } from "./version-controls";
import { ClaudeCapacitySettings } from "./capacity-settings";
import { ClaudeResetGrants } from "./reset-grants";
import { ModelSelection } from "./model-selection";
import { AccountRoutingPolicyControl } from "@/features/accounts/components/routing-policy";
import { AccountInfoPanel } from "@/features/accounts/components/account-info-panel";
import { formatDateTimeInline, formatSlug } from "@/utils/formatters";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";

export function ClaudeAccountControls({
  account,
  readOnly,
  onCreated,
  children,
}: {
  account: ClaudeAccount | null;
  readOnly: boolean;
  onCreated: (id: string) => void;
  children: (controls: { onAdd: () => void; detail: ReactNode }) => ReactNode;
}) {
  const api = useClaude();
  const dateFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
  const [open, setOpen] = useState(false);
  const [reconnectId, setReconnectId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [flow, setFlow] = useState<OAuthStarted | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
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
  function close() {
    setOpen(false);
    setReconnectId(null);
    setFile(null);
    setCode("");
    setFlow(null);
    setName("");
    setAcknowledged(false);
  }
  function created(result: ClaudeAccount) {
    close();
    onCreated(result.id);
  }
  const detail = account && (
    <section className="animate-fade-in-up min-w-0 space-y-4 rounded-xl border bg-card p-4 sm:p-5">
      <div>
        <h2 className="min-w-0 truncate text-base font-semibold"><ClaudeName account={account} /></h2>
        <p className="mt-0.5 text-xs text-muted-foreground">Claude OAuth | {account.state.selections.length} models selected</p>
      </div>
      <section className="min-w-0 space-y-4 rounded-lg border bg-muted/30 p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Usage</h3>
        <ClaudeQuota account={account} detailed />
        <ClaudeResetGrants key={account.id} accountId={account.id} readOnly={readOnly} />
        <ProviderAccountTrends provider="claude" accountId={account.id} embedded />
      </section>
      <p className="text-xs text-muted-foreground">
        Quota observations are provider-reported. Recorded API-equivalent costs
        are not subscription charges. OAuth acceptance and included-plan billing
        require live qualification.
      </p>
      {[error, account.state.catalog_error, account.state.usage_error]
        .filter(Boolean)
        .map((message, index) => (
          <p key={index} role="alert" className="text-sm text-destructive">
            {message}
          </p>
        ))}
      <AccountInfoPanel title="Credentials" rows={[
        { label: "Status", value: formatSlug(account.credentialStatus) },
        { label: "Access token expires", value: formatDateTimeInline(account.expiresAt, dateFormat) },
        { label: "Catalog updated", value: formatDateTimeInline(account.state.catalog_updated_at, dateFormat) },
        { label: "Usage updated", value: formatDateTimeInline(account.state.usage_updated_at, dateFormat) },
      ]} />
      <div className="space-y-3 border-t pt-4">
        <AccountRoutingPolicyControl
          policy={account.routingPolicy}
          disabled={readOnly || busy}
          onChange={(routingPolicy) => void run(() => api.update.mutateAsync({ id: account.id, body: { routingPolicy } }))}
        />
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={readOnly || busy}
            onClick={() => {
              setReconnectId(account.id);
              setName(account.name);
              setError(null);
              setOpen(true);
            }}
          >
            Reconnect
          </Button>
          <AccountPauseButton
            paused={!account.isEnabled}
            disabled={readOnly || busy}
            onClick={() => void run(() => api.update.mutateAsync({
              id: account.id,
              body: { isEnabled: !account.isEnabled },
            }))}
          />
          <Button
            size="sm"
            variant="outline"
            disabled={readOnly || busy}
            onClick={() => void run(() => api.refresh.mutateAsync(account.id))}
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <Button
            size="sm"
            variant="outline"
            aria-label="Delete Claude account"
            disabled={readOnly || busy}
            onClick={() => setDeleteOpen(true)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <ClaudeCapacitySettings
        key={`${account.id}:${account.maxConcurrency}`}
        value={account.maxConcurrency}
        readOnly={readOnly}
        onSave={(maxConcurrency) =>
          api.update.mutateAsync({ id: account.id, body: { maxConcurrency } })
        }
      />
      <ModelSelection
        key={account.id + JSON.stringify(account.state.selections)}
        account={account}
        readOnly={readOnly}
        onSave={(selections) =>
          api.update.mutateAsync({ id: account.id, body: { selections } })
        }
      />
      <ClaudeVersionControls readOnly={readOnly} />
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
      <Dialog
        open={open}
        onOpenChange={(value) => {
          if (!busy && !value) close();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {reconnectId ? "Reconnect Claude account" : "Add Claude account"}
            </DialogTitle>
            <DialogDescription>
              Sign in with OAuth or explicitly import a Claude Code credential
              file. Credentials are encrypted and never displayed.
            </DialogDescription>
          </DialogHeader>
          <label className="space-y-1 text-sm">
            Account name
            <Input
              value={name}
              disabled={busy || !!flow || !!reconnectId}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={acknowledged}
              disabled={busy || !!flow}
              onChange={(event) => setAcknowledged(event.target.checked)}
            />
            I will not use this refresh grant in another client. Concurrent
            refresh consumers can invalidate access.
          </label>
          {flow ? (
            <div className="space-y-3">
              <a
                href={flow.authorizationUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm underline"
              >
                Open Claude authorization
              </a>
              <p className="text-xs text-muted-foreground">
                Paste the returned authorization code. Expires{" "}
                {new Date(flow.expiresAt).toLocaleString()}.
              </p>
              <Input
                aria-label="Authorization code"
                type="password"
                value={code}
                onChange={(event) => setCode(event.target.value)}
              />
              <Button
                disabled={readOnly || busy || !code.trim()}
                onClick={() =>
                  void run(async () =>
                    created(
                      await api.complete.mutateAsync({
                        state: flow.state,
                        code: code.trim(),
                      }),
                    ),
                  )
                }
              >
                Complete sign-in
              </Button>
            </div>
          ) : (
            <>
              <Button
                disabled={readOnly || busy || !name.trim() || !acknowledged}
                onClick={() =>
                  void run(async () =>
                    setFlow(
                      await api.start.mutateAsync({
                        name: name.trim(),
                        acknowledgeExclusiveRefresh: true,
                        sourceId: reconnectId ?? undefined,
                      }),
                    ),
                  )
                }
              >
                Sign in with Claude
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
                disabled={
                  readOnly || busy || !file || !name.trim() || !acknowledged
                }
                onClick={() =>
                  void run(async () => {
                    if (!file) return;
                    if (file.size > 1024 * 1024)
                      throw new Error("Credential file exceeds 1 MB");
                    let credentials: unknown;
                    try {
                      credentials = JSON.parse(await file.text());
                    } catch {
                      throw new Error(
                        "Credential file must contain valid JSON",
                      );
                    }
                    created(
                      reconnectId
                        ? await api.reconnect.mutateAsync({
                            id: reconnectId,
                            credentials,
                          })
                        : await api.enroll.mutateAsync({
                            name: name.trim(),
                            credentials,
                            acknowledgeExclusiveRefresh: true,
                          }),
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
