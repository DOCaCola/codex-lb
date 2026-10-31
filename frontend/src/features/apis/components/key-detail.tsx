import {
  CalendarClock,
  CalendarX,
  Clock,
  Copy,
  KeyRound,
  LayoutDashboard,
  PauseCircle,
  Pause,
  Play,
  RefreshCw,
  ScrollText,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import { Fragment, lazy, Suspense, useMemo, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { ProviderLogo } from "@/components/brand/provider-account-name";
import { ChartToggle } from "@/components/chart-toggle";
import { MiniQuotaBar } from "@/components/mini-quota-bar";
import { Button } from "@/components/ui/button";
import { accountColorPalette } from "@/features/accounts/account-colors";
import {
  DetailBanner,
  DetailCard,
  DetailMenu,
  DetailParts,
  DetailRows,
  type DetailMenuItem,
} from "@/features/accounts/components/provider-detail";
import { ApiKeySettingsForm } from "@/features/api-keys/components/api-key-settings-form";
import { USAGE_SECTIONS, type ApiKey, type ApiKeyUpdateRequest } from "@/features/api-keys/schemas";
import type { ApiTrendChartProps } from "@/features/apis/components/api-trend-chart";
import { KeyStateBadge, LimitTrack } from "@/features/apis/components/key-parts";
import {
  blockingLimit,
  formatLastUsed,
  formatLimitAmount,
  keyHref,
  keyState,
  keyStateDetail,
  limitName,
  limitPercent,
  useKeyTab,
  type KeyTab,
} from "@/features/apis/key-summary";
import type { ApiKeyTrendPoint, ApiKeyTrendsResponse, ApiKeyUsage7DayResponse } from "@/features/apis/schemas";
import { formatCoveredCostShort } from "@/features/dashboard/cost-coverage";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { useThemeStore } from "@/hooks/use-theme";
import {
  formatCompactNumber,
  formatDateTimeLines,
  formatPercentNullable,
  formatQuotaResetLabel,
  formatTimeLong,
} from "@/utils/formatters";

const ApiTrendChart = lazy(() =>
  import("@/features/apis/components/api-trend-chart").then((module) => ({
    default: (props: ApiTrendChartProps) => <module.ApiTrendChart {...props} />,
  })),
);

type TrendMode = "hourly" | "cumulative";

/** Running totals of values and of their cost coverage. */
function accumulate(points: ApiKeyTrendPoint[]): ApiKeyTrendPoint[] {
  let running = { v: 0, pricedRequests: 0, unpricedRequests: 0, unmeteredRequests: 0, coverageUnknown: false };
  return points.map((point) => {
    running = {
      v: running.v + point.v,
      pricedRequests: running.pricedRequests + (point.pricedRequests ?? 0),
      unpricedRequests: running.unpricedRequests + (point.unpricedRequests ?? 0),
      unmeteredRequests: running.unmeteredRequests + (point.unmeteredRequests ?? 0),
      coverageUnknown: running.coverageUnknown || !!point.coverageUnknown,
    };
    return { t: point.t, ...running };
  });
}

function formatDate(iso: string): string {
  return formatTimeLong(iso).date;
}

function LastWeekCard({
  apiKey,
  trends,
  usage,
  usageUnavailable,
}: {
  apiKey: ApiKey;
  trends: ApiKeyTrendsResponse | undefined;
  usage: ApiKeyUsage7DayResponse | undefined;
  usageUnavailable: boolean;
}) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<TrendMode>("hourly");
  const chart = useMemo(() => {
    if (!trends) return null;
    return mode === "cumulative"
      ? { cost: accumulate(trends.cost), tokens: accumulate(trends.tokens) }
      : { cost: trends.cost, tokens: trends.tokens };
  }, [trends, mode]);
  const placeholder = usageUnavailable ? t("apis.detail.usageUnavailable") : "--";
  const lastUsed = apiKey.lastUsedAt ? formatDateTimeLines(apiKey.lastUsedAt) : null;
  const stats: { label: string; value: string; meta?: string }[] = [
    { label: t("apis.detail.requests"), value: usage ? formatCompactNumber(usage.totalRequests) : placeholder },
    {
      label: t("apis.detail.tokens"),
      value: usage ? formatCompactNumber(usage.totalTokens) : placeholder,
      meta: usage ? t("apis.detail.cached", { value: formatCompactNumber(usage.cachedInputTokens) }) : undefined,
    },
    { label: t("apis.detail.cost"), value: usage ? formatCoveredCostShort(usage.totalCostUsd, usage) : placeholder },
    lastUsed
      ? { label: t("apis.list.lastUsed"), value: lastUsed.primary, meta: lastUsed.secondary }
      : { label: t("apis.list.lastUsed"), value: formatLastUsed(apiKey, t) },
  ];
  return (
    <DetailCard
      title={t("apis.detail.lastWeek")}
      data-testid="api-key-last-week"
      action={
        <ChartToggle<TrendMode>
          label={t("apiKeys.trend.mode")}
          value={mode}
          options={[
            { value: "hourly", label: t("apiKeys.trend.hourly") },
            { value: "cumulative", label: t("apiKeys.trend.cumulative") },
          ]}
          onChange={setMode}
        />
      }
    >
      <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="min-w-0">
            <div className="text-[11px] text-muted-foreground">{stat.label}</div>
            <div className="truncate text-lg font-semibold tabular-nums">{stat.value}</div>
            {stat.meta ? <div className="text-[11px] text-muted-foreground tabular-nums">{stat.meta}</div> : null}
          </div>
        ))}
      </div>
      <div className="mt-4 border-t pt-3">
        <div className="mb-2 flex items-center gap-3 text-[11px] text-muted-foreground" data-testid="api-trend-legend">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-chart-2" />
            {t("apis.trend.series.tokens")}
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-chart-1" />
            {t("apis.trend.series.cost")}
          </span>
        </div>
        {chart ? (
          <Suspense fallback={<div className="h-[280px]" />}>
            <ApiTrendChart cost={chart.cost} tokens={chart.tokens} />
          </Suspense>
        ) : (
          <div className="h-[280px]" />
        )}
      </div>
    </DetailCard>
  );
}

