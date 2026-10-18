import { useMemo, useState } from "react";
import { Shrink } from "lucide-react";
import { useTranslation } from "react-i18next";

import { AlertMessage } from "@/components/alert-message";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SpinnerBlock } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useModelCompactionRoutes } from "@/features/settings/hooks/use-settings";
import type { CompactionRoute, CompactionRouteModel } from "@/features/settings/schemas";
import { useDialogState } from "@/hooks/use-dialog-state";
import { getErrorMessageOrNull } from "@/utils/errors";

export type CompactionRouteSettingsProps = {
  disabled?: boolean;
};

// Radix Select reserves the empty string, so "keep the client's effort" needs a sentinel.
const CLIENT_EFFORT = "__client__";

type Draft = { slug: string; compactionModel: string; effort: string; isNew: boolean };

/**
 * Settings -> Model catalogue -> Compaction routing: run a coding model's
 * native compaction on another native model, optionally at another effort.
 * Clients keep their model; only the upstream compaction request moves. The
 * backend rejects incompatible routes on save and reports a stored route as
 * inactive (with its reason) while the live catalog makes it incompatible.
 */
export function CompactionRouteSettings({ disabled = false }: CompactionRouteSettingsProps) {
  const { t } = useTranslation();
  const { routesQuery, upsertMutation, deleteMutation } = useModelCompactionRoutes();
  const [draft, setDraft] = useState<Draft | null>(null);
  const removeDialog = useDialogState<CompactionRoute>();

  const error = useMemo(
    () =>
      getErrorMessageOrNull(routesQuery.error) ||
      getErrorMessageOrNull(upsertMutation.error) ||
      getErrorMessageOrNull(deleteMutation.error),
    [routesQuery.error, upsertMutation.error, deleteMutation.error],
  );

  const models = useMemo(() => routesQuery.data?.models ?? [], [routesQuery.data?.models]);
  const routes = routesQuery.data?.routes ?? [];
  const modelsBySlug = useMemo(() => new Map(models.map((model) => [model.slug, model])), [models]);
  const unroutedModels = models.filter((model) => !routes.some((route) => route.slug === model.slug));
  const busy = disabled || upsertMutation.isPending || deleteMutation.isPending;
  const draftEfforts = draft ? (modelsBySlug.get(draft.compactionModel)?.reasoningEfforts ?? []) : [];
  const canSave = !busy && draft !== null && draft.slug !== "" && draft.compactionModel !== "";

  const modelLabel = (slug: string) => modelsBySlug.get(slug)?.displayName ?? slug;

  const handleSave = async () => {
    if (!draft || !canSave) {
      return;
    }
    await upsertMutation.mutateAsync({
      slug: draft.slug,
      compactionModel: draft.compactionModel,
      reasoningEffort: draft.effort === CLIENT_EFFORT ? null : draft.effort,
    });
    setDraft(null);
  };

  const selectCompactionModel = (compactionModel: string) => {
    if (!draft) {
      return;
    }
    const efforts = modelsBySlug.get(compactionModel)?.reasoningEfforts ?? [];
    setDraft({ ...draft, compactionModel, effort: efforts.includes(draft.effort) ? draft.effort : CLIENT_EFFORT });
  };

  const modelSelect = (
    value: string,
    onChange: (slug: string) => void,
    options: CompactionRouteModel[],
    label: string,
  ) => (
    <Select value={value || undefined} onValueChange={onChange} disabled={busy}>
      <SelectTrigger aria-label={label} className="h-8 w-[180px] text-xs">
        <SelectValue placeholder={t("settings.compactionRoutes.form.selectModel")} />
      </SelectTrigger>
      <SelectContent>
        {options.map((model) => (
          <SelectItem key={model.slug} value={model.slug} className="text-xs">
            {model.displayName}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );

  const draftCells = (current: Draft) => (
    <>
      <TableCell>
        {current.isNew ? (
          modelSelect(
            current.slug,
            (slug) => setDraft({ ...current, slug }),
            unroutedModels,
            t("settings.compactionRoutes.form.codingModel"),
          )
        ) : (
          <ModelName name={modelLabel(current.slug)} slug={current.slug} />
        )}
      </TableCell>
      <TableCell>
        {modelSelect(current.compactionModel, selectCompactionModel, models, t("settings.compactionRoutes.form.compactionModel"))}
      </TableCell>
      <TableCell>
        <Select
          value={current.effort}
          onValueChange={(effort) => setDraft({ ...current, effort })}
          disabled={busy || current.compactionModel === ""}
        >
          <SelectTrigger aria-label={t("settings.compactionRoutes.form.effort")} className="h-8 w-[150px] text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={CLIENT_EFFORT} className="text-xs">
              {t("settings.compactionRoutes.clientEffort")}
            </SelectItem>
            {draftEfforts.map((effort) => (
              <SelectItem key={effort} value={effort} className="text-xs">
                {effort}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </TableCell>
      <TableCell />
      <TableCell className="text-right">
        <Button type="button" size="sm" className="h-8 text-xs" disabled={!canSave} onClick={() => void handleSave()}>
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
      </TableCell>
    </>
  );

  return (
    <section id="compaction-routing" className="scroll-mt-16 space-y-3 rounded-xl border bg-card p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <Shrink className="h-4 w-4 text-primary" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">{t("settings.compactionRoutes.title")}</h3>
            <p className="text-xs text-muted-foreground">{t("settings.compactionRoutes.description")}</p>
          </div>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 shrink-0 text-xs"
          disabled={busy || draft !== null || unroutedModels.length === 0}
          onClick={() => setDraft({ slug: "", compactionModel: "", effort: CLIENT_EFFORT, isNew: true })}
        >
          {t("settings.compactionRoutes.actions.add")}
        </Button>
      </div>

      {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}

      {routesQuery.isLoading && !routesQuery.data ? (
        <div className="py-8">
          <SpinnerBlock />
        </div>
      ) : routes.length === 0 && !draft?.isNew ? (
        <p className="rounded-xl border border-dashed px-4 py-6 text-center text-xs text-muted-foreground">
          {t("settings.compactionRoutes.empty")}
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("settings.compactionRoutes.table.codingModel")}</TableHead>
                <TableHead>{t("settings.compactionRoutes.table.compactionModel")}</TableHead>
                <TableHead>{t("settings.compactionRoutes.table.effort")}</TableHead>
                <TableHead>{t("settings.compactionRoutes.table.status")}</TableHead>
                <TableHead className="w-[200px] text-right">{t("apiKeys.table.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {routes.map((route) =>
                draft !== null && !draft.isNew && draft.slug === route.slug ? (
                  <TableRow key={route.slug}>{draftCells(draft)}</TableRow>
                ) : (
                  <TableRow key={route.slug}>
                    <TableCell>
                      <ModelName name={modelLabel(route.slug)} slug={route.slug} />
                    </TableCell>
                    <TableCell>
                      <ModelName name={modelLabel(route.compactionModel)} slug={route.compactionModel} />
                    </TableCell>
                    <TableCell className="text-xs">
                      {route.reasoningEffort ?? (
                        <span className="text-muted-foreground">{t("settings.compactionRoutes.clientEffort")}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {route.status === "active" ? (
                        <Badge variant="secondary" className="text-[10px] font-normal">
                          {t("settings.compactionRoutes.status.active")}
                        </Badge>
                      ) : (
                        <span className="flex flex-col gap-1">
                          <Badge variant="outline" className="w-fit text-[10px] font-normal text-destructive">
                            {t("settings.compactionRoutes.status.inactive")}
                          </Badge>
                          {route.reason ? (
                            <span className="text-[11px] text-muted-foreground">
                              {t(`settings.compactionRoutes.reasons.${route.reason}`, { defaultValue: route.reason })}
                            </span>
                          ) : null}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        disabled={busy || draft !== null}
                        onClick={() =>
                          setDraft({
                            slug: route.slug,
                            compactionModel: route.compactionModel,
                            effort: route.reasoningEffort ?? CLIENT_EFFORT,
                            isNew: false,
                          })
                        }
                      >
                        {t("common.actions.edit")}
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="text-destructive hover:text-destructive"
                        disabled={busy || draft !== null}
                        onClick={() => removeDialog.show(route)}
                      >
                        {t("common.actions.remove")}
                      </Button>
                    </TableCell>
                  </TableRow>
                ),
              )}
              {draft?.isNew ? <TableRow>{draftCells(draft)}</TableRow> : null}
            </TableBody>
          </Table>
        </div>
      )}

      <ConfirmDialog
        open={removeDialog.open}
        title={t("settings.compactionRoutes.removeDialog.title")}
        description={t("settings.compactionRoutes.removeDialog.description", { slug: removeDialog.data?.slug ?? "" })}
        confirmLabel={t("common.actions.remove")}
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

function ModelName({ name, slug }: { name: string; slug: string }) {
  return (
    <span className="flex flex-col">
      <span className="text-xs font-medium">{name}</span>
      <span className="font-mono text-[11px] text-muted-foreground">{slug}</span>
    </span>
  );
}
