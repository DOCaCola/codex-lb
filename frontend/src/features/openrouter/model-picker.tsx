import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import type { OpenRouterAccount, Selection } from "./api";

export function ModelPicker({
  account,
  onClose,
  onSave,
  busy,
}: {
  account: OpenRouterAccount;
  onClose: () => void;
  onSave: (selections: Selection[]) => Promise<void>;
  busy: boolean;
}) {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Selection[]>(
    account.state.selections,
  );
  const [error, setError] = useState<string | null>(null);
  const catalog = useMemo(
    () => new Map(account.state.catalog.map((model) => [model.id, model])),
    [account],
  );
  const ids = useMemo(
    () =>
      [
        ...new Set([...selected.map((item) => item.model), ...catalog.keys()]),
      ].filter((id) =>
        `${id} ${catalog.get(id)?.name ?? ""}`
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    [catalog, search, selected],
  );
  const valid = selected.every(
    (item) =>
      Number.isInteger(item.contextWindow) &&
      item.contextWindow > 0 &&
      (item.maxOutputTokens === null ||
        (Number.isInteger(item.maxOutputTokens) && item.maxOutputTokens > 0)),
  );
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="max-h-[90dvh] w-[calc(100%-2rem)] max-w-3xl grid-rows-[auto_auto_minmax(0,1fr)_auto] sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Models · {account.name}</DialogTitle>
          <DialogDescription>
            Only selected models are available to clients. New models remain
            disabled after synchronization.
          </DialogDescription>
        </DialogHeader>
        <Input
          aria-label="Search OpenRouter models"
          placeholder="Search models"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <div className="max-h-[55vh] space-y-2 overflow-y-auto">
          {ids.map((id) => {
            const model = catalog.get(id);
            const selection = selected.find((item) => item.model === id);
            const price = (value: number | null | undefined) =>
              value == null ? "Unknown" : `$${(value * 1e6).toLocaleString()}`;
            return (
              <div key={id} className="rounded-lg border p-3 text-sm">
                <label className="flex items-center gap-3">
                  <Checkbox
                    checked={!!selection}
                    disabled={busy || (!model && !selection)}
                    onCheckedChange={(checked) =>
                      setSelected((current) =>
                        checked
                          ? [
                              ...current,
                              {
                                model: id,
                                contextWindow: 262144,
                                maxOutputTokens: null,
                                displayName: null,
                              },
                            ]
                          : current.filter((item) => item.model !== id),
                      )
                    }
                  />
                  <span>
                    {model?.name ?? id} {!model ? "— Unavailable" : ""}
                  </span>
                </label>
                <div className="mt-1 break-all text-xs text-muted-foreground">
                  openrouter/{id}
                </div>
                {model && (
                  <div className="mt-1 text-xs text-muted-foreground">
                    Input {price(model.pricing.prompt)} · Cached{" "}
                    {price(model.pricing.input_cache_read)} · Output{" "}
                    {price(model.pricing.completion)} / 1M tokens
                    <br />
                    {model.supported_parameters.includes("tools")
                      ? "Tools · "
                      : ""}
                    {model.architecture.input_modalities.join(", ")}
                    {model.reasoning?.supported_efforts?.length
                      ? ` · Reasoning: ${model.reasoning.supported_efforts.join(", ")}`
                      : ""}
                    {model.reasoning?.mandatory ? " (required)" : ""}
                  </div>
                )}
                {selection && (
                  <div className="mt-2 grid gap-3 sm:grid-cols-2">
                    <label className="space-y-1 text-xs">
                      Display name
                      <Input
                        aria-label={`Display name for ${id}`}
                        value={selection.displayName ?? ""}
                        placeholder={model?.name ?? id}
                        disabled={busy}
                        onChange={(event) =>
                          setSelected((current) =>
                            current.map((item) =>
                              item.model === id
                                ? {
                                    ...item,
                                    displayName: event.target.value || null,
                                  }
                                : item,
                            ),
                          )
                        }
                      />
                    </label>
                    <label className="space-y-1 text-xs">
                      Output cap (optional)
                      <Input
                        type="number"
                        min={1}
                        step={1}
                        aria-label={`Output cap for ${id}`}
                        value={selection.maxOutputTokens ?? ""}
                        placeholder="Provider limit"
                        disabled={busy}
                        onChange={(event) =>
                          setSelected((current) =>
                            current.map((item) =>
                              item.model === id
                                ? {
                                    ...item,
                                    maxOutputTokens: event.target.value
                                      ? Number(event.target.value)
                                      : null,
                                  }
                                : item,
                            ),
                          )
                        }
                      />
                    </label>
                  </div>
                )}
                {selection && (
                  <label className="mt-2 flex items-center gap-3 text-xs">
                    Context cap
                    <Input
                      type="number"
                      min={1}
                      step={1}
                      className="w-36"
                      aria-label={`Context cap for ${id}`}
                      value={selection.contextWindow}
                      onChange={(event) =>
                        setSelected((current) =>
                          current.map((item) =>
                            item.model === id
                              ? {
                                  ...item,
                                  contextWindow: Number(event.target.value),
                                }
                              : item,
                          ),
                        )
                      }
                    />
                    <span className="text-muted-foreground">
                      Upstream limits also apply
                    </span>
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
            disabled={busy || !valid}
            onClick={async () => {
              try {
                await onSave(selected);
                onClose();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Save failed");
              }
            }}
          >
            Save {selected.length} models
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