function CostByAccountCard({ usage }: { usage: ApiKeyUsage7DayResponse | undefined }) {
  const { t } = useTranslation();
  const isDark = useThemeStore((state) => state.theme === "dark");
  const blurred = usePrivacyStore((state) => state.blurred);
  const rows = useMemo(() => {
    const costs = (usage?.accountCosts ?? []).filter(
      (item) => item.costUsd > 0 || item.unpricedRequests > 0 || item.unmeteredRequests > 0,
    );
    const palette = accountColorPalette(isDark);
    // Unattributed usage takes the first colour no account in this card shows.
    const shown = new Set(costs.map((item) => item.chartColor));
    const unknownColor = palette.find((_, index) => !shown.has(index)) ?? palette[0];
    const deletedColor = isDark ? "#404040" : "#d3d3d3";
    const total = costs.reduce((sum, item) => sum + item.costUsd, 0);
    return costs
      .map((item, index) => ({
        id: item.isDeleted ? "deleted" : (item.accountId ?? item.modelSourceId ?? "unknown-" + index),
        label: item.isDeleted
          ? t("apis.accountCost.deletedAccount")
          : (item.name ?? t("apis.accountCost.unknownAccount")),
        named: !item.isDeleted && item.name !== null,
        provider: item.isDeleted ? null : item.provider,
        color: item.isDeleted ? deletedColor : item.chartColor === null ? unknownColor : palette[item.chartColor],
        cost: formatCoveredCostShort(item.costUsd, item),
        share: total > 0 ? (item.costUsd / total) * 100 : 0,
      }))
      .sort((left, right) => right.share - left.share);
  }, [usage, isDark, t]);
  return (
    <DetailCard title={t("apis.accountCost.title")} hint={t("apis.detail.lastWeekHint")} data-testid="account-cost-panel">
      {rows.length === 0 ? (
        <p className="text-xs text-muted-foreground">{t("apiKeys.trend.empty")}</p>
      ) : (
        <div className="flex flex-col gap-2.5">
          {rows.map((row) => (
            <div key={row.id} className="min-w-0" data-testid="account-cost-row">
              <div className="mb-1 flex min-w-0 items-center gap-2 text-xs">
                {row.provider ? (
                  <ProviderLogo provider={row.provider} color={row.color} />
                ) : (
                  <span aria-hidden className="flex size-4 shrink-0 items-center justify-center">
                    <span className="size-2.5 rounded-full" style={{ backgroundColor: row.color }} />
                  </span>
                )}
                <span className="min-w-0 truncate font-medium">
                  {row.named && blurred ? <span className="privacy-blur">{row.label}</span> : row.label}
                </span>
                <span className="ml-auto shrink-0 tabular-nums">
                  {row.cost} <span className="text-muted-foreground">· {Math.round(row.share)}%</span>
                </span>
              </div>
              <LimitTrack percent={row.share} color={row.color} className="ml-6" />
            </div>
          ))}
        </div>
      )}
    </DetailCard>
  );
}

