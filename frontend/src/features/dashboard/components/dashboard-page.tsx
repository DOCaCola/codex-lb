import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";

import { AlertMessage } from "@/components/alert-message";
import { Button } from "@/components/ui/button";
import { useDialogState } from "@/hooks/use-dialog-state";
import { useAccountMutations } from "@/features/accounts/hooks/use-accounts";
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { ResetCreditConfirmDialog } from "@/features/accounts/components/reset-credit-confirm-dialog";
import { AccountCards } from "@/features/dashboard/components/account-cards";
import { useOpenRouterAccounts } from "@/features/openrouter/use-openrouter";
import { useClaudeAccounts } from "@/features/claude/use-claude";
import { AccountList } from "@/features/dashboard/components/account-list";
import { AccountSummaryLine } from "@/features/dashboard/components/account-summary-line";
import { AccountViewModeToggle } from "@/features/dashboard/components/account-view-mode-toggle";
import { DashboardSkeleton } from "@/features/dashboard/components/dashboard-skeleton";
import { OverviewTimeframeSelect } from "@/features/dashboard/components/filters/overview-timeframe-select";
import { StatsGrid } from "@/features/dashboard/components/stats-grid";
import { QuotaSection } from "@/features/dashboard/components/quota-section";
import { usePermission } from "@/features/auth/hooks/use-auth";
import {
  useDashboard,
  useDashboardProjections,
} from "@/features/dashboard/hooks/use-dashboard";
import { buildDashboardView } from "@/features/dashboard/utils";
import {
  DEFAULT_OVERVIEW_TIMEFRAME,
  parseOverviewTimeframe,
  type AccountSummary,
  type OverviewTimeframe,
} from "@/features/dashboard/schemas";
import { useDashboardPreferencesStore } from "@/hooks/use-dashboard-preferences";
import { getErrorMessageOrNull } from "@/utils/errors";

type RetainedDashboardLoadError = {
  timeframe: OverviewTimeframe;
  message: string;
};

