import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { useDialogState } from "@/hooks/use-dialog-state";
import { getErrorMessageOrNull } from "@/utils/errors";
import { ModelSourceAccountDetail } from "./account-detail";
import { ModelSourceCreateDialog } from "./components/model-source-create-dialog";
import { ModelSourceEditDialog } from "./components/model-source-edit-dialog";
import { useModelSources } from "./hooks/use-model-sources";
import type { ModelSource } from "./schemas";

export function ModelSourceAccountControls({
  readOnly = false,
  source,
  onCreated,
  children,
}: {
  readOnly?: boolean;
  source: ModelSource | null;
  onCreated: (id: string) => void;
  children: (controls: { onAdd: () => void; detail: ReactNode }) => ReactNode;
}) {
  const { t } = useTranslation();
  const { createMutation, updateMutation, deleteMutation } = useModelSources();
  const accountColors = useAccountColorHexes();
  const createDialog = useDialogState();
  const editDialog = useDialogState<ModelSource>();
  const deleteDialog = useDialogState<ModelSource>();
  const busy = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;
  const error = getErrorMessageOrNull(updateMutation.error) || getErrorMessageOrNull(deleteMutation.error);
  return (
    <>
      {children({
        onAdd: () => createDialog.show(),
        detail: source ? (
          <ModelSourceAccountDetail
            source={source}
            color={accountColors.modelSources.get(source.id)}
            readOnly={readOnly}
            busy={busy}
            error={error ?? undefined}
            onRename={(name) => updateMutation.mutateAsync({ sourceId: source.id, payload: { name } })}
            onToggle={(isEnabled) => updateMutation.mutate({ sourceId: source.id, payload: { isEnabled } })}
            onEdit={() => editDialog.show(source)}
            onDelete={() => deleteDialog.show(source)}
          />
        ) : null,
      })}
      <ModelSourceCreateDialog
        open={createDialog.open}
        busy={createMutation.isPending}
        onOpenChange={createDialog.onOpenChange}
        onSubmit={async (payload) => {
          const created = await createMutation.mutateAsync(payload);
          onCreated(created.id);
        }}
      />
      <ModelSourceEditDialog
        open={editDialog.open}
        busy={updateMutation.isPending}
        source={editDialog.data}
        onOpenChange={editDialog.onOpenChange}
        onSubmit={async (sourceId, payload) => {
          await updateMutation.mutateAsync({ sourceId, payload });
        }}
      />
      <ConfirmDialog
        open={deleteDialog.open}
        title={t("modelSources.deleteDialog.title")}
        description={t("modelSources.deleteDialog.description")}
        confirmLabel={t("common.actions.delete")}
        confirmDisabled={deleteMutation.isPending}
        onOpenChange={deleteDialog.onOpenChange}
        onConfirm={async () => {
          if (deleteDialog.data) {
            await deleteMutation.mutateAsync(deleteDialog.data.id);
            deleteDialog.hide();
          }
        }}
      />
    </>
  );
}
