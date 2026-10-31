import { ChevronDown, ChevronUp, Plus, UserX } from "lucide-react";
import { Suspense, lazy, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { AlertMessage } from "@/components/alert-message";
import { LoadingOverlay } from "@/components/layout/loading-overlay";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useDialogState } from "@/hooks/use-dialog-state";
import { AccountDetail } from "@/features/accounts/components/account-detail";
import { AccountsSkeleton } from "@/features/accounts/components/accounts-skeleton";
import { AddAccountDialog } from "@/features/accounts/components/add-account-dialog";
import { ImportDialog } from "@/features/accounts/components/import-dialog";
import { ProviderRail } from "@/features/accounts/components/provider-rail";
import { ProvidersList } from "@/features/accounts/components/providers-list";
import { useRailCollapsed } from "@/features/accounts/hooks/use-rail-collapsed";
import { accountHref } from "@/features/accounts/provider-summary";
import { ResetCreditConfirmDialog } from "@/features/accounts/components/reset-credit-confirm-dialog";
import { AuthExportDialog } from "@/features/accounts/components/auth-export-dialog";
import { WindowsOauthHelp } from "@/features/accounts/components/windows-oauth-help";
import {
  useAccounts,
  useAccountUsageResetCredits,
} from "@/features/accounts/hooks/use-accounts";
import { useProviderActivity } from "@/features/accounts/hooks/use-provider-activity";
import { useSummaryContext } from "@/features/accounts/hooks/use-summary-context";
import { PROVIDER_LABELS, buildProviderGroups, needsAttention } from "@/features/accounts/provider-summary";
import {
  DEFAULT_ACCOUNT_SORT_MODE,
  type AccountSortMode,
} from "@/features/accounts/sorting";
import { useOauth } from "@/features/accounts/hooks/use-oauth";
import {
  useSettings,
  useUpstreamProxyAdmin,
} from "@/features/settings/hooks/use-settings";
import type { AccountAuthExportResponse } from "@/features/accounts/schemas";
import { usePermission } from "@/features/auth/hooks/use-auth";
import { getErrorMessageOrNull } from "@/utils/errors";
import { cn } from "@/lib/utils";
import { OpenRouterAccountControls } from "@/features/openrouter/account-controls";
import { useOpenRouterAccounts } from "@/features/openrouter/use-openrouter";
import { ClaudeAccountControls } from "@/features/claude/account-controls";
import { useClaudeAccounts } from "@/features/claude/use-claude";
import { AntigravityAccountControls } from "@/features/antigravity/account-controls";
import { useAntigravityAccounts } from "@/features/antigravity/use-antigravity";
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { ModelSourceAccountControls } from "@/features/model-sources/account-controls";
import { isUserDefinedSource } from "@/features/model-sources/display-values";
import { useModelSourcesList } from "@/features/model-sources/hooks/use-model-sources";

const OauthDialog = lazy(() =>
  import("@/features/accounts/components/oauth-dialog").then((m) => ({
    default: m.OauthDialog,
  })),
);

