import { useCallback, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Columns3, List, MessagesSquare, RefreshCw, RotateCcw } from "lucide-react";

import { AlertMessage } from "@/components/alert-message";
import { ChartToggle } from "@/components/chart-toggle";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SpinnerBlock } from "@/components/ui/spinner";
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { useModels } from "@/features/api-keys/hooks/use-models";
import { useAuthStore, usePermission } from "@/features/auth/hooks/use-auth";
import { ConversationsView } from "@/features/dashboard/components/conversations-view";
import { ConversationTimeframeSelect } from "@/features/dashboard/components/filters/conversation-timeframe-select";
import { CompactPaginationControls } from "@/features/dashboard/components/filters/pagination-controls";
import { RequestFilters } from "@/features/dashboard/components/filters/request-filters";
import { TimeframeSelect } from "@/features/dashboard/components/filters/timeframe-select";
import { RecentRequestsTable } from "@/features/dashboard/components/recent-requests-table";
import { formatCoveredCost, formatCoveredCostShort } from "@/features/dashboard/cost-coverage";
import { useDashboard } from "@/features/dashboard/hooks/use-dashboard";
import { useConversations } from "@/features/dashboard/hooks/use-conversations";
import { useRequestLogTablePreferences } from "@/features/dashboard/hooks/use-request-log-table-preferences";
import { useRequestLogs } from "@/features/dashboard/hooks/use-request-logs";
import { REQUEST_LOG_COLUMN_OPTIONS } from "@/features/dashboard/request-log-columns";
import {
  parseDashboardView,
  type ConversationTimeframe,
  type DashboardView,
} from "@/features/dashboard/schemas";
import { REQUEST_STATUS_LABELS } from "@/utils/constants";
import { formatModelLabel, formatNumber, formatSlug } from "@/utils/formatters";

const MODEL_OPTION_DELIMITER = ":::";

