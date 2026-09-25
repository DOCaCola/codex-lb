import { useState, type ReactNode } from "react";
import { Pause, Play, RefreshCw, Trash2 } from "lucide-react";
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
import { useClaude } from "./use-claude";
import type { ClaudeAccount, ClaudeSelection, OAuthStarted } from "./api";
import { ClaudeVersionControls } from "./version-controls";

function ModelSelection({
  account,
  readOnly,
  onSave,
}: {
  account: ClaudeAccount;
  readOnly: boolean;
  onSave: (selections: ClaudeSelection[]) => Promise<unknown>;
}) {
  const [selections, setSelections] = useState(account.state.selections);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const catalog = [...account.state.catalog];
  for (const selection of selections) {
    if (!catalog.some((model) => model.id === selection.model))
      catalog.push({
        id: selection.model,
        display_name: `${selection.model} (unavailable)`,
      });
  }
  return (
    <section className="space-y-3">
      <h3 className="font-medium">Models available to clients</h3>
      <Input
        aria-label="Search Claude models"
        placeholder="Search models"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      <div className="max-h-96 space-y-3 overflow-y-auto">
        {catalog
          .filter((model) =>
            `${model.id} ${model.display_name}`
              .toLowerCase()
              .includes(search.toLowerCase()),
          )
          .map((model) => {
            const selected = selections.find((item) => item.model === model.id);
            return (
              <div key={model.id} className="space-y-2 rounded-lg border p-3">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    disabled={readOnly || busy}
                    checked={!!selected}
                    onChange={(event) =>
                      setSelections((current) =>
                        event.target.checked
                          ? [
                              ...current,
                              {
                                model: model.id,
                                contextWindow: 200000,
                                maxOutputTokens: 8192,
                              },
                            ]
                          : current.filter((item) => item.model !== model.id),
                      )
                    }
                  />
                  {model.display_name}
                </label>
                {selected && (
                  <div className="grid grid-cols-2 gap-3">
                    {(["contextWindow", "maxOutputTokens"] as const).map(
                      (field) => (
                        <label
                          key={field}
                          className="space-y-1 text-xs text-muted-foreground"
                        >
                          {field === "contextWindow"
                            ? "Context tokens"
                            : "Maximum output tokens"}
                          <Input
                            type="number"
                            min={1}
                            max={field === "contextWindow" ? 262144 : undefined}
                            value={selected[field]}
                            disabled={readOnly || busy}
                            onChange={(event) =>
                              setSelections((current) =>
                                current.map((item) =>
                                  item.model === model.id
                                    ? {
                                        ...item,
                                        [field]: Number(event.target.value),
                                      }
                                    : item,
                                ),
                              )
                            }
                          />
                        </label>
                      ),
                    )}
                  </div>
                )}
              </div>
            );
          })}
      </div>
      {!catalog.length && (
        <p className="text-sm text-muted-foreground">
          Refresh the account to discover its catalog. Models remain disabled
          until selected.
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <Button
        disabled={
          readOnly ||
          busy ||
          selections.some(
            (item) =>
              !Number.isInteger(item.contextWindow) ||
              item.contextWindow < 1 ||
              item.contextWindow > 262144 ||
              !Number.isInteger(item.maxOutputTokens) ||
              item.maxOutputTokens < 1,
          )
        }
        onClick={async () => {
          setBusy(true);
          setError(null);
          try {
            await onSave(selections);
          } catch (cause) {
            setError(
              cause instanceof Error ? cause.message : "Could not save models",
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        Save models
      </Button>
    </section>
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
  children: (controls: { onAdd: () => void; detail: ReactNode }) => ReactNode;
}) {
  const api = useClaude();
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
    <section className="space-y-5 rounded-xl border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">
          <ClaudeName account={account} />
        </h2>
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
          <Button
            size="sm"
            variant="outline"
            disabled={readOnly || busy}
            onClick={() =>
              void run(() =>
                api.update.mutateAsync({
                  id: account.id,
                  body: { isEnabled: !account.isEnabled },
                }),
              )
            }
          >
            {account.isEnabled ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {account.isEnabled ? "Pause" : "Resume"}
          </Button>
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
      <p className="text-sm text-muted-foreground">
        Claude OAuth · Credentials: {account.credentialStatus}. Token expiry:{" "}
        {new Date(account.expiresAt).toLocaleString()}.
      </p>
      <ClaudeQuota account={account} detailed />
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
