import { Fragment, useMemo, useState } from "react";
import { BookOpen, Info } from "lucide-react";
import { useTranslation } from "react-i18next";

import { AlertMessage } from "@/components/alert-message";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SpinnerBlock } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useModelContextWindowOverrides } from "@/features/settings/hooks/use-settings";
import type { ModelCatalogueEntry, ModelContextWindowOverride } from "@/features/settings/schemas";
import { useDialogState } from "@/hooks/use-dialog-state";
import { cn } from "@/lib/utils";
import { getErrorMessageOrNull } from "@/utils/errors";

export type ModelCatalogueSettingsProps = {
  disabled?: boolean;
};

type Draft = { slug: string; contextWindow: string };

type ListFilter = "all" | "listed" | "hidden";

const LIST_FILTERS: ListFilter[] = ["all", "listed", "hidden"];

function parseContextWindow(value: string): number | null {
  const trimmed = value.trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isSafeInteger(parsed) && parsed >= 1 ? parsed : null;
}

/**
 * Settings -> Model catalogue: one row per text model currently offered to
 * clients, with its default window, the maximum an override may report, and
 * the window clients receive. Clients compact at 90% of that window. Rows are
 * grouped by provider in catalogue order.
 *
 * A dashboard override wins for its slug; an override inherited from
 * `CODEX_LB_MODEL_CONTEXT_WINDOW_OVERRIDES` is read-only until overridden, and
 * removing a dashboard override returns the model to the environment entry or
 * to its default.
 *
 * The "Client lists" switch hides a model from client model pickers; hidden
 * models stay usable by name.
 */
