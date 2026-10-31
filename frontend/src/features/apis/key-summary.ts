import type { TFunction } from "i18next";
import { useMemo } from "react";
import { useMatch } from "react-router-dom";

import type { ApiKey, LimitRule } from "@/features/api-keys/schemas";
import type { ApiKeysTrendsResponse } from "@/features/apis/schemas";
import type { CostCoverage } from "@/features/dashboard/cost-coverage";
import { useThemeStore } from "@/hooks/use-theme";
import { buildDonutPalette } from "@/utils/colors";
import {
  formatCompactNumber,
  formatCurrency,
  formatDateTimeInline,
  formatExpiresIn,
  formatQuotaResetLabel,
  formatTimeLong,
} from "@/utils/formatters";

const DAY_MS = 86_400_000;
/** A key expiring within this window needs attention. */
const EXPIRING_MS = 14 * DAY_MS;
/** Six-hour buckets over the seven-day window. */
export const WEEK_BUCKETS = 28;

export type KeyState = "active" | "expiring" | "limited" | "disabled" | "expired";
export type KeyTone = "ok" | "warn" | "bad" | "off";

export const KEY_TONE: Record<KeyState, KeyTone> = {
  active: "ok",
  expiring: "warn",
  limited: "bad",
  disabled: "off",
  expired: "off",
};

export const KEY_DOT: Record<KeyTone, string> = {
  ok: "bg-emerald-500",
  warn: "bg-amber-500",
  bad: "bg-destructive",
  off: "bg-muted-foreground",
};

export const KEY_TEXT: Record<KeyTone, string> = {
  ok: "text-muted-foreground",
  off: "text-muted-foreground",
  warn: "text-amber-600 dark:text-amber-400",
  bad: "text-destructive",
};

export function limitPercent(limit: LimitRule): number {
  return limit.maxValue > 0 ? Math.min(100, (limit.currentValue / limit.maxValue) * 100) : 0;
}

function isReached(limit: LimitRule): boolean {
  return limit.maxValue > 0 && limit.currentValue >= limit.maxValue;
}

/** The reached rule that blocks the key longest, or null when no rule is reached. */
export function blockingLimit(apiKey: ApiKey): LimitRule | null {
  return apiKey.limits
    .filter(isReached)
    .reduce<LimitRule | null>((latest, limit) => (!latest || limit.resetAt > latest.resetAt ? limit : latest), null);
}

export function keyState(apiKey: ApiKey, now = Date.now()): KeyState {
  if (!apiKey.isActive) return "disabled";
  const expiresAt = apiKey.expiresAt ? new Date(apiKey.expiresAt).getTime() : null;
  if (expiresAt !== null && expiresAt <= now) return "expired";
  if (blockingLimit(apiKey)) return "limited";
  if (expiresAt !== null && expiresAt - now <= EXPIRING_MS) return "expiring";
  return "active";
}

export type KeyFilter = "all" | "active" | "attention" | "inactive";
export const KEY_FILTERS: KeyFilter[] = ["all", "active", "attention", "inactive"];

export function matchesKeyFilter(state: KeyState, filter: KeyFilter): boolean {
  switch (filter) {
    case "all":
      return true;
    case "active":
      return state === "active" || state === "expiring";
    case "attention":
      return state === "limited" || state === "expiring";
    case "inactive":
      return state === "disabled" || state === "expired";
  }
}

export function matchesKeySearch(apiKey: ApiKey, search: string): boolean {
  const query = search.trim().toLowerCase();
  return !query || apiKey.name.toLowerCase().includes(query) || apiKey.keyPrefix.toLowerCase().includes(query);
}

/** Amount of a limit rule in its own unit: cost rules count micro-dollars. */
export function formatLimitAmount(limit: Pick<LimitRule, "limitType">, value: number): string {
  return limit.limitType === "cost_usd" ? formatCurrency(value / 1_000_000) : formatCompactNumber(value);
}

export function limitName(limit: LimitRule, t: TFunction): string {
  return [
    t("apiKeys.limitTypes." + limit.limitType),
    t("apiKeys.limitWindows." + limit.limitWindow).toLowerCase(),
    limit.modelFilter,
  ]
    .filter(Boolean)
    .join(" · ");
}

/** Second line of a key's status: when it expires, which limit blocks it, or when it expired. */
export function keyStateDetail(apiKey: ApiKey, state: KeyState, t: TFunction): string | null {
  if (state === "expiring" && apiKey.expiresAt) {
    return t("apis.state.expiresIn", { relative: formatExpiresIn(apiKey.expiresAt) });
  }
  if (state === "expired" && apiKey.expiresAt) return formatTimeLong(apiKey.expiresAt).date;
  const limit = state === "limited" ? blockingLimit(apiKey) : null;
  if (limit) return limitName(limit, t) + " · " + t("apis.limits.resets", { time: formatQuotaResetLabel(limit.resetAt) });
  return null;
}

