import { KeySquare } from "lucide-react";
import { lazy, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { AlertMessage } from "@/components/alert-message";
import { Button } from "@/components/ui/button";
import { useDialogState } from "@/hooks/use-dialog-state";
import { ApiKeyAuthToggle } from "@/features/api-keys/components/api-key-auth-toggle";
import { ApiKeyQuotaPrivacyToggle } from "@/features/api-keys/components/api-key-quota-privacy-toggle";
import { ApiKeyCreatedDialog } from "@/features/api-keys/components/api-key-created-dialog";
import { ApiKeyTable } from "@/features/api-keys/components/api-key-table";
import { useApiKeys } from "@/features/api-keys/hooks/use-api-keys";
import type { ApiKey, ApiKeyCreateRequest } from "@/features/api-keys/schemas";
import { keyHref } from "@/features/apis/key-summary";
import { getErrorMessageOrNull } from "@/utils/errors";

const ApiKeyCreateDialog = lazy(() =>
  import("@/features/api-keys/components/api-key-create-dialog").then((m) => ({ default: m.ApiKeyCreateDialog })),
);

export type ApiKeysSectionProps = {
  apiKeyAuthEnabled: boolean;
  hideUpstreamQuotaFromApiKeys: boolean;
  disabled?: boolean;
  /** The auth and quota-privacy toggles are security settings (`security:write`). */
  policyControlsDisabled?: boolean;
  onApiKeyAuthEnabledChange: (enabled: boolean) => void;
  onHideUpstreamQuotaFromApiKeysChange: (enabled: boolean) => void;
};

export function ApiKeysSection({
  apiKeyAuthEnabled,
  hideUpstreamQuotaFromApiKeys,
  disabled = false,
  policyControlsDisabled = disabled,
  onApiKeyAuthEnabledChange,
  onHideUpstreamQuotaFromApiKeysChange,
}: ApiKeysSectionProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    apiKeysQuery,
    createMutation,
    deleteMutation,
    regenerateMutation,
  } = useApiKeys();

  const createDialog = useDialogState();
  const deleteDialog = useDialogState<ApiKey>();
  const createdDialog = useDialogState<string>();

  const keys = apiKeysQuery.data ?? [];
  const busy =
    disabled ||
    apiKeysQuery.isFetching ||
    createMutation.isPending ||
    deleteMutation.isPending ||
    regenerateMutation.isPending;

  const mutationError = useMemo(
    () =>
      getErrorMessageOrNull(createMutation.error) ||
      getErrorMessageOrNull(deleteMutation.error) ||
      getErrorMessageOrNull(regenerateMutation.error),
    [createMutation.error, deleteMutation.error, regenerateMutation.error],
  );

  const handleCreate = async (payload: ApiKeyCreateRequest) => {
    const created = await createMutation.mutateAsync(payload);
    createdDialog.show(created.key);
  };

  return (
    <section className="space-y-3 rounded-xl border bg-card p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <KeySquare className="h-4 w-4 text-primary" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">{t("apiKeys.section.title")}</h3>
            <p className="text-xs text-muted-foreground">{t("apiKeys.section.description")}</p>
          </div>
        </div>
        <Button type="button" size="sm" className="h-8 text-xs" onClick={() => createDialog.show()} disabled={busy}>
          {t("apiKeys.section.createKey")}
        </Button>
      </div>

      <ApiKeyAuthToggle
        enabled={apiKeyAuthEnabled}
        disabled={busy || policyControlsDisabled}
        onChange={onApiKeyAuthEnabledChange}
      />

      <ApiKeyQuotaPrivacyToggle
        enabled={hideUpstreamQuotaFromApiKeys}
        disabled={busy || policyControlsDisabled}
        onChange={onHideUpstreamQuotaFromApiKeysChange}
      />

      {mutationError ? <AlertMessage variant="error">{mutationError}</AlertMessage> : null}

      <ApiKeyTable
        keys={keys}
        busy={busy}
        onEdit={(apiKey) => navigate(keyHref(apiKey.id, "settings"))}
        onDelete={(apiKey) => deleteDialog.show(apiKey)}
        onRegenerate={(apiKey) => {
          void regenerateMutation.mutateAsync(apiKey.id).then((result) => {
            createdDialog.show(result.key);
          });
        }}
      />

      <ApiKeyCreateDialog
        open={createDialog.open}
        busy={createMutation.isPending}
        onOpenChange={createDialog.onOpenChange}
        onSubmit={handleCreate}
      />

      <ApiKeyCreatedDialog
        open={createdDialog.open}
        apiKey={createdDialog.data}
        onOpenChange={createdDialog.onOpenChange}
      />

      <ConfirmDialog
        open={deleteDialog.open}
        title={t("apiKeys.deleteDialog.title")}
        description={t("apiKeys.deleteDialog.description")}
        confirmLabel={t("common.actions.delete")}
        onOpenChange={deleteDialog.onOpenChange}
        onConfirm={() => {
          if (!deleteDialog.data) {
            return;
          }
          void deleteMutation.mutateAsync(deleteDialog.data.id).finally(() => {
            deleteDialog.hide();
          });
        }}
      />
    </section>
  );
}