export function ModelCatalogueSettings({ disabled = false }: ModelCatalogueSettingsProps) {
  const { t } = useTranslation();
  const { overridesQuery, upsertMutation, deleteMutation, visibilityMutation } = useModelContextWindowOverrides();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [listFilter, setListFilter] = useState<ListFilter>("all");
  const removeDialog = useDialogState<ModelContextWindowOverride>();

  const error = useMemo(
    () =>
      getErrorMessageOrNull(overridesQuery.error) ||
      getErrorMessageOrNull(upsertMutation.error) ||
      getErrorMessageOrNull(deleteMutation.error) ||
      getErrorMessageOrNull(visibilityMutation.error),
    [overridesQuery.error, upsertMutation.error, deleteMutation.error, visibilityMutation.error],
  );

  const models = useMemo(() => overridesQuery.data?.models ?? [], [overridesQuery.data?.models]);
  const overrides = useMemo(
    () => new Map((overridesQuery.data?.overrides ?? []).map((override) => [override.slug, override])),
    [overridesQuery.data?.overrides],
  );
  const busy = disabled || upsertMutation.isPending || deleteMutation.isPending || visibilityMutation.isPending;
  const filterCounts: Record<ListFilter, number> = {
    all: models.length,
    listed: models.filter((model) => model.listed).length,
    hidden: models.filter((model) => !model.listed).length,
  };
  const providerGroups = useMemo(() => {
    const groups = new Map<string, ModelCatalogueEntry[]>();
    for (const model of models) {
      groups.set(model.provider, [...(groups.get(model.provider) ?? []), model]);
    }
    return [...groups.entries()].map(([provider, entries]) => ({
      provider,
      hiddenCount: entries.filter((model) => !model.listed).length,
      models: entries.filter((model) => listFilter === "all" || (listFilter === "listed") === model.listed),
    }));
  }, [models, listFilter]);
  const shownGroups = providerGroups.filter((group) => group.models.length > 0);

  const draftModel = draft ? models.find((model) => model.slug === draft.slug) : undefined;
  const draftWindow = draft ? parseContextWindow(draft.contextWindow) : null;
  const aboveMaximum =
    draftWindow !== null && draftModel?.maxContextWindow != null && draftWindow > draftModel.maxContextWindow;
  const canSave = !busy && draftWindow !== null && !aboveMaximum;

  const handleSave = async () => {
    if (!draft || !canSave || draftWindow === null) {
      return;
    }
    await upsertMutation.mutateAsync({ slug: draft.slug, contextWindow: draftWindow });
    setDraft(null);
  };

  const startEditing = (model: ModelCatalogueEntry) => {
    const current = overrides.get(model.slug)?.contextWindow ?? model.defaultContextWindow;
    setDraft({ slug: model.slug, contextWindow: String(current) });
  };

  return (
    <section id="model-catalogue" className="scroll-mt-16 space-y-3 rounded-xl border bg-card p-5">
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
          <BookOpen className="h-4 w-4 text-primary" aria-hidden="true" />
        </div>
        <div>
          <h3 className="text-sm font-semibold">{t("settings.modelCatalogue.title")}</h3>
          <p className="text-xs text-muted-foreground">{t("settings.modelCatalogue.description")}</p>
        </div>
      </div>

      {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}

      {overridesQuery.isLoading && !overridesQuery.data ? (
        <div className="py-8">
          <SpinnerBlock />
        </div>
      ) : models.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title={t("settings.modelCatalogue.empty.title")}
          description={t("settings.modelCatalogue.empty.description")}
        />
      ) : (
        <div className="space-y-2">
          <div
            className="inline-flex h-8 items-center rounded-md border bg-background p-0.5"
            role="radiogroup"
            aria-label={t("settings.modelCatalogue.filter.label")}
          >
            {LIST_FILTERS.map((option) => {
              const selected = listFilter === option;
              return (
                <button
                  key={option}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => setListFilter(option)}
                  className={cn(
                    "inline-flex h-6 items-center gap-1.5 rounded-[5px] px-2.5 text-xs text-muted-foreground transition-colors",
                    selected
                      ? "bg-accent text-accent-foreground shadow-sm"
                      : "hover:bg-accent/60 hover:text-accent-foreground",
                  )}
                >
                  {t(`settings.modelCatalogue.filter.${option}`)}{" "}
                  <span className="text-[11px] tabular-nums text-muted-foreground">{filterCounts[option]}</span>
                </button>
              );
            })}
          </div>
          <div className="overflow-x-auto rounded-xl border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("settings.modelCatalogue.table.model")}</TableHead>
                  <TableHead className="text-right">{t("settings.modelCatalogue.table.default")}</TableHead>
                  <TableHead className="text-right">{t("settings.modelCatalogue.table.maximum")}</TableHead>
                  <TableHead>{t("settings.modelCatalogue.table.contextWindow")}</TableHead>
                  <TableHead>{t("settings.modelCatalogue.table.clientLists")}</TableHead>
                  <TableHead className="w-[200px] text-right">{t("apiKeys.table.actions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shownGroups.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="py-6 text-center text-xs text-muted-foreground">
                      {t("settings.modelCatalogue.filter.empty")}
                    </TableCell>
                  </TableRow>
                ) : null}
                {shownGroups.map((group) => (
                  <Fragment key={group.provider}>
                    <TableRow className="bg-muted/40 hover:bg-muted/40">
                      <TableCell
                        colSpan={6}
                        className="py-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
                      >
                        {t(`settings.modelCatalogue.provider.${group.provider}`, group.provider)}
                        {group.hiddenCount > 0 ? (
                          <span className="ml-1.5 font-normal normal-case tracking-normal">
                            {t("settings.modelCatalogue.groupHidden", {
                              count: group.hiddenCount,
                            })}
                          </span>
                        ) : null}
                      </TableCell>
                    </TableRow>
                    {group.models.map((model) => {
                      const override = overrides.get(model.slug);
                      const editing = draft?.slug === model.slug;
                      const dimmed = !model.listed && "opacity-60";
                      return (
                        <TableRow key={model.slug}>
                          <TableCell>
                            <span className={cn("flex flex-col", dimmed)}>
                              <span className="text-xs font-medium">{model.displayName}</span>
                              <span className="font-mono text-[11px] text-muted-foreground">{model.slug}</span>
                            </span>
                          </TableCell>
                          <TableCell className={cn("text-right text-xs tabular-nums", dimmed)}>
                            {model.defaultContextWindow.toLocaleString()}
                          </TableCell>
                          <TableCell className={cn("text-right text-xs tabular-nums", dimmed)}>
                            {model.maxContextWindow !== null ? model.maxContextWindow.toLocaleString() : "—"}
                          </TableCell>
                          <TableCell className={cn(dimmed)}>
                            {editing && draft ? (
                              <span className="flex flex-col gap-1">
                                <Input
                                  aria-label={t("settings.modelCatalogue.form.contextWindowLabel", {
                                    model: model.slug,
                                  })}
                                  value={draft.contextWindow}
                                  onChange={(event) =>
                                    setDraft({
                                      slug: model.slug,
                                      contextWindow: event.target.value,
                                    })
                                  }
                                  onKeyDown={(event) => {
                                    if (event.key === "Enter") {
                                      void handleSave();
                                    }
                                  }}
                                  inputMode="numeric"
                                  className="h-8 max-w-[140px] text-xs tabular-nums"
                                  disabled={busy}
                                  autoFocus
                                />
                                {aboveMaximum && model.maxContextWindow !== null ? (
                                  <span className="text-[11px] text-destructive">
                                    {t("settings.modelCatalogue.aboveMaximum", {
                                      value: model.maxContextWindow.toLocaleString(),
                                    })}
                                  </span>
                                ) : null}
                              </span>
                            ) : override ? (
                              <span className="flex flex-col gap-1">
                                <span className="text-xs tabular-nums">{override.contextWindow.toLocaleString()}</span>
                                {override.source === "dashboard" ? (
                                  <span className="flex flex-wrap items-center gap-1">
                                    <Badge variant="secondary" className="text-[10px] font-normal">
                                      {t("settings.modelCatalogue.source.dashboard")}
                                    </Badge>
                                    {override.envValue !== null ? (
                                      <span className="text-[11px] text-muted-foreground">
                                        {t("settings.modelCatalogue.source.environmentValue", {
                                          value: override.envValue.toLocaleString(),
                                        })}
                                      </span>
                                    ) : null}
                                  </span>
                                ) : (
                                  <Badge variant="outline" className="w-fit text-[10px] font-normal">
                                    {t("settings.inherit.environment", {
                                      value: override.contextWindow.toLocaleString(),
                                    })}
                                  </Badge>
                                )}
                              </span>
                            ) : (
                              <span className="text-xs text-muted-foreground">
                                {t("settings.modelCatalogue.source.default")}
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            <span className="flex items-center gap-2 text-[11px] text-muted-foreground">
                              <Switch
                                checked={model.listed}
                                onCheckedChange={(listed) =>
                                  visibilityMutation.mutate({
                                    slug: model.slug,
                                    listed,
                                  })
                                }
                                disabled={busy}
                                aria-label={t("settings.modelCatalogue.form.listedLabel", { model: model.slug })}
                              />
                              {model.listed ? t("settings.modelCatalogue.listed") : t("settings.modelCatalogue.hidden")}
                            </span>
                          </TableCell>
                          <TableCell className="text-right">
                            {editing ? (
                              <>
                                <Button
                                  type="button"
                                  size="sm"
                                  className="h-8 text-xs"
                                  disabled={!canSave}
                                  onClick={() => void handleSave()}
                                >
                                  {t("common.actions.save")}
                                </Button>
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  className="h-8 text-xs"
                                  disabled={busy}
                                  onClick={() => setDraft(null)}
                                >
                                  {t("common.cancel")}
                                </Button>
                              </>
                            ) : (
                              <>
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  disabled={busy}
                                  onClick={() => startEditing(model)}
                                >
                                  {override?.source === "dashboard"
                                    ? t("common.actions.edit")
                                    : t("settings.modelCatalogue.actions.override")}
                                </Button>
                                {override?.source === "dashboard" ? (
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="ghost"
                                    className="text-destructive hover:text-destructive"
                                    disabled={busy}
                                    onClick={() => removeDialog.show(override)}
                                  >
                                    {override.envValue !== null
                                      ? t("settings.inherit.reset")
                                      : t("common.actions.remove")}
                                  </Button>
                                ) : null}
                              </>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="flex items-start gap-1.5 text-[11px] text-muted-foreground">
            <Info className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" />
            {t("settings.modelCatalogue.cacheNote")}
          </p>
        </div>
      )}

      <ConfirmDialog
        open={removeDialog.open}
        title={
          removeDialog.data?.envValue != null
            ? t("settings.modelCatalogue.removeDialog.resetTitle")
            : t("settings.modelCatalogue.removeDialog.title")
        }
        description={
          removeDialog.data?.envValue != null
            ? t("settings.modelCatalogue.removeDialog.resetDescription", {
                slug: removeDialog.data?.slug ?? "",
                value: removeDialog.data?.envValue.toLocaleString() ?? "",
              })
            : t("settings.modelCatalogue.removeDialog.description", {
                slug: removeDialog.data?.slug ?? "",
              })
        }
        confirmLabel={removeDialog.data?.envValue != null ? t("settings.inherit.reset") : t("common.actions.remove")}
        onOpenChange={removeDialog.onOpenChange}
        onConfirm={() => {
          if (!removeDialog.data) {
            return;
          }
          void deleteMutation.mutateAsync(removeDialog.data.slug).finally(() => {
            removeDialog.hide();
          });
        }}
      />
    </section>
  );
}
