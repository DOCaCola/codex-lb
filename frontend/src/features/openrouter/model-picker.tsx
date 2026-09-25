import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import type { OpenRouterAccount, Selection } from "./api";
import { modelSelectionKind, type ModelSelectionKind } from "./model-selection";

type CatalogModel = OpenRouterAccount["state"]["catalog"][number];
const capabilities = {
  "Text generation": (model: CatalogModel) =>
    model.architecture.output_modalities.includes("text"),
  "Image generation": (model: CatalogModel) => model.image !== null,
  Vision: (model: CatalogModel) =>
    model.architecture.input_modalities.includes("image"),
  Tools: (model: CatalogModel) => model.supported_parameters.includes("tools"),
  Reasoning: (model: CatalogModel) =>
    model.supported_parameters.includes("reasoning"),
};
type Capability = keyof typeof capabilities;

export function ModelPicker({
  account,
  onClose,
  onSave,
  busy,
  kind = "models",
}: {
  account: OpenRouterAccount;
  onClose: () => void;
  onSave: (selections: Selection[]) => Promise<void>;
  busy: boolean;
  kind?: ModelSelectionKind;
}) {
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<Capability[]>([]);
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
      ].filter((id) => {
        const model = catalog.get(id);
        return (
          modelSelectionKind(model) === kind &&
          `${id} ${catalog.get(id)?.name ?? ""}`
            .toLowerCase()
            .includes(search.toLowerCase()) &&
          filters.every(
            (capability) => model && capabilities[capability](model),
          )
        );
      }),
    [catalog, search, selected, filters, kind],
  );
  const selectedCount = selected.filter(
    (item) => modelSelectionKind(catalog.get(item.model)) === kind,
  ).length;
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
          <DialogTitle>
            {kind === "images" ? "Image models" : "Models"} · {account.name}
          </DialogTitle>
          <DialogDescription>
            {kind === "images"
              ? "Select image generation and editing models for the public Images API. Conversational selections are preserved. Refresh the account if an image model is missing."
              : "Only selected models are available to clients. Image selections are preserved. New models remain disabled after synchronization."}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-wrap gap-2">
          <Input
            className="min-w-40 flex-1"
            aria-label="Search OpenRouter models"
            placeholder="Search models"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                Capabilities{filters.length > 0 ? ` (${filters.length})` : ""}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Match all selected</DropdownMenuLabel>
              {(Object.keys(capabilities) as Capability[]).map((capability) => (
                <DropdownMenuCheckboxItem
                  key={capability}
                  checked={filters.includes(capability)}
                  onSelect={(event) => event.preventDefault()}
                  onCheckedChange={(checked) =>
                    setFilters((current) =>
                      checked
                        ? [...current, capability]
                        : current.filter((item) => item !== capability),
                    )
                  }
                >
                  {capability}
                </DropdownMenuCheckboxItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuItem
                disabled={filters.length === 0}
                onSelect={() => setFilters([])}
              >
                Clear capability filters
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="max-h-[55vh] space-y-2 overflow-y-auto">
          {ids.length === 0 && (
            <p role="status" className="p-3 text-sm text-muted-foreground">
              No models match your search and capability filters.
            </p>
          )}
          {ids.map((id) => {
            const model = catalog.get(id);
            const imageOnly = kind === "images";
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
                {model?.image && (
                  <div className="mt-1 text-xs text-muted-foreground">
                    Image generation / editing · Public Images API only
                    {model.image.endpoint_details.length === 0 && (
                      <div>
                        Select and save to synchronize endpoint pricing.
                      </div>
                    )}
                    {model.image.endpoint_details.map((endpoint) => (
                      <div key={endpoint.provider_name}>
                        {endpoint.provider_name}:{" "}
                        {endpoint.pricing
                          .map(
                            (line) =>
                              `${line.billable}${line.variant ? ` (${line.variant})` : ""}: $${(line.cost_usd * (line.unit === "token" ? 1e6 : 1)).toLocaleString()} / ${line.unit === "token" ? "1M tokens" : line.unit}`,
                          )
                          .join(" · ") || "Pricing unavailable"}
                      </div>
                    ))}
                  </div>
                )}
                {model && !imageOnly && (
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
                    {!imageOnly && (
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
                    )}
                  </div>
                )}
                {selection && !imageOnly && (
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
            Save {selectedCount} {kind === "images" ? "image models" : "models"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
