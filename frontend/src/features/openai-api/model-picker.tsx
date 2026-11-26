import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { CatalogModel, OpenAIApiAccount, Selection } from "./api";
import { OPENAI_API_MODEL_PREFIX } from "./display-values";

export type ModelPickerKind = CatalogModel["kind"];

/** Selections whose model left the catalog stay manageable in the text picker. */
function selectionKind(model: CatalogModel | undefined): ModelPickerKind {
  return model?.kind ?? "text";
}

export function ModelPicker({
  account,
  kind,
  busy,
  onClose,
  onSave,
}: {
  account: OpenAIApiAccount;
  kind: ModelPickerKind;
  busy: boolean;
  onClose: () => void;
  onSave: (selections: Selection[]) => Promise<void>;
}) {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Selection[]>(account.state.selections);
  const [error, setError] = useState<string | null>(null);
  const catalog = useMemo(() => new Map(account.state.catalog.map((model) => [model.id, model])), [account]);
  const ids = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return [...new Set([...account.state.selections.map((item) => item.model), ...catalog.keys()])]
      .filter((id) => selectionKind(catalog.get(id)) === kind && id.toLowerCase().includes(needle))
      .sort((left, right) => left.localeCompare(right));
  }, [account.state.selections, catalog, kind, search]);
  const selectedCount = selected.filter((item) => selectionKind(catalog.get(item.model)) === kind).length;
  const images = kind === "image";
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="max-h-[90dvh] w-[calc(100%-2rem)] max-w-2xl grid-rows-[auto_auto_minmax(0,1fr)_auto] sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {images ? "Image models" : "Models"} · {account.name}
          </DialogTitle>
          <DialogDescription>
            {images
              ? "Image models serve the Images API and image redirects. Codex clients reach them only through a redirect in Settings → Model catalogue."
              : "Selected models are published to /v1 clients as openai-apikey/<model>. Codex clients cannot use them: the monthly API credit does not cover Codex usage."}
          </DialogDescription>
        </DialogHeader>
        <Input
          aria-label="Search OpenAI API models"
          placeholder="Search models"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <div className="max-h-[55vh] space-y-2 overflow-y-auto">
          {ids.length === 0 && (
            <p role="status" className="p-3 text-sm text-muted-foreground">
              {catalog.size === 0 ? "The catalog is empty. Refresh the account." : "No models match your search."}
            </p>
          )}
          {ids.map((id) => {
            const model = catalog.get(id);
            const selection = selected.find((item) => item.model === id);
            return (
              <div key={id} className="rounded-lg border p-3 text-sm">
                <label className="flex items-center gap-3">
                  <Checkbox
                    checked={!!selection}
                    disabled={busy}
                    onCheckedChange={(checked) =>
                      setSelected((current) =>
                        checked
                          ? [...current, { model: id, displayName: null }]
                          : current.filter((item) => item.model !== id),
                      )
                    }
                  />
                  <span>
                    {id}
                    {model ? "" : " — Unavailable"}
                  </span>
                </label>
                <div className="mt-1 break-all text-xs text-muted-foreground">
                  {OPENAI_API_MODEL_PREFIX}
                  {id}
                </div>
                {selection && (
                  <label className="mt-2 block space-y-1 text-xs sm:max-w-[50%]">
                    Display name
                    <Input
                      aria-label={`Display name for ${id}`}
                      value={selection.displayName ?? ""}
                      placeholder={id}
                      disabled={busy}
                      onChange={(event) =>
                        setSelected((current) =>
                          current.map((item) =>
                            item.model === id ? { ...item, displayName: event.target.value || null } : item,
                          ),
                        )
                      }
                    />
                  </label>
                )}
              </div>
            );
          })}
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={busy}
            onClick={async () => {
              try {
                await onSave(selected);
                onClose();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Save failed");
              }
            }}
          >
            Save {selectedCount} {images ? "image " : ""}
            {selectedCount === 1 ? "model" : "models"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
