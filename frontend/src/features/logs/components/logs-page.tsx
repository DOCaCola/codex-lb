import { useCallback, useEffect, useMemo } from "react";
import { Trans, useTranslation } from "react-i18next";
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
import { RequestFilters } from "@/features/dashboard/components/filters/request-filters";
import { RecentRequestsTable } from "@/features/dashboard/components/recent-requests-table";
import { formatCoveredCost } from "@/features/dashboard/cost-coverage";
import { useDashboard } from "@/features/dashboard/hooks/use-dashboard";
import { useConversations } from "@/features/dashboard/hooks/use-conversations";
import { useRequestLogTablePreferences } from "@/features/dashboard/hooks/use-request-log-table-preferences";
import { useRequestLogs } from "@/features/dashboard/hooks/use-request-logs";
import { REQUEST_LOG_COLUMN_OPTIONS } from "@/features/dashboard/request-log-columns";
import {
  parseConversationTimeframe,
  parseDashboardView,
  type ConversationTimeframe,
  type DashboardView,
} from "@/features/dashboard/schemas";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { REQUEST_STATUS_LABELS } from "@/utils/constants";
import { formatModelLabel, formatSlug } from "@/utils/formatters";

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
  const conversationTimeframe = useMemo(
    () => parseConversationTimeframe(searchParams.get("conversationTimeframe")),
    [searchParams],
  );
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
  // Arrivals are tracked on the first page of settled (non-placeholder) data.
  const liveRequestContext =
    !logsQuery.isPlaceholderData && filters.offset === 0 ? JSON.stringify(filters) : null;

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

  const blurred = usePrivacyStore((s) => s.blurred);

  const conversationSummary = useMemo(() => {
    const conv = logPage?.conversation;
    if (!conv || !filters.conversationId) {
      return null;
    }
    const cost = conv.costCoverage
      ? formatCoveredCost(conv.aggregatedCostUsd, conv.costCoverage)
      : "Unknown";
    const count = conv.requestCount;
    const suffixParts: string[] = [];

    if (filters.timeframe !== "all") {
      suffixParts.push(filters.timeframe);
    }
    if (filters.statuses.length > 0) {
      const labels = filters.statuses.map((s) =>
        t(`dashboard.requestStatus.${s}`, {
          defaultValue: REQUEST_STATUS_LABELS[s] ?? s,
        }),
      );
      suffixParts.push(labels.join(", "));
    }
    if (filters.modelOptions.length > 0) {
      const labels = filters.modelOptions.map((raw) => {
        const decoded = modelOptions.find((o) => o.value === raw);
        if (decoded) return decoded.label;
        // Decode from the filter value itself when options are stale/missing
        const [model, ...rest] = raw.split(MODEL_OPTION_DELIMITER);
        const effort = rest.join(MODEL_OPTION_DELIMITER);
        return formatModelLabel(model, effort || null);
      });
      suffixParts.push(labels.join(", "));
    }
    if (filters.accountIds.length > 0) {
      const labels = filters.accountIds.map((id) => {
        const opt = accountOptions.find((o) => o.value === id);
        if (!opt) return t("dashboard.filters.accounts"); // safe fallback: localized label
        const raw = opt.label;
        if (blurred && opt.isEmail) {
          return id.slice(0, 8);
        }
        return raw;
      });
      suffixParts.push(labels.join(", "));
    }
    if (filters.apiKeyIds.length > 0) {
      const labels = filters.apiKeyIds.map((id) => {
        const opt = apiKeyOptions.find((o) => o.value === id);
        return opt?.label ?? t("dashboard.filters.apiKeys"); // safe fallback
      });
      suffixParts.push(labels.join(", "));
    }
    if (filters.search) {
      suffixParts.push(`"${filters.search}"`);
    }

    const codeClass = "rounded bg-muted px-1 py-0.5 text-xs font-mono";

    if (suffixParts.length > 0) {
      return (
        <Trans
          i18nKey="dashboard.conversation.summaryWithFilters"
          values={{
            id: filters.conversationId,
            count,
            cost,
            filters: suffixParts.join(", "),
          }}
          components={[
            <code key="id" className={codeClass} />,
            <code key="count" className={codeClass} />,
            <code key="cost" className={codeClass} />,
          ]}
        />
      );
    }
    return (
      <Trans
        i18nKey="dashboard.conversation.summary"
        values={{ id: filters.conversationId, count, cost }}
        components={[
          <code key="id" className={codeClass} />,
          <code key="count" className={codeClass} />,
          <code key="cost" className={codeClass} />,
        ]}
      />
    );
  }, [
    logPage?.conversation,
    filters,
    t,
    accountOptions,
    apiKeyOptions,
    modelOptions,
    blurred,
  ]);

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

  return (
    <div className="animate-fade-in-up space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("logs.page.title")}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("logs.page.subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {logsView === "conversations" ? (
            <ConversationTimeframeSelect
              value={conversationTimeframe}
              onChange={handleConversationTimeframeChange}
            />
          ) : null}
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
        </div>
      </div>

      {errorMessage ? (
        <AlertMessage variant="error">{errorMessage}</AlertMessage>
      ) : null}

      <section className="space-y-4" data-testid="logs-section" data-view={logsView}>
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
          <div className="h-px min-w-8 flex-1 bg-border" />
          {logsView === "request-logs" ? (
            <>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button type="button" variant="outline" size="sm">
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
                aria-label={t("dashboard.requests.columnLayout.restoreDefault")}
                title={t("dashboard.requests.columnLayout.restoreDefault")}
                onClick={restoreDefaultLayout}
              >
                <RotateCcw className="h-4 w-4" />
              </Button>
            </>
          ) : null}
        </div>
        {logsView === "conversations" ? (
          <ConversationsView state={conversationsState} accounts={accounts} />
        ) : (
          <>
            {logsQuery.error ? (
              <div className="space-y-3 rounded-xl border bg-card p-4">
                <div role="alert">
                  <AlertMessage variant="error">
                    {logsQuery.error.message}
                  </AlertMessage>
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
            {logsQuery.isPending && !logPage ? (
              <div className="rounded-xl border bg-card py-8">
                <SpinnerBlock />
              </div>
            ) : logPage ? (
              <>
                <RequestFilters
                  filters={filters}
                  accountOptions={accountOptions}
                  apiKeyOptions={apiKeyOptions}
                  modelOptions={modelOptions}
                  statusOptions={statusOptions}
                  showApiKeyFilter={canReadApiKeys}
                  onSearchChange={(search) =>
                    updateFilters({ search, offset: 0 })
                  }
                  onTimeframeChange={(timeframe) =>
                    updateFilters({ timeframe, offset: 0 })
                  }
                  onAccountChange={(accountIds) =>
                    updateFilters({ accountIds, offset: 0 })
                  }
                  onApiKeyChange={(apiKeyIds) =>
                    updateFilters({ apiKeyIds, offset: 0 })
                  }
                  onModelChange={(modelOptionsSelected) =>
                    updateFilters({
                      modelOptions: modelOptionsSelected,
                      offset: 0,
                    })
                  }
                  onStatusChange={(statuses) =>
                    updateFilters({ statuses, offset: 0 })
                  }
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
                {conversationSummary ? (
                  <div className="rounded-xl border bg-card p-4">
                    <p className="text-sm text-muted-foreground">
                      {conversationSummary}
                    </p>
                  </div>
                ) : logPage.costCoverage ? (
                  <div className="rounded-xl border bg-card p-4 text-sm text-muted-foreground">
                    {formatCoveredCost(logPage.costCoverage.knownCostUsd, logPage.costCoverage)}
                  </div>
                ) : null}
                <div className="transition-opacity duration-200">
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
                    filtersApplied={emptyStateFiltersApplied}
                    liveContextKey={liveRequestContext}
                    onLimitChange={(limit) =>
                      updateFilters({ limit, offset: 0 })
                    }
                    onOffsetChange={(offset) => updateFilters({ offset })}
                    onConversationClick={handleConversationClick}
                  />
                </div>
              </>
            ) : null}
          </>
        )}
      </section>
    </div>
  );
}
