import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";

import { AlertMessage } from "@/components/alert-message";
import { ChartToggle } from "@/components/chart-toggle";
import { Button } from "@/components/ui/button";
import { useDialogState } from "@/hooks/use-dialog-state";
import { useAccountMutations } from "@/features/accounts/hooks/use-accounts";
import { useProviderActivity } from "@/features/accounts/hooks/use-provider-activity";
import { useSummaryContext } from "@/features/accounts/hooks/use-summary-context";
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { summarizeSources, type ProviderSummary } from "@/features/accounts/provider-summary";
import { ResetCreditConfirmDialog } from "@/features/accounts/components/reset-credit-confirm-dialog";
import { listApiKeys } from "@/features/api-keys/api";
import { useKeyColors } from "@/features/apis/key-summary";
import { useOpenRouter, useOpenRouterAccounts } from "@/features/openrouter/use-openrouter";
import { useClaude, useClaudeAccounts } from "@/features/claude/use-claude";
import { useAntigravity, useAntigravityAccounts } from "@/features/antigravity/use-antigravity";
import { ActivityStrip } from "@/features/dashboard/components/activity-strip";
import { AccountViewModeToggle } from "@/features/dashboard/components/account-view-mode-toggle";
import {
  DashboardAccountCards,
  DashboardAccountList,
  type DashboardAccountActions,
} from "@/features/dashboard/components/dashboard-accounts";
import { DashboardSkeleton } from "@/features/dashboard/components/dashboard-skeleton";
import { DashboardStatusLine } from "@/features/dashboard/components/dashboard-status-line";
import { QuotaSection } from "@/features/dashboard/components/quota-section";
import { usePermission } from "@/features/auth/hooks/use-auth";
import {
  useDashboard,
  useDashboardProjections,
} from "@/features/dashboard/hooks/use-dashboard";
import { buildDashboardView } from "@/features/dashboard/utils";
import {
  DEFAULT_OVERVIEW_TIMEFRAME,
  OVERVIEW_TIMEFRAMES,
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

type ResetCreditDialogTarget = {
  accountId: string;
  availableResetCredits: number;
};

function SectionHeader({ title, hint, children }: { title: string; hint?: string; children?: React.ReactNode }) {
  return (
    <div className="flex min-h-[30px] flex-wrap items-center gap-2.5">
      <h2 className="text-sm font-semibold">{title}</h2>
      {hint ? <span className="text-xs text-muted-foreground">{hint}</span> : null}
      <span className="flex-1" />
      {children}
    </div>
  );
}

export function DashboardPage() {
  const { t, i18n } = useTranslation();
  const resolvedLanguage = i18n.resolvedLanguage;
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const accountColors = useAccountColorHexes();
  const summaryContext = useSummaryContext();
  const { activity, available: activityAvailable } = useProviderActivity();
  const showAccountBurnrate = useDashboardPreferencesStore(
    (s) => s.accountBurnrateEnabled,
  );
  const accountViewMode = useDashboardPreferencesStore(
    (s) => s.accountViewMode,
  );
  const setAccountViewMode = useDashboardPreferencesStore(
    (s) => s.setAccountViewMode,
  );
  // Account actions follow the permission their backend route demands
  // (`accounts:write`), not the coarse `write` alias.
  const canWriteAccounts = usePermission("accounts:write");
  const canReadApiKeys = usePermission("api_keys:read");
  const apiKeysQuery = useQuery({
    queryKey: ["api-keys", "list"],
    queryFn: listApiKeys,
    enabled: canReadApiKeys,
  });
  const keyColors = useKeyColors(apiKeysQuery.data ?? []);
  const openRouterQuery = useOpenRouterAccounts();
  const claudeQuery = useClaudeAccounts();
  const antigravityQuery = useAntigravityAccounts();
  const claudeAccounts = useMemo(() => claudeQuery.data?.accounts ?? [], [claudeQuery.data]);
  const antigravityAccounts = useMemo(() => antigravityQuery.data?.accounts ?? [], [antigravityQuery.data]);
  const openRouterAccounts = useMemo(() => openRouterQuery.data?.accounts ?? [], [openRouterQuery.data]);
  const claude = useClaude();
  const antigravity = useAntigravity();
  const openRouter = useOpenRouter();
  const overviewTimeframe = useMemo(
    () => parseOverviewTimeframe(searchParams.get("overviewTimeframe")),
    [searchParams],
  );
  const dashboardQuery = useDashboard(overviewTimeframe);
  const [retainedDashboardLoadError, setRetainedDashboardLoadError] =
    useState<RetainedDashboardLoadError | null>(null);
  const [overviewRetryTimeframe, setOverviewRetryTimeframe] =
    useState<OverviewTimeframe | null>(null);
  const projectionsQuery = useDashboardProjections(
    Boolean(dashboardQuery.data),
  );
  const { resumeMutation } = useAccountMutations();
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

  const overview = dashboardQuery.data;
  const codexAccounts = useMemo(() => overview?.accounts ?? [], [overview]);

  const summaries = useMemo(
    () =>
      summarizeSources(
        { accounts: codexAccounts, claudeAccounts, antigravityAccounts, openRouterAccounts, modelSources: [] },
        { ...summaryContext, quotaDisplay: "both" },
      ),
    [codexAccounts, claudeAccounts, antigravityAccounts, openRouterAccounts, summaryContext],
  );
  const summariesById = useMemo(
    () => new Map(summaries.map((summary) => [summary.id, summary])),
    [summaries],
  );

  const actions = useMemo<DashboardAccountActions>(
    () => ({
      readOnly: !canWriteAccounts,
      onResume: (summary: ProviderSummary) => {
        const body = { isEnabled: true };
        switch (summary.entry.kind) {
          case "codex":
            void resumeMutation.mutateAsync(summary.id);
            break;
          case "claude":
            claude.update.mutate({ id: summary.id, body });
            break;
          case "antigravity":
            antigravity.update.mutate({ id: summary.id, body });
            break;
          case "openrouter":
            openRouter.update.mutate({ id: summary.id, body });
            break;
        }
      },
      onResetCredit: (account: AccountSummary) =>
        resetCreditDialog.show({
          accountId: account.accountId,
          availableResetCredits: account.availableResetCredits ?? 0,
        }),
    }),
    [antigravity.update, canWriteAccounts, claude.update, openRouter.update, resetCreditDialog, resumeMutation],
  );

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
    (overview || retainedDashboardLoadError.timeframe !== overviewTimeframe)
  ) {
    setRetainedDashboardLoadError(null);
  } else if (
    !overview &&
    dashboardLoadError !== null &&
    (retainedDashboardLoadError === null ||
      retainedDashboardLoadError.message !== dashboardLoadError)
  ) {
    setRetainedDashboardLoadError({
      timeframe: overviewTimeframe,
      message: dashboardLoadError,
    });
  }
  const displayedDashboardLoadError =
    dashboardLoadError ??
    (retainedDashboardLoadError?.timeframe === overviewTimeframe
      ? retainedDashboardLoadError.message
      : null);
  const overviewRetryBusy =
    dashboardQuery.isFetching || overviewRetryTimeframe === overviewTimeframe;
  const errorMessage = overview ? dashboardLoadError : null;

  const accountsHint = [
    t("dashboard.accounts.hint.total", { count: summaries.length }),
    t("dashboard.accounts.hint.ready", { count: summaries.filter((s) => s.status === "active").length }),
    ...[
      ["limited", summaries.filter((s) => s.status === "limited" || s.status === "exceeded").length],
      ["paused", summaries.filter((s) => s.status === "paused").length],
      ["signIn", summaries.filter((s) => s.status === "reauth" || s.status === "deactivated").length],
    ]
      .filter(([, count]) => (count as number) > 0)
      .map(([key, count]) => t("dashboard.accounts.hint." + key, { count })),
  ].join(" · ");

  const providerErrors = [claudeQuery.error, antigravityQuery.error, openRouterQuery.error].filter(
    (error): error is Error => error !== null,
  );
  const providersLoading = claudeQuery.isLoading || antigravityQuery.isLoading || openRouterQuery.isLoading;

  return (
    <div className="animate-fade-in-up space-y-7">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <h1 className="text-lg font-semibold tracking-tight">
          {t("dashboard.page.title")}
        </h1>
        <div className="min-w-0 flex-1">
          {view ? <DashboardStatusLine summaries={summaries} /> : null}
        </div>
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
              const retryTimeframe = overviewTimeframe;
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
            codexAccounts={codexAccounts}
            primaryCapacityCredits={
              overview?.summary.primaryWindow.capacityCredits ?? 0
            }
            secondaryCapacityCredits={
              overview?.summary.secondaryWindow?.capacityCredits ?? 0
            }
            claudeAccounts={claudeAccounts}
            antigravityAccounts={antigravityAccounts}
            summaries={summariesById}
            modelSourceColors={accountColors.modelSources}
            keyColors={keyColors}
          />

          <section className="flex flex-col gap-2.5" data-testid="accounts-section">
            <SectionHeader title={t("accounts.page.title")} hint={accountsHint}>
              <AccountViewModeToggle
                value={accountViewMode}
                onChange={setAccountViewMode}
              />
            </SectionHeader>
            {accountViewMode === "list" ? (
              <DashboardAccountList
                summaries={summaries}
                colors={accountColors}
                activity={activity}
                activityAvailable={activityAvailable}
                actions={actions}
              />
            ) : (
              <DashboardAccountCards
                summaries={summaries}
                colors={accountColors}
                activity={activity}
                activityAvailable={activityAvailable}
                actions={actions}
              />
            )}
            {providersLoading ? (
              <p className="text-sm text-muted-foreground">
                {t("dashboard.accounts.loadingProviders")}
              </p>
            ) : null}
            {providerErrors.map((error) => (
              <p key={error.message} role="alert" className="text-sm text-destructive">
                {error.message}
              </p>
            ))}
          </section>

          <section className="flex flex-col gap-2.5" data-testid="activity-section">
            <SectionHeader title={t("dashboard.activity.title")}>
              <ChartToggle<OverviewTimeframe>
                label={t("dashboard.filters.overviewTimeframe")}
                value={overviewTimeframe}
                onChange={handleOverviewTimeframeChange}
                options={OVERVIEW_TIMEFRAMES.map((value) => ({ value, label: value }))}
              />
            </SectionHeader>
            <ActivityStrip stats={view.stats} />
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
