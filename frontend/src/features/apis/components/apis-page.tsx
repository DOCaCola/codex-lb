import { KeyRound, Plus, ShieldCheck } from "lucide-react";
import { lazy, Suspense, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AlertMessage } from "@/components/alert-message";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { LoadingOverlay } from "@/components/layout/loading-overlay";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useRailCollapsed } from "@/features/accounts/hooks/use-rail-collapsed";
import { ApiKeyCreatedDialog } from "@/features/api-keys/components/api-key-created-dialog";
import type { ApiKey, ApiKeyCreateRequest, ApiKeyUpdateRequest } from "@/features/api-keys/schemas";
import { ApiComparisonTrend } from "@/features/apis/components/api-comparison-trend";
import { ApisSkeleton } from "@/features/apis/components/apis-skeleton";
import { KeyDetail } from "@/features/apis/components/key-detail";
import { KeyRail } from "@/features/apis/components/key-rail";
import { KeysList, type KeyActions } from "@/features/apis/components/keys-list";
import type { ComparisonProvider } from "@/features/apis/comparison-trends";
import {
  useApiKeys,
  useApiKeysTrends,
  useApiKeyTrends,
  useApiKeyUsage7Day,
} from "@/features/apis/hooks/use-apis";
import {
  keyHref,
  keySeriesId,
  keyState,
  lifetimeCostTotal,
  matchesKeyFilter,
  useKeyColors,
  useKeyTab,
  weeklyUsageByKey,
} from "@/features/apis/key-summary";
import { useAuthStore, usePermission } from "@/features/auth/hooks/use-auth";
import { useDialogState } from "@/hooks/use-dialog-state";
import { cn } from "@/lib/utils";
import { getErrorMessageOrNull } from "@/utils/errors";
import { formatCurrency } from "@/utils/formatters";

const ApiKeyCreateDialog = lazy(() =>
  import("@/features/api-keys/components/api-key-create-dialog").then((m) => ({
    default: m.ApiKeyCreateDialog,
  })),
);

