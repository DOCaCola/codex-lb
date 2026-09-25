import { Database, Pencil, Plus, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { AlertMessage } from "@/components/alert-message";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { ModelSourceCreateDialog } from "@/features/model-sources/components/model-source-create-dialog";
import { ModelSourceEditDialog } from "@/features/model-sources/components/model-source-edit-dialog";
import { useModelSources } from "@/features/model-sources/hooks/use-model-sources";
import type {
  ModelSource,
  ModelSourceCreateRequest,
  ModelSourceUpdateRequest,
} from "@/features/model-sources/schemas";
import { useDialogState } from "@/hooks/use-dialog-state";
import { getErrorMessageOrNull } from "@/utils/errors";

export type ModelSourcesSettingsProps = {
  disabled?: boolean;
};

function protocolBadges(source: ModelSource) {
  return [
    source.supportsChatCompletions ? "chat" : null,
    source.supportsResponses ? "responses" : null,
    source.supportsAudioTranscriptions ? "audio" : null,
    source.supportsEmbeddings ? "embeddings" : null,
  ].filter((value): value is string => value !== null);
}

export function ModelSourcesSettings({
  disabled = false,
}: ModelSourcesSettingsProps) {
  const { t } = useTranslation();
  const { modelSourcesQuery, createMutation, updateMutation, deleteMutation } =
    useModelSources();
  const createDialog = useDialogState();
  const editDialog = useDialogState<ModelSource>();
  const deleteDialog = useDialogState<ModelSource>();
  const sources = (modelSourcesQuery.data?.sources ?? []).filter(source => source.kind !== "openrouter");
  const busy =
    disabled ||
    modelSourcesQuery.isFetching ||
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending;
  const error =
    getErrorMessageOrNull(modelSourcesQuery.error) ||
    getErrorMessageOrNull(createMutation.error) ||
    getErrorMessageOrNull(updateMutation.error) ||
    getErrorMessageOrNull(deleteMutation.error);

  const createSource = async (payload: ModelSourceCreateRequest) => {
    await createMutation.mutateAsync(payload);
  };

  const updateSource = async (
    sourceId: string,
    payload: ModelSourceUpdateRequest,
  ) => {
    await updateMutation.mutateAsync({ sourceId, payload });
  };

  return (
    <section className="space-y-4 rounded-xl border bg-card p-5">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <Database className="h-4 w-4 text-primary" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">{t("modelSources.title")}</h3>
            <p className="text-xs text-muted-foreground">
              {t("modelSources.description")}
            </p>
          </div>
        </div>
        <Button
          type="button"
          size="sm"
          className="h-8 gap-1.5 text-xs"
          disabled={busy}
          onClick={() => createDialog.show()}
        >
          <Plus className="h-3.5 w-3.5" />
          {t("modelSources.actions.addSource")}
        </Button>
      </div>

      {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}

      <div className="space-y-2">
        {sources.length > 0 ? (
          sources.map((source) => (
            <div key={source.id} className="rounded-lg border p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{source.name}</span>
                    <Badge variant={source.isEnabled ? "default" : "secondary"}>
                      {source.isEnabled
                        ? t("common.states.enabled")
                        : t("common.states.disabled")}
                    </Badge>
                    {protocolBadges(source).map((protocol) => (
                      <Badge key={protocol} variant="secondary">
                        {protocol}
                      </Badge>
                    ))}
                  </div>
                  <div className="truncate text-xs text-muted-foreground">
                    {source.baseUrl}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Switch
                    aria-label={t("modelSources.actions.toggleAria", {
                      name: source.name,
                    })}
                    checked={source.isEnabled}
                    disabled={busy}
                    onCheckedChange={(checked) =>
                      void updateMutation.mutateAsync({
                        sourceId: source.id,
                        payload: { isEnabled: checked },
                      })
                    }
                  />
                  <Button
                    type="button"
                    size="icon-sm"
                    variant="ghost"
                    disabled={busy}
                    onClick={() => editDialog.show(source)}
                  >
                    <Pencil className="size-4" />
                    <span className="sr-only">
                      {t("modelSources.actions.editAria", {
                        name: source.name,
                      })}
                    </span>
                  </Button>
                  <Button
                    type="button"
                    size="icon-sm"
                    variant="ghost"
                    disabled={busy}
                    onClick={() => deleteDialog.show(source)}
                  >
                    <Trash2 className="size-4" />
                    <span className="sr-only">
                      {t("modelSources.actions.deleteAria", {
                        name: source.name,
                      })}
                    </span>
                  </Button>
                </div>
              </div>
              <div className="mt-3 space-y-2 border-t pt-3">
                {source.models.map((model) => (
                  <div
                    key={model.id}
                    className="space-y-1 rounded-md bg-muted/40 p-2 text-xs"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="break-all font-medium">
                        {model.displayName || model.model}
                      </span>
                      {!model.isEnabled ? (
                        <Badge variant="secondary">
                          {t("common.states.disabled")}
                        </Badge>
                      ) : null}
                    </div>
                    {model.displayName && model.displayName !== model.model ? (
                      <div className="break-all text-muted-foreground">
                        {model.model}
                      </div>
                    ) : null}
                    <div className="text-muted-foreground">
                      {t("modelSources.fields.pricing")}
                    </div>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 tabular-nums">
                      <span>
                        {t("common.units.input")}:{" "}
                        {model.inputPer1M === null
                          ? "—"
                          : `$${model.inputPer1M}`}
                      </span>
                      <span>
                        {t("common.units.cached")}:{" "}
                        {model.cachedInputPer1M === null
                          ? "—"
                          : `$${model.cachedInputPer1M}`}
                      </span>
                      <span>
                        {t("common.units.output")}:{" "}
                        {model.outputPer1M === null
                          ? "—"
                          : `$${model.outputPer1M}`}
                      </span>
                      {model.audioPerMinute !== null ? (
                        <span>
                          {t("modelSources.fields.perMinute")}: $
                          {model.audioPerMinute}
                        </span>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        ) : (
          <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
            {t("modelSources.empty")}
          </div>
        )}
      </div>

      <ModelSourceCreateDialog
        open={createDialog.open}
        busy={createMutation.isPending}
        onOpenChange={createDialog.onOpenChange}
        onSubmit={createSource}
      />

      <ModelSourceEditDialog
        open={editDialog.open}
        busy={updateMutation.isPending}
        source={editDialog.data}
        onOpenChange={editDialog.onOpenChange}
        onSubmit={updateSource}
      />

      <ConfirmDialog
        open={deleteDialog.open}
        title={t("modelSources.deleteDialog.title")}
        description={t("modelSources.deleteDialog.description")}
        confirmLabel={t("common.actions.delete")}
        onOpenChange={deleteDialog.onOpenChange}
        onConfirm={() => {
          if (!deleteDialog.data) return;
          void deleteMutation
            .mutateAsync(deleteDialog.data.id)
            .finally(() => deleteDialog.hide());
        }}
      />
    </section>
  );
}
