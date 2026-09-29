import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatCompactNumber } from "@/utils/formatters";
import type { ClaudeAccount, ClaudeSelection } from "./api";

export function ModelSelection({
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
        max_input_tokens: null,
        max_tokens: null,
      });
  }
  return (
    <section className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Models available to clients</h3>
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
                    disabled={readOnly || busy || (!selected && (model.max_input_tokens === null || model.max_tokens === null))}
                    checked={!!selected}
                    onChange={(event) =>
                      setSelections((current) =>
                        event.target.checked
                          ? [
                              ...current,
                              {
                                model: model.id,
                              },
                            ]
                          : current.filter((item) => item.model !== model.id),
                      )
                    }
                  />
                  {model.display_name}
                </label>
                <p className="text-xs text-muted-foreground">
                  {model.max_input_tokens !== null && model.max_tokens !== null
                    ? `${formatCompactNumber(model.max_input_tokens)} context · ${formatCompactNumber(model.max_tokens)} maximum output · ${formatCompactNumber(Math.min(64000, model.max_tokens))} default output`
                    : "Token limits unavailable. Refresh the catalog before enabling this model."}
                </p>
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
        disabled={readOnly || busy}
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