/** The Providers page: every account grouped by provider at /providers, one account at /providers/:accountId. */
export function ProvidersPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { accountId: selectedId = null } = useParams();
  const [accountSortMode, setAccountSortMode] = useState<AccountSortMode>(
    DEFAULT_ACCOUNT_SORT_MODE,
  );
  const [oauthAccountId, setOauthAccountId] = useState<string | null>(null);
  const [chooserOpen, setChooserOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [railCollapsed, toggleRail] = useRailCollapsed();
  const {
    accountsQuery,
    importMutation,
    pauseMutation,
    resumeMutation,
    setAliasMutation,
    probeMutation,
    usageResetMutation,
    limitWarmupMutation,
    updateMutation,
    deleteMutation,
    routingPolicyMutation,
    creditPolicyMutation,
    exportAuthMutation,
  } = useAccounts();
  const { settingsQuery } = useSettings();
  const canWrite = usePermission("accounts:write");
  const openRouterQuery = useOpenRouterAccounts();
  const claudeQuery = useClaudeAccounts();
  const claudeAccounts = useMemo(
    () => claudeQuery.data?.accounts ?? [],
    [claudeQuery.data],
  );
  const antigravityQuery = useAntigravityAccounts();
  const antigravityAccounts = useMemo(
    () => antigravityQuery.data?.accounts ?? [],
    [antigravityQuery.data],
  );
  const openRouterAccounts = useMemo(
    () => openRouterQuery.data?.accounts ?? [],
    [openRouterQuery.data],
  );
  const modelSourcesQuery = useModelSourcesList();
  const modelSources = useMemo(
    () => (modelSourcesQuery.data?.sources ?? []).filter(isUserDefinedSource),
    [modelSourcesQuery.data],
  );
  // Upstream-proxy administration is an ops:write read on the backend; cached
  // data from an earlier admin session must not be rendered either.
  const canReadUpstreamProxy = usePermission("ops:write");
  const { upstreamProxyQuery, accountBindingMutation, testEndpointMutation } =
    useUpstreamProxyAdmin({
      enabled: canReadUpstreamProxy,
    });
  const oauth = useOauth();
  const accountColors = useAccountColorHexes();
  const { activity, available: activityAvailable } = useProviderActivity();
  const { t: summaryT, quotaDisplay, subscriptionEnds } = useSummaryContext();

  const importDialog = useDialogState();
  const oauthDialog = useDialogState();
  const deleteDialog = useDialogState<string>();
  type ResetCreditDialogTarget = {
    accountId: string;
    availableResetCredits: number;
  };
  const resetCreditDialog = useDialogState<ResetCreditDialogTarget>();
  const usageResetDialog = useDialogState<string>();
  const exportDialog = useDialogState<AccountAuthExportResponse>();
  const [deleteHistory, setDeleteHistory] = useState(false);

  const accounts = useMemo(
    () => accountsQuery.data ?? [],
    [accountsQuery.data],
  );
  const showResetCreditBadges =
    settingsQuery.data?.showResetCreditBadges ?? true;
  const showResetCreditExpiryBadge =
    settingsQuery.data?.showResetCreditExpiryBadge ?? true;
  const limitWarmupGloballyEnabled = settingsQuery.data?.limitWarmupEnabled;

  const groups = useMemo(
    () =>
      buildProviderGroups(
        { accounts, claudeAccounts, antigravityAccounts, openRouterAccounts, modelSources },
        accountSortMode,
        { t: summaryT, quotaDisplay, subscriptionEnds },
      ),
    [accounts, claudeAccounts, antigravityAccounts, openRouterAccounts, modelSources, accountSortMode, summaryT, quotaDisplay, subscriptionEnds],
  );
  const summaries = groups.flatMap((group) => group.summaries);
  const selectedSummary = summaries.find((summary) => summary.id === selectedId) ?? null;
  const selectedClaudeAccount = selectedSummary?.entry.kind === "claude" ? selectedSummary.entry.account : null;
  const selectedAntigravityAccount = selectedSummary?.entry.kind === "antigravity" ? selectedSummary.entry.account : null;
  const selectedOpenRouterAccount = selectedSummary?.entry.kind === "openrouter" ? selectedSummary.entry.account : null;
  const selectedModelSource = selectedSummary?.entry.kind === "openai_compatible" ? selectedSummary.entry.account : null;
  const selectedAccount = selectedSummary?.entry.kind === "codex" ? selectedSummary.entry.account : null;
  const resetCreditsQuery = useAccountUsageResetCredits(
    selectedAccount?.accountId ?? null,
  );
  const providersLoading =
    !accountsQuery.data ||
    claudeQuery.isLoading ||
    antigravityQuery.isLoading ||
    openRouterQuery.isLoading ||
    modelSourcesQuery.isLoading;
  const openAccount = (id: string) => navigate(accountHref(id));

  const mutationBusy =
    importMutation.isPending ||
    pauseMutation.isPending ||
    resumeMutation.isPending ||
    setAliasMutation.isPending ||
    probeMutation.isPending ||
    usageResetMutation.isPending ||
    limitWarmupMutation.isPending ||
    deleteMutation.isPending ||
    routingPolicyMutation.isPending ||
    creditPolicyMutation.isPending ||
    exportAuthMutation.isPending ||
    updateMutation.isPending ||
    accountBindingMutation.isPending ||
    testEndpointMutation.isPending;

  const mutationError =
    getErrorMessageOrNull(importMutation.error) ||
    getErrorMessageOrNull(pauseMutation.error) ||
    getErrorMessageOrNull(resumeMutation.error) ||
    getErrorMessageOrNull(setAliasMutation.error) ||
    getErrorMessageOrNull(probeMutation.error) ||
    getErrorMessageOrNull(usageResetMutation.error) ||
    getErrorMessageOrNull(limitWarmupMutation.error) ||
    getErrorMessageOrNull(deleteMutation.error) ||
    getErrorMessageOrNull(routingPolicyMutation.error) ||
    getErrorMessageOrNull(creditPolicyMutation.error) ||
    getErrorMessageOrNull(exportAuthMutation.error) ||
    getErrorMessageOrNull(updateMutation.error) ||
    getErrorMessageOrNull(settingsQuery.error) ||
    getErrorMessageOrNull(upstreamProxyQuery.error) ||
    getErrorMessageOrNull(accountBindingMutation.error) ||
    getErrorMessageOrNull(testEndpointMutation.error);

  const readyCount = summaries.filter((summary) => summary.tone === "ok").length;
  const attentionCount = summaries.filter(needsAttention).length;
  const pausedCount = summaries.filter((summary) => summary.status === "paused").length;

  return (
    <ClaudeAccountControls
      account={selectedClaudeAccount}
      onCreated={openAccount}
      readOnly={!canWrite}
    >
      {({ onSignIn: onClaudeSignIn, onImport: onClaudeImport, detail: claudeDetail }) => (
        <AntigravityAccountControls
          account={selectedAntigravityAccount}
          onCreated={openAccount}
          readOnly={!canWrite}
        >
          {({ onSignIn: onAntigravitySignIn, onImport: onAntigravityImport, detail: antigravityDetail }) => (
            <OpenRouterAccountControls
              account={selectedOpenRouterAccount}
              onCreated={openAccount}
              readOnly={!canWrite}
            >
              {({ onAdd, detail }) => (
                <ModelSourceAccountControls
                  source={selectedModelSource}
                  onCreated={openAccount}
                  readOnly={!canWrite}
                >
                  {({ onAdd: onAddOpenAICompatible, detail: modelSourceDetail }) => (
                    <div className="animate-fade-in-up space-y-4">
                      {selectedId === null ? (
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                          <h1 className="text-xl font-semibold tracking-tight">{t("providers.page.title")}</h1>
                          {summaries.length > 0 ? (
                            <p className="text-sm text-muted-foreground" data-testid="providers-summary">
                              {t("providers.page.ready", { ready: readyCount, total: summaries.length })}
                              {attentionCount > 0 ? " · " + t("providers.page.attention", { count: attentionCount }) : null}
                              {pausedCount > 0 ? " · " + t("providers.page.paused", { count: pausedCount }) : null}
                            </p>
                          ) : null}
                          <div className="ml-auto flex items-center gap-2">
                            {canWrite ? (
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="gap-1 text-xs"
                                aria-expanded={helpOpen}
                                onClick={() => setHelpOpen((current) => !current)}
                              >
                                {t("accounts.list.needHelp")}
                                {helpOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                              </Button>
                            ) : null}
                            <Button type="button" size="sm" className="gap-1.5" disabled={!canWrite} onClick={() => setChooserOpen(true)}>
                              <Plus className="h-3.5 w-3.5" />
                              {t("accounts.list.addAccount")}
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex flex-wrap items-center gap-2 text-[12.5px] text-muted-foreground">
                          <Link to="/providers" className="hover:text-foreground">
                            {t("providers.page.title")}
                          </Link>
                          {selectedSummary ? (
                            <>
                              <span aria-hidden="true">/</span>
                              <span>{PROVIDER_LABELS[selectedSummary.kind]}</span>
                              <span aria-hidden="true" className="hidden lg:inline">/</span>
                              <span className="hidden truncate text-foreground lg:inline">{selectedSummary.name}</span>
                              <Select value={selectedSummary.id} onValueChange={openAccount}>
                                <SelectTrigger size="sm" className="h-7 max-w-56 min-w-0 text-xs lg:hidden" aria-label={t("providers.rail.switch")}>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  {groups.map((group) => (
                                    <SelectGroup key={group.kind}>
                                      <SelectLabel>{PROVIDER_LABELS[group.kind]}</SelectLabel>
                                      {group.summaries.map((summary) => (
                                        <SelectItem key={summary.id} value={summary.id}>
                                          {summary.name}
                                        </SelectItem>
                                      ))}
                                    </SelectGroup>
                                  ))}
                                </SelectContent>
                              </Select>
                            </>
                          ) : null}
                        </div>
                      )}

                      {mutationError ? (
                        <AlertMessage variant="error">{mutationError}</AlertMessage>
                      ) : null}
                      {openRouterQuery.error && (
                        <AlertMessage variant="error">
                          {openRouterQuery.error.message}
                        </AlertMessage>
                      )}
                      {claudeQuery.error && (
                        <AlertMessage variant="error">
                          {claudeQuery.error.message}
                        </AlertMessage>
                      )}
                      {antigravityQuery.error && (
                        <AlertMessage variant="error">
                          {antigravityQuery.error.message}
                        </AlertMessage>
                      )}
                      {modelSourcesQuery.error && (
                        <AlertMessage variant="error">
                          {modelSourcesQuery.error.message}
                        </AlertMessage>
                      )}
                      {helpOpen && canWrite && selectedId === null ? <WindowsOauthHelp /> : null}

                      {providersLoading ? (
                        <AccountsSkeleton />
                      ) : selectedId === null ? (
                        <ProvidersList
                          groups={groups}
                          activity={activity}
                          activityAvailable={activityAvailable}
                          colors={accountColors}
                          sortMode={accountSortMode}
                          onSortModeChange={setAccountSortMode}
                          showResetCreditBadges={showResetCreditBadges}
                          readOnly={!canWrite}
                          onAdd={() => setChooserOpen(true)}
                        />
                      ) : (
                        <div
                          data-testid="provider-detail-layout"
                          className={cn(
                            "grid min-w-0 grid-cols-1 items-start gap-4",
                            railCollapsed ? "lg:grid-cols-[3.5rem_minmax(0,1fr)]" : "lg:grid-cols-[18rem_minmax(0,1fr)]",
                          )}
                        >
                          <ProviderRail
                            groups={groups}
                            selectedId={selectedId}
                            colors={accountColors}
                            collapsed={railCollapsed}
                            onToggleCollapsed={toggleRail}
                          />
                          {selectedClaudeAccount ? (
                            claudeDetail
                          ) : selectedAntigravityAccount ? (
                            antigravityDetail
                          ) : selectedOpenRouterAccount ? (
                            detail
                          ) : selectedModelSource ? (
                            modelSourceDetail
                          ) : selectedAccount ? (
                            <AccountDetail
                              account={selectedAccount}
                              busy={mutationBusy}
                              readOnly={!canWrite}
                              onPause={(accountId) =>
                                void pauseMutation.mutateAsync(accountId)
                              }
                              onResume={(accountId) =>
                                void resumeMutation.mutateAsync(accountId)
                              }
                              onProbe={(accountId) =>
                                void probeMutation.mutateAsync({ accountId })
                              }
                              onResetUsage={(accountId) =>
                                usageResetDialog.show(accountId)
                              }
                              onSetAlias={(accountId, alias) =>
                                setAliasMutation.mutateAsync({ accountId, alias })
                              }
                              onDelete={(accountId) => deleteDialog.show(accountId)}
                              onReauth={() => {
                                setOauthAccountId(selectedAccount.accountId);
                                oauthDialog.show();
                              }}
                              onExportAuth={(accountId) => {
                                void exportAuthMutation
                                  .mutateAsync(accountId)
                                  .then((result) => exportDialog.show(result))
                                  .catch(() => null);
                              }}
                              onResetCredit={(accountId) => {
                                resetCreditDialog.show({
                                  accountId,
                                  availableResetCredits:
                                    selectedAccount.availableResetCredits ?? 0,
                                });
                              }}
                              showResetCreditExpiryBadge={showResetCreditExpiryBadge}
                              limitWarmupGloballyEnabled={limitWarmupGloballyEnabled}
                              onLimitWarmupChange={(accountId, enabled) =>
                                void limitWarmupMutation.mutateAsync({
                                  accountId,
                                  enabled,
                                })
                              }
                              onRoutingPolicyChange={(accountId, routingPolicy) =>
                                void routingPolicyMutation.mutateAsync({
                                  accountId,
                                  routingPolicy,
                                })
                              }
                              onCreditPolicyChange={(accountId, creditPolicy) =>
                                void creditPolicyMutation.mutateAsync({
                                  accountId,
                                  creditPolicy,
                                })
                              }
                              onSecurityWorkAuthorizedChange={(accountId, enabled) =>
                                void updateMutation.mutateAsync({
                                  accountId,
                                  securityWorkAuthorized: enabled,
                                })
                              }
                              upstreamProxyAdmin={
                                canReadUpstreamProxy
                                  ? (upstreamProxyQuery.data ?? null)
                                  : null
                              }
                              onProxyBindingSave={(accountId, payload) =>
                                accountBindingMutation.mutateAsync({
                                  accountId,
                                  payload,
                                })
                              }
                              onProxyEndpointTest={(endpointId) =>
                                testEndpointMutation.mutateAsync(endpointId)
                              }
                              resetCredits={
                                resetCreditsQuery.data?.rateLimitResetCredits ?? null
                              }
                              resetCreditsLoading={resetCreditsQuery.isFetching}
                              resetCreditsUnavailable={!!resetCreditsQuery.error}
                            />
                          ) : (
                            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed p-12 text-center" data-testid="provider-not-found">
                              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
                                <UserX className="h-5 w-5 text-muted-foreground" />
                              </div>
                              <p className="mt-3 text-sm font-medium text-muted-foreground">{t("providers.notFound.title")}</p>
                              <p className="mt-1 text-xs text-muted-foreground/70">{t("providers.notFound.description")}</p>
                              <Button asChild variant="outline" size="sm" className="mt-4">
                                <Link to="/providers">{t("providers.rail.all")}</Link>
                              </Button>
                            </div>
                          )}
                        </div>
                      )}

                      <AddAccountDialog
                        open={chooserOpen}
                        onOpenChange={setChooserOpen}
                        codex={{
                          onSignIn: () => {
                            setOauthAccountId(null);
                            oauthDialog.show();
                          },
                          onImport: () => importDialog.show(),
                        }}
                        claude={{ onSignIn: onClaudeSignIn, onImport: onClaudeImport }}
                        antigravity={{ onSignIn: onAntigravitySignIn, onImport: onAntigravityImport }}
                        onOpenRouter={onAdd}
                        onOpenAICompatible={onAddOpenAICompatible}
                      />

                      <ImportDialog
                        open={importDialog.open}
                        busy={importMutation.isPending}
                        error={getErrorMessageOrNull(importMutation.error)}
                        onOpenChange={importDialog.onOpenChange}
                        onImport={async (file) => {
                          await importMutation.mutateAsync(file);
                        }}
                      />

                      <Suspense fallback={null}>
                        <OauthDialog
                          open={oauthDialog.open}
                          state={oauth.state}
                          onOpenChange={(open) => {
                            oauthDialog.onOpenChange(open);
                            if (!open) {
                              setOauthAccountId(null);
                            }
                          }}
                          onStart={async (method) => {
                            await oauth.start(method, oauthAccountId ?? undefined);
                          }}
                          onComplete={async () => {
                            await accountsQuery.refetch();
                          }}
                          onManualCallback={async (callbackUrl) => {
                            await oauth.manualCallback(callbackUrl);
                          }}
                          onReset={oauth.reset}
                        />
                      </Suspense>

                      <AuthExportDialog
                        open={exportDialog.open}
                        exportData={exportDialog.data}
                        onOpenChange={exportDialog.onOpenChange}
                      />

                      {resetCreditDialog.data ? (
                        <ResetCreditConfirmDialog
                          open={resetCreditDialog.open}
                          accountId={resetCreditDialog.data.accountId}
                          summaryAvailableCount={
                            resetCreditDialog.data.availableResetCredits
                          }
                          onOpenChange={resetCreditDialog.onOpenChange}
                        />
                      ) : null}

                      <ConfirmDialog
                        open={deleteDialog.open}
                        title={t("accounts.deleteDialog.title")}
                        description={t("accounts.deleteDialog.description")}
                        confirmLabel={t("common.actions.delete")}
                        cancelLabel={t("common.cancel")}
                        onOpenChange={(open) => {
                          deleteDialog.onOpenChange(open);
                          if (!open) setDeleteHistory(false);
                        }}
                        onConfirm={() => {
                          if (!deleteDialog.data) {
                            return;
                          }
                          void deleteMutation
                            .mutateAsync({
                              accountId: deleteDialog.data,
                              deleteHistory,
                            })
                            .finally(() => {
                              deleteDialog.hide();
                              setDeleteHistory(false);
                            });
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <Checkbox
                            id="delete-history"
                            checked={deleteHistory}
                            onCheckedChange={(checked) =>
                              setDeleteHistory(checked === true)
                            }
                          />
                          <label
                            htmlFor="delete-history"
                            className="text-sm text-muted-foreground cursor-pointer"
                          >
                            {t("accounts.deleteDialog.deleteHistory")}
                          </label>
                        </div>
                      </ConfirmDialog>

                      <ConfirmDialog
                        open={usageResetDialog.open}
                        title={t("accounts.usageResetDialog.title")}
                        description={t("accounts.usageResetDialog.description")}
                        confirmLabel={t("common.actions.reset")}
                        cancelLabel={t("common.cancel")}
                        onOpenChange={usageResetDialog.onOpenChange}
                        onConfirm={() => {
                          if (!usageResetDialog.data) {
                            return;
                          }
                          void usageResetMutation
                            .mutateAsync({ accountId: usageResetDialog.data })
                            .finally(() => {
                              usageResetDialog.hide();
                            });
                        }}
                      />

                      <LoadingOverlay
                        visible={!!accountsQuery.data && mutationBusy}
                        label={t("accounts.page.updating")}
                      />
                    </div>
                  )}
                </ModelSourceAccountControls>
              )}
            </OpenRouterAccountControls>
          )}
        </AntigravityAccountControls>
      )}
    </ClaudeAccountControls>
  );
}