/** Models, accounts and a non-foreground traffic class of a key, in one line. */
export function keyScope(apiKey: ApiKey, t: TFunction): string {
  const models = apiKey.enforcedModel
    ? apiKey.enforcedModel
    : !apiKey.allowedModels || apiKey.allowedModels.length === 0
      ? t("apiKeys.modelSelect.all")
      : apiKey.allowedModels.length === 1
        ? apiKey.allowedModels[0]
        : t("apis.scope.models", { count: apiKey.allowedModels.length });
  const routes = [
    apiKey.accountAssignmentScopeEnabled ? t("apis.scope.accounts", { count: apiKey.assignedAccountIds.length }) : null,
    apiKey.sourceAssignmentScopeEnabled ? t("apis.scope.sources", { count: apiKey.assignedSourceIds.length }) : null,
  ].filter(Boolean);
  return [
    models,
    routes.length > 0 ? routes.join(", ") : t("apiKeys.accountSelect.all"),
    apiKey.trafficClass === "opportunistic" ? t("common.traffic.opportunistic") : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

export function formatLastUsed(apiKey: ApiKey, t: TFunction): string {
  return apiKey.lastUsedAt ? formatDateTimeInline(apiKey.lastUsedAt) : t("apis.lastUsedNever");
}

export type KeyWeek = {
  costUsd: number;
  tokens: number;
  coverage: Required<CostCoverage>;
  /** Cost per six-hour bucket across the window. */
  costBuckets: number[];
};

function emptyWeek(): KeyWeek {
  return {
    costUsd: 0,
    tokens: 0,
    coverage: { pricedRequests: 0, unpricedRequests: 0, unmeteredRequests: 0, coverageUnknown: false },
    costBuckets: Array.from({ length: WEEK_BUCKETS }, () => 0),
  };
}

/** Each key's last seven days, from the comparison trends of all providers. */
export function weeklyUsageByKey(data: ApiKeysTrendsResponse | undefined): Map<string, KeyWeek> {
  const weeks = new Map<string, KeyWeek>();
  if (!data) return weeks;
  const since = new Date(data.since).getTime();
  const span = Math.max(1, new Date(data.until).getTime() - since);
  for (const series of data.series) {
    if (series.isDeleted || series.keyId === null) continue;
    const week = emptyWeek();
    for (const point of series.cost) {
      week.costUsd += point.v;
      week.coverage.pricedRequests += point.pricedRequests ?? 0;
      week.coverage.unpricedRequests += point.unpricedRequests ?? 0;
      week.coverage.unmeteredRequests += point.unmeteredRequests ?? 0;
      week.coverage.coverageUnknown ||= !!point.coverageUnknown;
      const bucket = Math.floor(((new Date(point.t).getTime() - since) / span) * WEEK_BUCKETS);
      week.costBuckets[Math.min(WEEK_BUCKETS - 1, Math.max(0, bucket))] += point.v;
    }
    week.tokens = series.tokens.reduce((sum, point) => sum + point.v, 0);
    weeks.set(series.keyId, week);
  }
  return weeks;
}

export type KeySort = "lastUsed" | "cost7d" | "costLifetime" | "name" | "expiry";
export const KEY_SORTS: KeySort[] = ["lastUsed", "cost7d", "costLifetime", "name", "expiry"];

export function sortKeys(apiKeys: ApiKey[], sort: KeySort, weeks: Map<string, KeyWeek>): ApiKey[] {
  const byName = (left: ApiKey, right: ApiKey) => left.name.localeCompare(right.name);
  const descending = (value: (apiKey: ApiKey) => number) => (left: ApiKey, right: ApiKey) =>
    value(right) - value(left) || byName(left, right);
  const compare = {
    lastUsed: descending((apiKey) => (apiKey.lastUsedAt ? new Date(apiKey.lastUsedAt).getTime() : 0)),
    cost7d: descending((apiKey) => weeks.get(apiKey.id)?.costUsd ?? 0),
    costLifetime: descending((apiKey) => apiKey.usageSummary?.totalCostUsd ?? 0),
    name: byName,
    // Keys without expiry come last.
    expiry: (left: ApiKey, right: ApiKey) =>
      (left.expiresAt ? new Date(left.expiresAt).getTime() : Infinity) -
        (right.expiresAt ? new Date(right.expiresAt).getTime() : Infinity) || byName(left, right),
  }[sort];
  return [...apiKeys].sort(compare);
}

export function lifetimeCostTotal(apiKeys: ApiKey[]): number {
  return apiKeys.reduce((sum, apiKey) => sum + (apiKey.usageSummary?.totalCostUsd ?? 0), 0);
}

/** Colours by comparison series id (`key:<id>`, `deleted`, `other`), stable in creation order. */
export type KeyColors = Map<string, string>;

export function keySeriesId(keyId: string): string {
  return "key:" + keyId;
}

export function useKeyColors(apiKeys: ApiKey[]): KeyColors {
  const isDark = useThemeStore((state) => state.theme === "dark");
  return useMemo(() => {
    const ordered = [...apiKeys].sort(
      (left, right) => left.createdAt.localeCompare(right.createdAt) || left.id.localeCompare(right.id),
    );
    const palette = buildDonutPalette(ordered.length + 2, isDark);
    const colors: KeyColors = new Map(ordered.map((apiKey, index) => [keySeriesId(apiKey.id), palette[index]]));
    colors.set("deleted", palette[ordered.length]);
    colors.set("other", palette[ordered.length + 1]);
    return colors;
  }, [apiKeys, isDark]);
}

export type KeyTab = "overview" | "settings";

export function keyHref(id: string, tab: KeyTab = "overview"): string {
  const href = "/keys/" + encodeURIComponent(id);
  return tab === "settings" ? href + "/settings" : href;
}

/** Tab of the open key page, carried in the URL so links and reloads keep it. */
export function useKeyTab(): KeyTab {
  return useMatch("/keys/:keyId/settings") ? "settings" : "overview";
}