export function DashboardPage() {
  const { t, i18n } = useTranslation();
  const resolvedLanguage = i18n.resolvedLanguage;
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const accountColors = useAccountColorHexes();
  const showAccountBurnrate = useDashboardPreferencesStore(
    (s) => s.accountBurnrateEnabled,
  );
  const accountViewMode = useDashboardPreferencesStore(
    (s) => s.accountViewMode,
  );
  const accountListSort = useDashboardPreferencesStore(
    (s) => s.accountListSort,
  );
  const setAccountViewMode = useDashboardPreferencesStore(
    (s) => s.setAccountViewMode,
  );
  const setAccountListSort = useDashboardPreferencesStore(
    (s) => s.setAccountListSort,
  );
  // Account actions follow the permission their backend route demands
  // (`accounts:write`), not the coarse `write` alias.
  const canWriteAccounts = usePermission("accounts:write");
  const openRouterQuery = useOpenRouterAccounts();
  const claudeQuery = useClaudeAccounts();
  const claudeAccounts = claudeQuery.data?.accounts ?? [];
  const openRouterAccounts = openRouterQuery.data?.accounts ?? [];
  const overviewTimeframe = useMemo(
    () => parseOverviewTimeframe(searchParams.get("overviewTimeframe")),
    [searchParams],
  );
  const dashboardTimeframe = overviewTimeframe;
  const dashboardQuery = useDashboard(dashboardTimeframe);
  const [retainedDashboardLoadError, setRetainedDashboardLoadError] =
    useState<RetainedDashboardLoadError | null>(null);
  const [overviewRetryTimeframe, setOverviewRetryTimeframe] =
    useState<OverviewTimeframe | null>(null);
  const projectionsQuery = useDashboardProjections(
    Boolean(dashboardQuery.data),
  );
  const { resumeMutation, limitWarmupMutation } = useAccountMutations();
  type ResetCreditDialogTarget = {
    accountId: string;
    availableResetCredits: number;
  };
  const resetCreditDialog = useDialogState<ResetCreditDialogTarget>();

  const isRefreshing =
    dashboardQuery.isFetching || projectionsQuery.isFetching;

  const handleRefresh = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  }, [queryClient]);

  const handleOverviewTimeframeChange = useCallback(
    (timeframe: OverviewTimeframe) => {
      const next = new URLSearchParams(searchParams);
      if (timeframe === DEFAULT_OVERVIEW_TIMEFRAME) {
        next.delete("overviewTimeframe");
      } else {
        next.set("overviewTimeframe", timeframe);
      }
      setSearchParams(next);
    },
    [searchParams, setSearchParams],
  );

  const handleAccountAction = useCallback(
    (account: AccountSummary, action: string) => {
      switch (action) {
        case "details":
          navigate(`/accounts?selected=${account.accountId}`);
          break;
        case "resume":
          if (canWriteAccounts) {
            void resumeMutation.mutateAsync(account.accountId);
          }
          break;
        case "reauth":
          navigate(`/accounts?selected=${account.accountId}`);
          break;
        case "warmup-toggle":
          if (canWriteAccounts) {
            void limitWarmupMutation.mutateAsync({
              accountId: account.accountId,
              enabled: !account.limitWarmupEnabled,
            });
          }
          break;
        case "reset-credit":
          resetCreditDialog.show({
            accountId: account.accountId,
            availableResetCredits: account.availableResetCredits ?? 0,
          });
          break;
      }
    },
    [
      canWriteAccounts,
      limitWarmupMutation,
      navigate,
      resetCreditDialog,
      resumeMutation,
    ],
  );

  const overview = dashboardQuery.data;

  const view = useMemo(() => {
    void resolvedLanguage;
    if (!overview) {
      return null;
    }
    return buildDashboardView(
      overview,
      {
        accountColors: accountColors.accounts,
        showAccountBurnrate,
      },
      projectionsQuery.data,
    );
  }, [
    overview,
    accountColors,
    showAccountBurnrate,
    projectionsQuery.data,
    resolvedLanguage,
  ]);

  const dashboardLoadError = getErrorMessageOrNull(dashboardQuery.error);
  if (
    retainedDashboardLoadError !== null &&
    (overview || retainedDashboardLoadError.timeframe !== dashboardTimeframe)
  ) {
    setRetainedDashboardLoadError(null);
  } else if (
    !overview &&
    dashboardLoadError !== null &&
    (retainedDashboardLoadError === null ||
      retainedDashboardLoadError.message !== dashboardLoadError)
  ) {
    setRetainedDashboardLoadError({
      timeframe: dashboardTimeframe,
      message: dashboardLoadError,
    });
  }
  const displayedDashboardLoadError =
    dashboardLoadError ??
    (retainedDashboardLoadError?.timeframe === dashboardTimeframe
      ? retainedDashboardLoadError.message
      : null);
  const overviewRetryBusy =
    dashboardQuery.isFetching || overviewRetryTimeframe === dashboardTimeframe;
  const errorMessage = overview ? dashboardLoadError : null;

  return (
    <div className="animate-fade-in-up space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("dashboard.page.title")}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("dashboard.page.subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <OverviewTimeframeSelect
            value={overviewTimeframe}
            onChange={handleOverviewTimeframeChange}
          />
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
            aria-label={t("dashboard.page.refresh")}
            title={t("dashboard.page.refresh")}
          >
            <RefreshCw
              className={`h-4 w-4${isRefreshing ? " animate-spin" : ""}`}
              aria-hidden="true"
            />
          </button>
        </div>
      </div>

      {errorMessage ? (
        <AlertMessage variant="error">{errorMessage}</AlertMessage>
      ) : null}

      {(dashboardQuery.isPending || dashboardQuery.isFetching) &&
      !view &&
      displayedDashboardLoadError === null ? (
        <DashboardSkeleton />
      ) : !view ? (
        <div className="space-y-3 rounded-xl border bg-card p-4">
          <div role="alert">
            <AlertMessage variant="error">
              {displayedDashboardLoadError ?? "Request failed"}
            </AlertMessage>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            aria-busy={overviewRetryBusy}
            disabled={overviewRetryBusy}
            onClick={() => {
              const retryTimeframe = dashboardTimeframe;
              setRetainedDashboardLoadError({
                timeframe: retryTimeframe,
                message: displayedDashboardLoadError ?? "Request failed",
              });
              setOverviewRetryTimeframe(retryTimeframe);
              void dashboardQuery.refetch().finally(() => {
                setOverviewRetryTimeframe((current) =>
                  current === retryTimeframe ? null : current,
                );
              });
            }}
          >
            {t("common.actions.retry")}
          </Button>
        </div>
      ) : (
        <>
          <QuotaSection
            view={view}
            primaryCapacityCredits={
              overview?.summary.primaryWindow.capacityCredits ?? 0
            }
            secondaryCapacityCredits={
              overview?.summary.secondaryWindow?.capacityCredits ?? 0
            }
            claudeAccounts={claudeAccounts}
            claudeAccountColors={accountColors.modelSources}
          />

          <section className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex min-w-0 flex-wrap items-center gap-3">
                <h2 className="text-[13px] font-medium uppercase tracking-wider text-muted-foreground">
                  {t("accounts.page.title")}
                </h2>
                <AccountSummaryLine
                  accounts={overview?.accounts ?? []}
                  openRouterAccounts={openRouterAccounts}
                  claudeAccounts={claudeAccounts}
                />
              </div>
              <div className="h-px min-w-8 flex-1 bg-border" />
              <AccountViewModeToggle
                value={accountViewMode}
                onChange={setAccountViewMode}
              />
            </div>
            {accountViewMode === "list" ? (
              <AccountList
                accounts={overview?.accounts ?? []}
                openRouterAccounts={openRouterAccounts}
                claudeAccounts={claudeAccounts}
                accountColors={accountColors}
                readOnly={!canWriteAccounts}
                sort={accountListSort}
                onSortChange={setAccountListSort}
                onAction={handleAccountAction}
              />
            ) : (
              <AccountCards
                accounts={overview?.accounts ?? []}
                openRouterAccounts={openRouterAccounts}
                claudeAccounts={claudeAccounts}
                accountColors={accountColors}
                readOnly={!canWriteAccounts}
                onAction={handleAccountAction}
              />
            )}
            {openRouterQuery.isLoading && (
              <p className="text-sm text-muted-foreground">
                Loading OpenRouter accounts…
              </p>
            )}
            {claudeQuery.isLoading && (
              <p className="text-sm text-muted-foreground">
                Loading Claude accounts…
              </p>
            )}
            {claudeQuery.error && (
              <p role="alert" className="text-sm text-destructive">
                {claudeQuery.error.message}
              </p>
            )}
            {openRouterQuery.error && (
              <p role="alert" className="text-sm text-destructive">
                {openRouterQuery.error.message}
              </p>
            )}
          </section>

          <section className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-[13px] font-medium uppercase tracking-wider text-muted-foreground">
                {t("dashboard.activity.title")}
              </h2>
              <div className="h-px min-w-8 flex-1 bg-border" />
            </div>
            <StatsGrid stats={view.stats} />
          </section>

        </>
      )}

      {resetCreditDialog.data ? (
        <ResetCreditConfirmDialog
          open={resetCreditDialog.open}
          accountId={resetCreditDialog.data.accountId}
          summaryAvailableCount={resetCreditDialog.data.availableResetCredits}
          onOpenChange={resetCreditDialog.onOpenChange}
        />
      ) : null}
    </div>
  );
}