export function LogsPage() {
  const { t } = useTranslation();
  const {
    visibleColumns,
    columnWidths,
    toggleColumn,
    setColumnWidth,
    restoreDefaultLayout,
  } = useRequestLogTablePreferences();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const accountColors = useAccountColorHexes();
  const modelsQuery = useModels();
  // Account names, plans and colours of the logged requests come from the
  // overview, which `dashboard:read` (this page's permission) already grants.
  const overviewQuery = useDashboard();
  const accounts = overviewQuery.data?.accounts ?? [];
  // Conversations and archives need `conversations:read`, the API-key filter `api_keys:read`.
  const canReadApiKeys = usePermission("api_keys:read");
  const initialized = useAuthStore((state) => state.initialized);
  const hasConversationsRead = usePermission("conversations:read");
  const canReadConversations = initialized && hasConversationsRead;
  const requestedView = useMemo(
    () => parseDashboardView(searchParams.get("view")),
    [searchParams],
  );
  const logsView = canReadConversations ? requestedView : "request-logs";
  useEffect(() => {
    if (
      !initialized ||
      canReadConversations ||
      searchParams.get("view") !== "conversations"
    ) {
      return;
    }
    const next = new URLSearchParams(searchParams);
    next.delete("view");
    setSearchParams(next, { replace: true });
  }, [initialized, canReadConversations, searchParams, setSearchParams]);
  const conversationsState = useConversations({
    enabled: canReadConversations && logsView === "conversations",
  });
  const { conversationsQuery } = conversationsState;
  // Read-only sessions never see the API-key filter control, so they must not
  // query with one either (URL-carried `apiKeyId` is dropped).
  const {
    filters,
    emptyStateFiltersApplied,
    logsQuery,
    optionsQuery,
    updateFilters,
  } = useRequestLogs({
    enabled: logsView === "request-logs",
    allowApiKeyFilters: canReadApiKeys,
  });

  const isRefreshing =
    logsView === "request-logs"
      ? logsQuery.isFetching
      : conversationsQuery.isFetching;

  const handleRefresh = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  }, [queryClient]);

  const handleConversationTimeframeChange = useCallback(
    (timeframe: ConversationTimeframe) => {
      conversationsState.updateFilters({ timeframe, offset: 0 });
    },
    [conversationsState],
  );

  const handleViewChange = useCallback(
    (nextView: DashboardView) => {
      const next = new URLSearchParams(searchParams);
      if (nextView === "request-logs") {
        next.delete("view");
      } else {
        next.set("view", nextView);
      }
      setSearchParams(next);
    },
    [searchParams, setSearchParams],
  );

  const handleConversationClick = useCallback(
    (conversationId: string) => {
      updateFilters({ conversationId, offset: 0 });
    },
    [updateFilters],
  );

  const handleConversationDismiss = useCallback(() => {
    updateFilters({ conversationId: null, offset: 0 });
  }, [updateFilters]);

  const logPage = logsQuery.data;
  const conversationPage = conversationsQuery.data;
  const requestQueryKey = JSON.stringify(filters);
  // Arrivals are tracked on the first page of settled (non-placeholder) data.
  const liveRequestContext =
    !logsQuery.isPlaceholderData && filters.offset === 0 ? requestQueryKey : null;

  const accountOptions = useMemo(() => {
    const entries = new Map<string, { label: string; isEmail: boolean }>();
    for (const account of overviewQuery.data?.accounts ?? []) {
      const raw = account.displayName || account.email || account.accountId;
      const isEmail = !!account.email && raw === account.email;
      entries.set(account.accountId, { label: raw, isEmail });
    }
    return (optionsQuery.data?.accountIds ?? []).map((accountId) => {
      const providerName = optionsQuery.data?.accountLabels?.[accountId];
      const entry = entries.get(accountId);
      return {
        value: accountId,
        label: providerName ?? entry?.label ?? accountId,
        isEmail: providerName ? true : entry?.isEmail ?? false,
      };
    });
  }, [optionsQuery.data?.accountIds, optionsQuery.data?.accountLabels, overviewQuery.data?.accounts]);

  const apiKeyOptions = useMemo(
    () =>
      (optionsQuery.data?.apiKeys ?? []).map((option) => ({
        value: option.id,
        label: option.keyPrefix
          ? `${option.name} · ${option.keyPrefix}`
          : option.name,
      })),
    [optionsQuery.data?.apiKeys],
  );

  const modelOptions = useMemo(
    () =>
      (optionsQuery.data?.modelOptions ?? []).map((option) => ({
        value: `${option.model}${MODEL_OPTION_DELIMITER}${option.reasoningEffort ?? ""}`,
        label: formatModelLabel(option.model, option.reasoningEffort),
      })),
    [optionsQuery.data?.modelOptions],
  );

  const statusOptions = useMemo(
    () =>
      (optionsQuery.data?.statuses ?? []).map((status) => ({
        value: status,
        label: t(`dashboard.requestStatus.${status}`, {
          defaultValue: REQUEST_STATUS_LABELS[status] ?? formatSlug(status),
        }),
      })),
    [optionsQuery.data?.statuses, t],
  );

  const errorMessage =
    overviewQuery.error?.message ||
    (logsView === "request-logs" && optionsQuery.error?.message) ||
    null;

  // Like the pane footers, the toolbar pager appears once there is something to page.
  const pager =
    logsView === "request-logs"
      ? logPage && (logPage.requests.length > 0 || filters.offset > 0)
        ? {
            total: logPage.total,
            limit: filters.limit,
            offset: filters.offset,
            hasMore: logPage.hasMore,
            onOffsetChange: (offset: number) => updateFilters({ offset }),
          }
        : null
      : conversationPage &&
          (conversationPage.conversations.length > 0 || conversationsState.filters.offset > 0)
        ? {
            total: conversationPage.total,
            limit: conversationsState.filters.limit,
            offset: conversationsState.filters.offset,
            hasMore: conversationPage.hasMore,
            onOffsetChange: (offset: number) => conversationsState.updateFilters({ offset }),
          }
        : null;

  const costCoverage = logPage?.costCoverage;
  const summary =
    logsView === "request-logs" ? (
      logPage ? (
        <span
          title={costCoverage ? formatCoveredCost(costCoverage.knownCostUsd, costCoverage) : undefined}
        >
          {t("logs.toolbar.requests", { count: logPage.total, formatted: formatNumber(logPage.total) })}
          {costCoverage ? (
            <>
              {" · "}
              <span className="font-mono text-foreground">
                {formatCoveredCostShort(costCoverage.knownCostUsd, costCoverage)}
              </span>
            </>
          ) : null}
        </span>
      ) : null
    ) : conversationPage ? (
      <span>
        {t("logs.toolbar.conversations", {
          count: conversationPage.total,
          formatted: formatNumber(conversationPage.total),
        })}
      </span>
    ) : null;

  const columnControls = (
    <>
      <span className="mx-1 h-5 w-px bg-border" aria-hidden="true" />
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button type="button" variant="outline" size="sm" className="h-8">
            <Columns3 className="mr-2 h-4 w-4" />
            {t("dashboard.requests.columnLayout.columns", {
              count: visibleColumns.length,
            })}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-52">
          <DropdownMenuLabel>
            {t("dashboard.requests.columnLayout.visibleColumns")}
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {REQUEST_LOG_COLUMN_OPTIONS.map((column) => {
            const isVisible = visibleColumns.includes(column.id);
            return (
              <DropdownMenuCheckboxItem
                key={column.id}
                checked={isVisible}
                disabled={isVisible && visibleColumns.length === 1}
                onCheckedChange={() => toggleColumn(column.id)}
                onSelect={(event) => event.preventDefault()}
              >
                {t(column.translationKey)}
              </DropdownMenuCheckboxItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-8 w-8"
        aria-label={t("dashboard.requests.columnLayout.restoreDefault")}
        title={t("dashboard.requests.columnLayout.restoreDefault")}
        onClick={restoreDefaultLayout}
      >
        <RotateCcw className="h-4 w-4" />
      </Button>
    </>
  );

  return (
    <div
      className="animate-fade-in-up flex h-[calc(100dvh-10rem)] min-h-[32rem] flex-col gap-4"
      data-testid="logs-section"
      data-view={logsView}
    >
      {errorMessage ? (
        <div className="shrink-0">
          <AlertMessage variant="error">{errorMessage}</AlertMessage>
        </div>
      ) : null}

      <section
        className="shrink-0 space-y-3 rounded-xl border bg-card p-3"
        aria-label={t("logs.page.controls")}
      >
        <div className="flex flex-wrap items-center gap-3">
          {canReadConversations ? (
            <ChartToggle
              label={t("logs.page.view")}
              value={logsView}
              onChange={handleViewChange}
              options={[
                {
                  value: "request-logs",
                  label: t("dashboard.views.request-logs"),
                  icon: <List className="h-3.5 w-3.5" aria-hidden="true" />,
                },
                {
                  value: "conversations",
                  label: t("dashboard.views.conversations"),
                  icon: <MessagesSquare className="h-3.5 w-3.5" aria-hidden="true" />,
                },
              ]}
            />
          ) : (
            <h2 className="text-[13px] font-medium uppercase tracking-wider text-muted-foreground">
              {t("dashboard.views.request-logs")}
            </h2>
          )}
          <span className="h-5 w-px bg-border" aria-hidden="true" />
          {logsView === "conversations" ? (
            <ConversationTimeframeSelect
              value={conversationsState.filters.timeframe}
              onChange={handleConversationTimeframeChange}
            />
          ) : (
            <TimeframeSelect
              value={filters.timeframe}
              onChange={(timeframe) => updateFilters({ timeframe, offset: 0 })}
            />
          )}
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
            aria-label={t("logs.page.refresh")}
            title={t("logs.page.refresh")}
          >
            <RefreshCw
              className={`h-4 w-4${isRefreshing ? " animate-spin" : ""}`}
              aria-hidden="true"
            />
          </button>
          <span className="flex-1" />
          {summary ? (
            <span className="text-xs tabular-nums text-muted-foreground" data-testid="logs-summary">
              {summary}
            </span>
          ) : null}
          {pager ? (
            <>
              <span className="h-5 w-px bg-border" aria-hidden="true" />
              <CompactPaginationControls {...pager} />
            </>
          ) : null}
        </div>
        {logsView === "request-logs" ? (
          <RequestFilters
            filters={filters}
            accountOptions={accountOptions}
            apiKeyOptions={apiKeyOptions}
            modelOptions={modelOptions}
            statusOptions={statusOptions}
            showApiKeyFilter={canReadApiKeys}
            trailing={columnControls}
            onSearchChange={(search) => updateFilters({ search, offset: 0 })}
            onAccountChange={(accountIds) => updateFilters({ accountIds, offset: 0 })}
            onApiKeyChange={(apiKeyIds) => updateFilters({ apiKeyIds, offset: 0 })}
            onModelChange={(modelOptionsSelected) =>
              updateFilters({ modelOptions: modelOptionsSelected, offset: 0 })
            }
            onStatusChange={(statuses) => updateFilters({ statuses, offset: 0 })}
            onConversationDismiss={handleConversationDismiss}
            onReset={() =>
              updateFilters({
                search: "",
                timeframe: "all",
                accountIds: [],
                apiKeyIds: [],
                modelOptions: [],
                statuses: [],
                conversationId: null,
                offset: 0,
              })
            }
          />
        ) : null}
      </section>

      {logsView === "conversations" ? (
        <ConversationsView state={conversationsState} accounts={accounts} />
      ) : (
        <>
          {logsQuery.error ? (
            <div className="shrink-0 space-y-3 rounded-xl border bg-card p-4">
              <div role="alert">
                <AlertMessage variant="error">{logsQuery.error.message}</AlertMessage>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  void logsQuery.refetch();
                }}
                disabled={logsQuery.isFetching}
              >
                {t("common.actions.retry")}
              </Button>
            </div>
          ) : null}
          {logPage ? (
            <RecentRequestsTable
              requests={logPage.requests}
              models={modelsQuery.data}
              accounts={accounts}
              accountColors={accountColors}
              total={logPage.total}
              visibleColumns={visibleColumns}
              columnWidths={columnWidths}
              onColumnWidthChange={setColumnWidth}
              limit={filters.limit}
              offset={filters.offset}
              hasMore={logPage.hasMore}
              scrollKey={requestQueryKey}
              filtersApplied={emptyStateFiltersApplied}
              liveContextKey={liveRequestContext}
              onLimitChange={(limit) => updateFilters({ limit, offset: 0 })}
              onOffsetChange={(offset) => updateFilters({ offset })}
              onConversationClick={handleConversationClick}
            />
          ) : logsQuery.isPending ? (
            <div className="flex flex-1 items-center justify-center rounded-xl border bg-card py-8">
              <SpinnerBlock />
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
