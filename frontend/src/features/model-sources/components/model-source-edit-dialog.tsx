import { useReducer, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Form } from "@/components/ui/form";
import { ModelSourceModelEditor } from "./model-source-model-editor";
import {
  useModelRows,
  modelRowsToInputs,
  validateModelRows,
} from "./model-source-model-draft";
import { ModelSourceFormFields } from "@/features/model-sources/components/model-source-form-fields";
import {
  createModelSourceFormSchema,
  draftFromSource,
  modelSourceDraftReducer,
  type ModelSourceFormValues,
} from "@/features/model-sources/components/model-source-form";
import type {
  ModelSource,
  ModelSourceUpdateRequest,
} from "@/features/model-sources/schemas";

export type ModelSourceEditDialogProps = {
  open: boolean;
  busy: boolean;
  source: ModelSource | null;
  onOpenChange: (open: boolean) => void;
  onSubmit: (
    sourceId: string,
    payload: ModelSourceUpdateRequest,
  ) => Promise<void>;
};

type ModelSourceEditFormProps = {
  source: ModelSource;
  busy: boolean;
  onSubmit: (
    sourceId: string,
    payload: ModelSourceUpdateRequest,
  ) => Promise<void>;
  onClose: () => void;
};

function ModelSourceEditForm({
  source,
  busy,
  onSubmit,
  onClose,
}: ModelSourceEditFormProps) {
  const { t } = useTranslation();
  const form = useForm<ModelSourceFormValues>({
    resolver: zodResolver(createModelSourceFormSchema(t)),
    defaultValues: {
      name: source.name,
      baseUrl: source.baseUrl,
      apiKey: "",
    },
  });
  const [draft, updateDraft] = useReducer(
    modelSourceDraftReducer,
    source,
    draftFromSource,
  );

  const [rows, setRows] = useModelRows(source);
  const [initialModels] = useState(() => modelRowsToInputs(rows));

  const handleSubmit = async (values: ModelSourceFormValues) => {
    if (!validateModelRows(rows)) {
      form.setError("root.models", {
        message: t("modelSources.modelEditor.validation"),
      });
      return;
    }
    const payload: ModelSourceUpdateRequest = {
      name: values.name,
      baseUrl: values.baseUrl,
      supportsChatCompletions: draft.supportsChatCompletions,
      supportsResponses: draft.supportsResponses,
      supportsAudioTranscriptions: draft.supportsAudioTranscriptions,
      supportsEmbeddings: draft.supportsEmbeddings,
    };

    const models = modelRowsToInputs(rows);
    if (JSON.stringify(models) !== JSON.stringify(initialModels))
      payload.models = models;

    // The stored key is never returned, so a blank field means "keep it";
    // only a typed value updates the credential.
    const apiKey = values.apiKey.trim();
    if (apiKey) {
      payload.apiKey = apiKey;
    }
    try {
      await onSubmit(source.id, payload);
    } catch {
      return;
    }
    onClose();
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(handleSubmit)}
        className="flex min-h-0 flex-1 flex-col"
      >
        <div
          className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain px-6 pb-4"
          data-testid="model-source-edit-scroll-region"
        >
          <ModelSourceFormFields
            control={form.control}
            draft={draft}
            updateDraft={updateDraft}
            apiKeyLabel={t("modelSources.fields.upstreamApiKey")}
            apiKeyPlaceholder={t("modelSources.editDialog.keepCurrentKey")}
          />
          <ModelSourceModelEditor
            rows={rows}
            control={form.control}
            onChange={(next) => {
              setRows(next);
              form.clearErrors("root.models");
            }}
          />
          {form.formState.errors.root?.models ? (
            <p role="alert" className="text-sm text-destructive">
              {form.formState.errors.root?.models.message}
            </p>
          ) : null}
        </div>
        <DialogFooter className="shrink-0 border-t px-6 py-4">
          <Button type="submit" disabled={busy || form.formState.isSubmitting}>
            {t("common.actions.save")}
          </Button>
        </DialogFooter>
      </form>
    </Form>
  );
}

export function ModelSourceEditDialog({
  open,
  busy,
  source,
  onOpenChange,
  onSubmit,
}: ModelSourceEditDialogProps) {
  const { t } = useTranslation();
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[calc(100dvh-2rem)] flex-col gap-0 overflow-clip p-0 sm:max-w-2xl">
        <DialogHeader className="shrink-0 px-6 pt-6 pr-12 pb-2">
          <DialogTitle>{t("modelSources.editDialog.title")}</DialogTitle>
          <DialogDescription>
            {t("modelSources.editDialog.description")}
          </DialogDescription>
        </DialogHeader>

        {source ? (
          <ModelSourceEditForm
            key={`${source.id}:${open ? "open" : "closed"}`}
            source={source}
            busy={busy}
            onSubmit={onSubmit}
            onClose={() => onOpenChange(false)}
          />
        ) : (
          <p className="px-6 pb-6 text-sm text-muted-foreground">
            {t("modelSources.editDialog.selectSource")}
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}