function LimitsCard({ apiKey, color, editLink }: { apiKey: ApiKey; color: string | undefined; editLink: ReactNode }) {
  const { t } = useTranslation();
  const primary = apiKey.pooledCapacityCreditsPrimary > 0 ? apiKey.pooledRemainingPercentPrimary : null;
  const secondary = apiKey.pooledRemainingPercentSecondary;
  const pooled = [
    primary !== null ? { key: "5h", label: t("apis.listItem.pooled5h"), aria: t("apis.listItem.pooled5hAria"), percent: primary } : null,
    secondary !== null ? { key: "weekly", label: t("apis.listItem.pooledWeekly"), aria: t("apis.listItem.pooledWeeklyAria"), percent: secondary } : null,
  ].filter((item) => item !== null);
  return (
    <DetailCard title={t("apiKeys.form.limits")} action={editLink} data-testid="api-key-limits">
      <DetailParts>
        {apiKey.limits.length === 0 ? (
          <p className="text-xs text-muted-foreground">{t("apis.limits.noneDescription")}</p>
        ) : (
          <div className="flex flex-col gap-3">
            {apiKey.limits.map((limit) => {
              const percent = limitPercent(limit);
              return (
                <div key={limit.id} className="min-w-0">
                  <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
                    <span className="min-w-0 truncate text-muted-foreground">{limitName(limit, t)}</span>
                    <b className={percent >= 100 ? "font-semibold text-destructive tabular-nums" : "font-semibold tabular-nums"}>
                      {Math.round(percent)}%
                    </b>
                  </div>
                  <LimitTrack percent={percent} color={color} />
                  <div className="mt-1 flex justify-between gap-2 text-[11px] text-muted-foreground tabular-nums">
                    <span>
                      {t("apis.limits.ofMax", {
                        current: formatLimitAmount(limit, limit.currentValue),
                        max: formatLimitAmount(limit, limit.maxValue),
                      })}
                    </span>
                    <span>{t("apis.limits.resets", { time: formatQuotaResetLabel(limit.resetAt) })}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {pooled.length > 0 ? (
          <div className="flex flex-col gap-2">
            <span className="text-[11px] font-medium text-muted-foreground">{t("apis.limits.pooled")}</span>
            {pooled.map((item) => (
              <div key={item.key} className="flex items-center gap-2 text-xs">
                <span className="w-24 shrink-0 text-muted-foreground">{item.label}</span>
                <MiniQuotaBar aria-label={item.aria} percent={item.percent} testId={"pooled-quota-track-" + item.key} />
                <span className="w-10 shrink-0 text-right tabular-nums">{formatPercentNullable(item.percent)}</span>
              </div>
            ))}
          </div>
        ) : null}
      </DetailParts>
    </DetailCard>
  );
}

function AccessCard({ apiKey, editLink }: { apiKey: ApiKey; editLink: ReactNode }) {
  const { t } = useTranslation();
  const efforts = apiKey.enforcedReasoningEffort
    ? t("apis.access.enforced", { value: t("common.reasoning." + apiKey.enforcedReasoningEffort) })
    : apiKey.allowedReasoningEfforts && apiKey.allowedReasoningEfforts.length > 0
      ? apiKey.allowedReasoningEfforts.map((effort) => t("common.reasoning." + effort)).join(", ")
      : t("apis.access.any");
  const sections = apiKey.usageSections
    .split(",")
    .filter((section) => (USAGE_SECTIONS as readonly string[]).includes(section))
    .map((section) => t("apiKeys.usageSections." + section));
  const transport = {
    smart: "apiKeys.transport.smart",
    always_http: "apiKeys.transport.alwaysHttp",
    always_websocket: "apiKeys.transport.alwaysWebsocket",
  } as const;
  return (
    <DetailCard title={t("apis.access.title")} action={editLink} data-testid="api-key-access">
      <DetailRows
        rows={[
          {
            label: t("apiKeys.table.models"),
            value: apiKey.allowedModels?.length ? apiKey.allowedModels.join(", ") : t("apiKeys.modelSelect.all"),
          },
          ...(apiKey.enforcedModel ? [{ label: t("apiKeys.form.enforcedModel"), value: apiKey.enforcedModel }] : []),
          { label: t("apis.access.efforts"), value: efforts },
          {
            label: t("apis.access.accounts"),
            value: apiKey.accountAssignmentScopeEnabled
              ? t("apis.scope.accounts", { count: apiKey.assignedAccountIds.length })
              : t("apiKeys.accountSelect.all"),
          },
          {
            label: t("apis.access.sources"),
            value: apiKey.sourceAssignmentScopeEnabled
              ? t("apis.scope.sources", { count: apiKey.assignedSourceIds.length })
              : t("apis.access.allSources"),
          },
          {
            label: t("apiKeys.form.trafficClass"),
            value: t(apiKey.trafficClass === "opportunistic" ? "common.traffic.opportunistic" : "common.traffic.foreground"),
          },
          {
            label: t("apis.access.serviceTier"),
            value: apiKey.enforcedServiceTier ? t("common.serviceTier." + apiKey.enforcedServiceTier) : t("apis.access.clientChoice"),
          },
          {
            label: t("apiKeys.form.httpClientRouting"),
            value: t(apiKey.transportPolicyOverride ? transport[apiKey.transportPolicyOverride] : "apiKeys.transport.followGlobal"),
          },
          { label: t("apiKeys.form.usageSections"), value: sections.length > 0 ? sections.join(", ") : t("common.options.none") },
          { label: t("apiKeys.table.expiry"), value: apiKey.expiresAt ? formatDate(apiKey.expiresAt) : t("common.time.never") },
        ]}
      />
    </DetailCard>
  );
}

function LifetimeCard({ apiKey, lifetimeTotal }: { apiKey: ApiKey; lifetimeTotal: number }) {
  const { t } = useTranslation();
  const usage = apiKey.usageSummary;
  const share = lifetimeTotal > 0 && usage ? Math.round((usage.totalCostUsd / lifetimeTotal) * 100) : 0;
  return (
    <DetailCard
      title={t("apis.detail.lifetime")}
      hint={t("apis.detail.since", { date: formatDate(apiKey.createdAt) })}
      data-testid="api-key-lifetime"
    >
      <DetailRows
        rows={[
          { label: t("apis.detail.requests"), value: formatCompactNumber(usage?.requestCount ?? 0) },
          {
            label: t("apis.detail.tokens"),
            value: usage
              ? formatCompactNumber(usage.totalTokens) + " · " + t("apis.detail.cached", { value: formatCompactNumber(usage.cachedInputTokens) })
              : formatCompactNumber(0),
          },
          {
            label: t("apis.detail.cost"),
            value: (
              <>
                {usage ? formatCoveredCostShort(usage.totalCostUsd, usage) : formatCompactNumber(0)}
                <span className="font-normal text-muted-foreground"> · {t("apis.detail.shareOfAll", { percent: share })}</span>
              </>
            ),
          },
        ]}
      />
    </DetailCard>
  );
}

export type KeyDetailProps = {
  apiKey: ApiKey;
  color: string | undefined;
  lifetimeTotal: number;
  trends: ApiKeyTrendsResponse | undefined;
  usage: ApiKeyUsage7DayResponse | undefined;
  usageUnavailable: boolean;
  busy: boolean;
  readOnly: boolean;
  onSave: (payload: ApiKeyUpdateRequest) => Promise<unknown>;
  onResetUsage: () => Promise<unknown>;
  onRegenerate: () => void;
  onToggleActive: () => void;
  onDelete: () => void;
};

/** One API key: header with actions, a state banner, then an Overview and a Settings tab. */
export function KeyDetail({
  apiKey,
  color,
  lifetimeTotal,
  trends,
  usage,
  usageUnavailable,
  busy,
  readOnly,
  onSave,
  onResetUsage,
  onRegenerate,
  onToggleActive,
  onDelete,
}: KeyDetailProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const urlTab = useKeyTab();
  // Read-only sessions have no Settings tab.
  const tab: KeyTab = readOnly ? "overview" : urlTab;
  const state = keyState(apiKey);
  const settingsHref = keyHref(apiKey.id, "settings");
  const toSettings = (label: string) => (
    <Button asChild size="sm" variant="outline">
      <Link to={settingsHref}>{label}</Link>
    </Button>
  );
  const editLink = readOnly ? null : (
    <Link to={settingsHref} className="text-xs font-medium text-primary hover:underline">
      {t("common.actions.edit")}
    </Link>
  );

  const blocking = blockingLimit(apiKey);
  const banner =
    state === "limited" && blocking ? (
      <DetailBanner tone="bad" icon={<Clock />} action={readOnly ? undefined : toSettings(t("apis.banner.editLimits"))}>
        {t("apis.banner.limited", {
          limit: limitName(blocking, t),
          current: formatLimitAmount(blocking, blocking.currentValue),
          max: formatLimitAmount(blocking, blocking.maxValue),
          time: formatQuotaResetLabel(blocking.resetAt),
        })}
      </DetailBanner>
    ) : state === "expiring" && apiKey.expiresAt ? (
      <DetailBanner tone="warn" icon={<CalendarClock />} action={readOnly ? undefined : toSettings(t("apis.banner.changeExpiry"))}>
        {t("apis.banner.expiring", { date: formatDate(apiKey.expiresAt), relative: keyStateDetail(apiKey, state, t) })}
      </DetailBanner>
    ) : state === "disabled" ? (
      <DetailBanner
        tone="off"
        icon={<PauseCircle />}
        action={
          readOnly ? undefined : (
            <Button size="sm" variant="outline" disabled={busy} onClick={onToggleActive}>
              {t("common.actions.enable")}
            </Button>
          )
        }
      >
        {t("apis.banner.disabled")}
      </DetailBanner>
    ) : state === "expired" && apiKey.expiresAt ? (
      <DetailBanner tone="off" icon={<CalendarX />} action={readOnly ? undefined : toSettings(t("apis.banner.changeExpiry"))}>
        {t("apis.banner.expired", { date: formatDate(apiKey.expiresAt) })}
      </DetailBanner>
    ) : null;

  const menu: DetailMenuItem[] = [
    {
      key: "copy-prefix",
      label: t("apis.detail.copyPrefix"),
      icon: <Copy />,
      onSelect: () => void navigator.clipboard.writeText(apiKey.keyPrefix),
    },
    {
      key: "copy-id",
      label: t("apis.detail.copyId"),
      icon: <Copy />,
      onSelect: () => void navigator.clipboard.writeText(apiKey.id),
    },
    ...(readOnly
      ? []
      : [{ key: "delete", label: t("apis.detail.delete"), icon: <Trash2 />, onSelect: onDelete, destructive: true, disabled: busy }]),
  ];
  const subline = [
    <span key="prefix" className="font-mono">{apiKey.keyPrefix}</span>,
    t("apis.detail.created", { date: formatDate(apiKey.createdAt) }),
    t("apis.detail.lastUsed", { value: formatLastUsed(apiKey, t) }),
    apiKey.expiresAt ? t("apis.detail.expires", { date: formatDate(apiKey.expiresAt) }) : t("apis.detail.neverExpires"),
  ];

  return (
    <div data-testid="api-key-detail" data-tab={tab} className="animate-fade-in-up flex min-w-0 flex-col gap-4">
      <div className="flex min-w-0 flex-wrap items-start gap-x-3 gap-y-2">
        <span className="mt-1 flex">
          <KeyRound className="size-6" style={{ color }} aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-[1_1_16rem]">
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
            <h1 className="min-w-0 truncate text-xl font-semibold tracking-tight">{apiKey.name}</h1>
            <KeyStateBadge state={state} />
          </div>
          <p className="mt-1 flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs text-muted-foreground">
            {subline.map((part, index) => (
              <Fragment key={index}>
                {index > 0 ? <span aria-hidden="true">·</span> : null}
                <span className="min-w-0 break-all">{part}</span>
              </Fragment>
            ))}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Button size="sm" variant="outline" className="gap-1.5" onClick={() => navigate("/logs?apiKeyId=" + encodeURIComponent(apiKey.id))}>
            <ScrollText className="size-3.5" />
            {t("providers.detail.openLogs")}
          </Button>
          {readOnly ? null : (
            <>
              <Button size="sm" variant="outline" className="gap-1.5" disabled={busy} onClick={onRegenerate}>
                <RefreshCw className="size-3.5" />
                {t("common.actions.regenerate")}
              </Button>
              <Button size="sm" variant="outline" className="gap-1.5" disabled={busy} onClick={onToggleActive}>
                {apiKey.isActive ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
                {t(apiKey.isActive ? "common.actions.disable" : "common.actions.enable")}
              </Button>
            </>
          )}
          <DetailMenu items={menu} label={t("providers.detail.moreActions")} />
        </div>
      </div>
      {banner}
      {readOnly ? null : (
        <div>
          <ChartToggle<KeyTab>
            label={t("apis.detail.tabs")}
            value={tab}
            onChange={(next) => navigate(keyHref(apiKey.id, next))}
            options={[
              { value: "overview", label: t("providers.detail.tabs.overview"), icon: <LayoutDashboard className="h-3.5 w-3.5" aria-hidden="true" /> },
              { value: "settings", label: t("providers.detail.tabs.settings"), icon: <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" /> },
            ]}
          />
        </div>
      )}
      {tab === "overview" ? (
        <div className="grid min-w-0 grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(19rem,1fr)]">
          <div className="flex min-w-0 flex-col gap-4">
            <LastWeekCard apiKey={apiKey} trends={trends} usage={usage} usageUnavailable={usageUnavailable} />
            <CostByAccountCard usage={usage} />
          </div>
          <div className="flex min-w-0 flex-col gap-4">
            <LimitsCard apiKey={apiKey} color={color} editLink={editLink} />
            <AccessCard apiKey={apiKey} editLink={editLink} />
            <LifetimeCard apiKey={apiKey} lifetimeTotal={lifetimeTotal} />
          </div>
        </div>
      ) : (
        <ApiKeySettingsForm
          key={apiKey.id}
          apiKey={apiKey}
          busy={busy}
          onSave={onSave}
          onResetUsage={onResetUsage}
          onRegenerate={onRegenerate}
          onToggleActive={onToggleActive}
          onDelete={onDelete}
        />
      )}
    </div>
  );
}