/** The API Keys page: every key at /keys, one key at /keys/:keyId and /keys/:keyId/settings. */
export function ApisPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { keyId: selectedId = null } = useParams();
  const tab = useKeyTab();
  // The backend answers every API-key read with 403 for principals without
  // `api_keys:read`, so the queries stay idle and the page explains instead.
  // Mutations still run behind the coarse write alias, so the controls follow it.
  const canReadKeys = usePermission("api_keys:read");
  const canWrite = useAuthStore((state) => state.canWrite);
  const { apiKeysQuery, createMutation, updateMutation, deleteMutation, regenerateMutation } = useApiKeys({
    enabled: canReadKeys,
  });
  const [railCollapsed, toggleRail] = useRailCollapsed();
  const [comparisonProvider, setComparisonProvider] = useState<ComparisonProvider>("all");

  const createDialog = useDialogState();
  const deleteDialog = useDialogState<ApiKey>();
  const createdDialog = useDialogState<string>();

  const apiKeys = useMemo(() => apiKeysQuery.data ?? [], [apiKeysQuery.data]);
  const colors = useKeyColors(apiKeys);
  // Rows and the rail always show each key's usage across all providers.
  const weeksQuery = useApiKeysTrends("all", { enabled: canReadKeys });
  const comparisonQuery = useApiKeysTrends(comparisonProvider, { enabled: canReadKeys });
  const weeks = useMemo(() => weeklyUsageByKey(weeksQuery.data), [weeksQuery.data]);
  const lifetimeTotal = lifetimeCostTotal(apiKeys);
  const selected = selectedId ? (apiKeys.find((apiKey) => apiKey.id === selectedId) ?? null) : null;
  const trendsQuery = useApiKeyTrends(selected?.id ?? null, { enabled: canReadKeys });
  const usage7DayQuery = useApiKeyUsage7Day(selected?.id ?? null, { enabled: canReadKeys });

  const mutationBusy =
    createMutation.isPending || updateMutation.isPending || deleteMutation.isPending || regenerateMutation.isPending;
  const mutationError =
    getErrorMessageOrNull(createMutation.error) ||
    getErrorMessageOrNull(updateMutation.error) ||
    getErrorMessageOrNull(deleteMutation.error) ||
    getErrorMessageOrNull(regenerateMutation.error);
  const listError = getErrorMessageOrNull(apiKeysQuery.error);
  const pageError = mutationError || (apiKeysQuery.data ? listError : null);

  const actions: KeyActions = {
    onRegenerate: (apiKey) => {
      void regenerateMutation
        .mutateAsync(apiKey.id)
        .then((result) => createdDialog.show(result.key))
        .catch(() => null);
    },
    onToggleActive: (apiKey) => {
      void updateMutation.mutateAsync({ keyId: apiKey.id, payload: { isActive: !apiKey.isActive } }).catch(() => null);
    },
  };
  const handleCreate = async (payload: ApiKeyCreateRequest) => {
    const created = await createMutation.mutateAsync(payload);
    createdDialog.show(created.key);
  };
  const update = (apiKey: ApiKey) => (payload: ApiKeyUpdateRequest) =>
    updateMutation.mutateAsync({ keyId: apiKey.id, payload });

  if (!canReadKeys) {
    return (
      <div className="animate-fade-in-up space-y-4">
        <h1 className="text-xl font-semibold tracking-tight">{t("apis.page.title")}</h1>
        <div
          role="status"
          className="flex flex-col items-center gap-2 rounded-xl border border-dashed bg-card p-8 text-center"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <ShieldCheck className="h-5 w-5 text-primary" aria-hidden="true" />
          </div>
          <p className="text-sm font-medium">{t("apis.page.adminOnlyTitle")}</p>
          <p className="text-xs text-muted-foreground">{t("apis.page.adminOnlyDescription")}</p>
        </div>
      </div>
    );
  }

  const activeCount = apiKeys.filter((apiKey) => matchesKeyFilter(keyState(apiKey), "active")).length;
  const weekCost = [...weeks.values()].reduce((sum, week) => sum + week.costUsd, 0);

  return (
    <div className="animate-fade-in-up space-y-4">
      {selectedId === null ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <h1 className="text-xl font-semibold tracking-tight">{t("apis.page.title")}</h1>
          {apiKeys.length > 0 ? (
            <p className="text-sm text-muted-foreground tabular-nums" data-testid="api-keys-summary">
              {t("apis.page.summary", {
                count: apiKeys.length,
                active: activeCount,
                week: formatCurrency(weekCost),
                lifetime: formatCurrency(lifetimeTotal),
              })}
            </p>
          ) : null}
          {canWrite ? (
            <Button type="button" size="sm" className="ml-auto gap-1.5" onClick={() => createDialog.show()}>
              <Plus className="h-3.5 w-3.5" />
              {t("apis.list.createKey")}
            </Button>
          ) : null}
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2 text-[12.5px] text-muted-foreground">
          <Link to="/keys" className="hover:text-foreground">
            {t("apis.page.title")}
          </Link>
          {selected ? (
            <>
              <span aria-hidden="true" className="hidden lg:inline">/</span>
              <span className="hidden truncate text-foreground lg:inline">{selected.name}</span>
              <Select value={selected.id} onValueChange={(id) => navigate(keyHref(id, tab))}>
                <SelectTrigger size="sm" className="h-7 max-w-56 min-w-0 text-xs lg:hidden" aria-label={t("apis.rail.switch")}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {apiKeys.map((apiKey) => (
                    <SelectItem key={apiKey.id} value={apiKey.id}>
                      {apiKey.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          ) : null}
        </div>
      )}

      {pageError ? <AlertMessage variant="error">{pageError}</AlertMessage> : null}

      {apiKeysQuery.isPending && !apiKeysQuery.data ? (
        <ApisSkeleton />
      ) : !apiKeysQuery.data ? (
        <div className="space-y-3 rounded-xl border bg-card p-4">
          <AlertMessage variant="error">{listError ?? t("apiKeys.toasts.loadFailed")}</AlertMessage>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void apiKeysQuery.refetch()}
            disabled={apiKeysQuery.isFetching}
          >
            {t("common.actions.retry")}
          </Button>
        </div>
      ) : selectedId === null ? (
        <>
          <ApiComparisonTrend
            data={comparisonQuery.data}
            loading={comparisonQuery.isPending}
            error={!!comparisonQuery.error}
            onRetry={() => void comparisonQuery.refetch()}
            provider={comparisonProvider}
            onProviderChange={setComparisonProvider}
            colors={colors}
          />
          <KeysList
            apiKeys={apiKeys}
            weeks={weeks}
            colors={colors}
            lifetimeTotal={lifetimeTotal}
            readOnly={!canWrite}
            actions={actions}
          />
        </>
      ) : (
        <div
          data-testid="api-key-detail-layout"
          className={cn(
            "grid min-w-0 grid-cols-1 items-start gap-4",
            railCollapsed ? "lg:grid-cols-[3.5rem_minmax(0,1fr)]" : "lg:grid-cols-[18rem_minmax(0,1fr)]",
          )}
        >
          <KeyRail
            apiKeys={apiKeys}
            selectedId={selectedId}
            colors={colors}
            weeks={weeks}
            collapsed={railCollapsed}
            onToggleCollapsed={toggleRail}
          />
          {selected ? (
            <KeyDetail
              apiKey={selected}
              color={colors.get(keySeriesId(selected.id))}
              lifetimeTotal={lifetimeTotal}
              trends={trendsQuery.data}
              usage={usage7DayQuery.data}
              usageUnavailable={!!usage7DayQuery.error}
              busy={mutationBusy}
              readOnly={!canWrite}
              onSave={update(selected)}
              onResetUsage={() => update(selected)({ resetUsage: true })}
              onRegenerate={() => actions.onRegenerate(selected)}
              onToggleActive={() => actions.onToggleActive(selected)}
              onDelete={() => deleteDialog.show(selected)}
            />
          ) : (
            <div
              className="flex flex-col items-center justify-center rounded-xl border border-dashed p-12 text-center"
              data-testid="api-key-not-found"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
                <KeyRound className="h-5 w-5 text-muted-foreground" />
              </div>
              <p className="mt-3 text-sm font-medium text-muted-foreground">{t("apis.notFound.title")}</p>
              <p className="mt-1 text-xs text-muted-foreground/70">{t("apis.notFound.description")}</p>
              <Button asChild variant="outline" size="sm" className="mt-4">
                <Link to="/keys">{t("apis.rail.all")}</Link>
              </Button>
            </div>
          )}
        </div>
      )}

      <Suspense fallback={null}>
        <ApiKeyCreateDialog
          open={createDialog.open}
          busy={createMutation.isPending}
          onOpenChange={createDialog.onOpenChange}
          onSubmit={handleCreate}
        />
      </Suspense>

      <ApiKeyCreatedDialog open={createdDialog.open} apiKey={createdDialog.data} onOpenChange={createdDialog.onOpenChange} />

      <ConfirmDialog
        open={deleteDialog.open}
        title={t("apiKeys.deleteDialog.title")}
        description={t("apiKeys.deleteDialog.description")}
        confirmLabel={t("common.actions.delete")}
        onOpenChange={deleteDialog.onOpenChange}
        onConfirm={() => {
          const target = deleteDialog.data;
          if (!target) return;
          void deleteMutation
            .mutateAsync(target.id)
            .then(() => {
              if (target.id === selectedId) navigate("/keys");
            })
            .catch(() => null)
            .finally(() => deleteDialog.hide());
        }}
      />

      <LoadingOverlay visible={!!apiKeysQuery.data && mutationBusy} label={t("apiKeys.page.updating")} />
    </div>
  );
}
