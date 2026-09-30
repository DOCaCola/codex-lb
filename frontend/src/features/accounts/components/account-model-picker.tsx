import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

export type AccountModelOption = {
  model: string;
  name: string;
  description: string;
  available: boolean;
};

export function AccountModelPicker({
  name,
  provider,
  catalog,
  selectedModels,
  disabled,
  onClose,
  onSave,
}: {
  name: string;
  provider: string;
  catalog: AccountModelOption[];
  selectedModels: string[];
  disabled: boolean;
  onClose: () => void;
  onSave: (selected: string[]) => Promise<unknown>;
}) {
  const [selected, setSelected] = useState(selectedModels);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const entries = [...catalog];
  for (const model of selectedModels) {
    if (!entries.some((entry) => entry.model === model)) {
      entries.push({
        model,
        name: model,
        description: "Unavailable in the current account catalog",
        available: false,
      });
    }
  }
  const shown = entries.filter((entry) =>
    `${entry.model} ${entry.name}`.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <DialogContent className="max-h-[90dvh] w-[calc(100%-2rem)] max-w-3xl grid-rows-[auto_auto_minmax(0,1fr)_auto] sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Models · {name}</DialogTitle>
          <DialogDescription>
            Choose models for selected mode. Saved choices are retained when All
            models is enabled. Upstream availability and quota still apply.
          </DialogDescription>
        </DialogHeader>
        <Input
          aria-label={`Search ${provider} models`}
          placeholder="Search models"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <div className="max-h-[55vh] space-y-2 overflow-y-auto">
          {shown.length === 0 && (
            <p role="status" className="p-3 text-sm text-muted-foreground">
              No models match your search. Refresh the account if a model is
              missing.
            </p>
          )}
          {shown.map((entry) => (
            <div key={entry.model} className="rounded-lg border p-3 text-sm">
              <label className="flex items-center gap-3">
                <Checkbox
                  checked={selected.includes(entry.model)}
                  disabled={
                    disabled ||
                    busy ||
                    (!entry.available && !selected.includes(entry.model))
                  }
                  onCheckedChange={(checked) =>
                    setSelected((current) =>
                      checked
                        ? [...current, entry.model]
                        : current.filter((model) => model !== entry.model),
                    )
                  }
                />
                <span>
                  {entry.name}
                  {!entry.available ? " — Unavailable" : ""}
                </span>
              </label>
              <p className="mt-1 break-all text-xs text-muted-foreground">
                {entry.model}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {entry.description}
              </p>
            </div>
          ))}
        </div>
        <div className="space-y-2">
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" disabled={busy} onClick={onClose}>
              Cancel
            </Button>
            <Button
              disabled={disabled || busy}
              onClick={async () => {
                setBusy(true);
                setError(null);
                try {
                  await onSave(selected);
                  onClose();
                } catch (cause) {
                  setError(
                    cause instanceof Error
                      ? cause.message
                      : "Could not save models",
                  );
                } finally {
                  setBusy(false);
                }
              }}
            >
              Save {selected.length}{" "}
              {selected.length === 1 ? "model" : "models"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
