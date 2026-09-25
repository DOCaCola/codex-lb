import { useState, type ReactNode } from "react";
import { OpenRouterAccountDetail } from "./account-detail";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

export function OpenRouterAccountControls({
  readOnly = false,
  account,
  onCreated,
  children,
}: {
  readOnly?: boolean;
  account: OpenRouterAccount | null;
  onCreated: (id: string) => void;
  children: (controls: { onAdd: () => void; detail: ReactNode }) => ReactNode;
}) {
  const { create, update, refresh, remove } = useOpenRouter();
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
  const error = create.error || update.error || refresh.error || remove.error;
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
  return (
    <>
      {children({
        onAdd: () => openEditor("new"),
        detail: account ? (
          <OpenRouterAccountDetail
            account={account}
            readOnly={readOnly}
            busy={busy}
            error={error?.message}
            onEdit={() => openEditor(account)}
            onModels={() => setModels(account)}
            onRefresh={() => refresh.mutate(account.id)}
            onToggle={(isEnabled) =>
              update.mutate({ id: account.id, body: { isEnabled } })
            }
            onDelete={() => setDeleting(account)}
          />
        ) : null,
      })}
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
                if (editing === "new") {
                  const created = await create.mutateAsync({
                    name,
                    apiKey,
                    ...(managementKey ? { managementKey } : {}),
                  });
                  onCreated(created.id);
                } else if (editing)
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
            <Button type="submit" disabled={readOnly || busy || !name.trim()}>
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
    </>
  );
}
