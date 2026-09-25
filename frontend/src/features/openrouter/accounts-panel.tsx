import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { ConfirmDialog } from "@/components/confirm-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { ModelPicker } from "./model-picker";
import { useOpenRouter } from "./use-openrouter";
import type { OpenRouterAccount } from "./api";

const money = (value: number | null | undefined) =>
  value == null
    ? "Unknown"
    : new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 4,
      }).format(value);
const timestamp = (value: string | null) =>
  value
    ? new Date(
        `${value}${/Z|[+-]\d\d:\d\d$/.test(value) ? "" : "Z"}`,
      ).toLocaleString()
    : "Never";

export function OpenRouterAccountsPanel({
  readOnly = false,
  dashboard = false,
}: {
  readOnly?: boolean;
  dashboard?: boolean;
}) {
  const { query, create, update, refresh, remove } = useOpenRouter();
  const [editing, setEditing] = useState<OpenRouterAccount | "new" | null>(
    null,
  );
  const [models, setModels] = useState<OpenRouterAccount | null>(null);
  const [deleting, setDeleting] = useState<OpenRouterAccount | null>(null);
  const [name, setName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [managementKey, setManagementKey] = useState("");
  const [clearManagement, setClearManagement] = useState(false);
  const busy =
    create.isPending ||
    update.isPending ||
    refresh.isPending ||
    remove.isPending;
  const error =
    query.error ||
    create.error ||
    update.error ||
    refresh.error ||
    remove.error;
  const accounts = query.data?.accounts ?? [];
  const openEditor = (account: OpenRouterAccount | "new") => {
    setEditing(account);
    setName(account === "new" ? "" : account.name);
    setApiKey("");
    setManagementKey("");
    setClearManagement(false);
  };
  const closeEditor = () => {
    setEditing(null);
    setApiKey("");
    setManagementKey("");
  };
  if (dashboard && accounts.length === 0 && !error) return null;
  return (
    <section className="space-y-4 rounded-xl border bg-card p-5">
      <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
        <h2 className="text-lg font-semibold">OpenRouter accounts</h2>
        {!dashboard && !readOnly && (
          <Button onClick={() => openEditor("new")}>
            Add OpenRouter account
          </Button>
        )}
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error.message}
        </p>
      )}
      {query.isLoading && (
        <p className="text-sm text-muted-foreground">Loading accounts…</p>
      )}
      {!query.isLoading && !accounts.length && (
        <p className="text-sm text-muted-foreground">
          Connect OpenRouter directly, then choose models to make available to
          clients.
        </p>
      )}
      <div className="grid gap-3 lg:grid-cols-2">
        {accounts.map((account) => {
          const state = account.state;
          const credits = state.credits;
          return (
            <div key={account.id} className="space-y-3 rounded-lg border p-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-medium">{account.name}</h3>
                <Switch
                  aria-label={`Enable ${account.name}`}
                  checked={account.isEnabled}
                  disabled={readOnly || dashboard || busy}
                  onCheckedChange={(isEnabled) =>
                    update.mutate({ id: account.id, body: { isEnabled } })
                  }
                />
              </div>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-muted-foreground">Account balance</dt>
                  <dd>
                    {money(
                      credits
                        ? credits.total_credits - credits.total_usage
                        : null,
                    )}
                    {state.credits_error && state.credits ? " · stale" : ""}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Key allowance left</dt>
                  <dd>
                    {state.key && state.key.limit === null
                      ? "No key cap"
                      : money(state.key?.limit_remaining)}
                    {state.key_error && state.key ? " · stale" : ""}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Used today</dt>
                  <dd>{money(state.key?.usage_daily)}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">
                    Free requests left today
                  </dt>
                  <dd>
                    {state.key?.free_model_daily_requests?.remaining ??
                      "Unknown"}
                  </dd>
                </div>
              </dl>
              {!account.hasManagementKey && (
                <p className="text-xs text-muted-foreground">
                  Add a management key to display account credits. Key allowance
                  is separate from balance.
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Usage: {timestamp(state.key_updated_at)} · Credits:{" "}
                {timestamp(state.credits_updated_at)}
                <br />
                Catalog: {timestamp(state.catalog_updated_at)} ·{" "}
                {state.selections.length} selected
              </p>
              {[state.catalog_error, state.key_error, state.credits_error]
                .filter(Boolean)
                .map((message) => (
                  <p key={message} className="text-xs text-destructive">
                    {message}
                  </p>
                ))}
              {!dashboard && !readOnly && (
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy}
                    onClick={() => setModels(account)}
                  >
                    Models
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy}
                    onClick={() => refresh.mutate(account.id)}
                  >
                    Refresh
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy}
                    onClick={() => openEditor(account)}
                  >
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={busy}
                    onClick={() => setDeleting(account)}
                  >
                    Delete
                  </Button>
                </div>
              )}
            </div>
          );
        })}
      </div>
      {models && (
        <ModelPicker
          key={models.id}
          account={models}
          busy={busy}
          onClose={() => setModels(null)}
          onSave={(selections) =>
            update
              .mutateAsync({ id: models.id, body: { selections } })
              .then(() => undefined)
          }
        />
      )}
      <Dialog
        open={editing !== null}
        onOpenChange={(open) => {
          if (!open) closeEditor();
        }}
      >
        <DialogContent className="max-h-[90dvh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editing === "new"
                ? "Add OpenRouter account"
                : "Edit OpenRouter account"}
            </DialogTitle>
            <DialogDescription>
              Credentials are encrypted. Inference and credit monitoring use
              separate keys.
            </DialogDescription>
          </DialogHeader>
          <form
            className="space-y-4"
            onSubmit={async (event) => {
              event.preventDefault();
              try {
                if (editing === "new")
                  await create.mutateAsync({
                    name,
                    apiKey,
                    ...(managementKey ? { managementKey } : {}),
                  });
                else if (editing)
                  await update.mutateAsync({
                    id: editing.id,
                    body: {
                      name,
                      ...(apiKey ? { apiKey } : {}),
                      ...(clearManagement
                        ? { managementKey: null }
                        : managementKey
                          ? { managementKey }
                          : {}),
                    },
                  });
                closeEditor();
              } catch {
                /* Mutation error is displayed below. */
              }
            }}
          >
            <label className="block space-y-1 text-sm">
              Name
              <Input
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label className="block space-y-1 text-sm">
              Inference API key
              <Input
                type="password"
                autoComplete="new-password"
                required={editing === "new"}
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder={
                  editing === "new" ? "" : "Leave blank to keep current key"
                }
              />
            </label>
            <label className="block space-y-1 text-sm">
              Management API key (optional)
              <Input
                type="password"
                autoComplete="new-password"
                disabled={clearManagement}
                value={managementKey}
                onChange={(event) => setManagementKey(event.target.value)}
                placeholder="For account balance only"
              />
            </label>
            {editing && editing !== "new" && editing.hasManagementKey && (
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={clearManagement}
                  onChange={(event) => setClearManagement(event.target.checked)}
                />
                Remove management key
              </label>
            )}
            {(create.error || update.error) && (
              <p role="alert" className="text-sm text-destructive">
                {(create.error || update.error)?.message}
              </p>
            )}
            <Button type="submit" disabled={busy || !name.trim()}>
              Save account
            </Button>
          </form>
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        title="Delete OpenRouter account?"
        description="The account and its selected model routes will be removed. Request history remains."
        confirmLabel="Delete"
        confirmDisabled={remove.isPending}
        onConfirm={async () => {
          if (deleting) {
            await remove.mutateAsync(deleting.id);
            setDeleting(null);
          }
        }}
      />
    </section>
  );
}
