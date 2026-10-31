import { Copy, ExternalLink, KeyRound, MoreHorizontal, Pause, Play, RefreshCw, ScrollText, Search } from "lucide-react";
import { useMemo, useState, type KeyboardEvent, type MouseEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { ApiKey } from "@/features/api-keys/schemas";
import { KeyLimitMeter, KeySparkline, KeyStateBadge } from "@/features/apis/components/key-parts";
import {
  KEY_FILTERS,
  KEY_SORTS,
  KEY_TEXT,
  KEY_TONE,
  formatLastUsed,
  keyHref,
  keyScope,
  keySeriesId,
  keyState,
  keyStateDetail,
  matchesKeyFilter,
  matchesKeySearch,
  sortKeys,
  type KeyColors,
  type KeyFilter,
  type KeySort,
  type KeyWeek,
} from "@/features/apis/key-summary";
import { formatCoveredCostShort } from "@/features/dashboard/cost-coverage";
import { cn } from "@/lib/utils";
import { formatCompactNumber, formatCurrency } from "@/utils/formatters";

const ROW_GRID =
  "grid grid-cols-2 items-center gap-x-3 gap-y-2 px-4 lg:grid-cols-[minmax(14rem,1.5fr)_minmax(8rem,.8fr)_minmax(12rem,1.2fr)_minmax(10rem,1fr)_minmax(9rem,.9fr)_minmax(7rem,.7fr)_2.25rem] lg:gap-x-4";

export type KeyActions = {
  onRegenerate: (apiKey: ApiKey) => void;
  onToggleActive: (apiKey: ApiKey) => void;
};

function share(value: number, total: number): number {
  return total > 0 ? (value / total) * 100 : 0;
}

function formatShare(percent: number): string {
  return percent > 0 && percent < 1 ? "<1%" : Math.round(percent) + "%";
}

export function KeyRowMenu({ apiKey, readOnly, actions }: { apiKey: ApiKey; readOnly: boolean; actions: KeyActions }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          aria-label={t("apis.list.rowActions", { name: apiKey.name })}
          onClick={(event: MouseEvent) => event.stopPropagation()}
        >
          <MoreHorizontal className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" onClick={(event: MouseEvent) => event.stopPropagation()}>
        <DropdownMenuItem onSelect={() => navigate(keyHref(apiKey.id))}>
          <ExternalLink />
          {t("apis.list.open")}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate("/logs?apiKeyId=" + encodeURIComponent(apiKey.id))}>
          <ScrollText />
          {t("providers.detail.openLogs")}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => void navigator.clipboard.writeText(apiKey.keyPrefix)}>
          <Copy />
          {t("apis.detail.copyPrefix")}
        </DropdownMenuItem>
        {readOnly ? null : (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => actions.onRegenerate(apiKey)}>
              <RefreshCw />
              {t("common.actions.regenerate")}
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => actions.onToggleActive(apiKey)}>
              {apiKey.isActive ? <Pause /> : <Play />}
              {t(apiKey.isActive ? "common.actions.disable" : "common.actions.enable")}
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function KeyRow({
  apiKey,
  color,
  week,
  lifetimeTotal,
  readOnly,
  actions,
}: {
  apiKey: ApiKey;
  color: string | undefined;
  week: KeyWeek | undefined;
  lifetimeTotal: number;
  readOnly: boolean;
  actions: KeyActions;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const state = keyState(apiKey);
  const detail = keyStateDetail(apiKey, state, t);
  const dim = state === "disabled" || state === "expired";
  const lifetime = apiKey.usageSummary;
  const lifetimeShare = share(lifetime?.totalCostUsd ?? 0, lifetimeTotal);
  const href = keyHref(apiKey.id);
  const onKeyDown = (event: KeyboardEvent) => {
    if (event.target === event.currentTarget && event.key === "Enter") navigate(href);
  };
  return (
    <div
      role="row"
      data-testid="api-key-row"
      tabIndex={-1}
      onClick={() => navigate(href)}
      onKeyDown={onKeyDown}
      className={cn(ROW_GRID, "cursor-pointer border-b py-2.5 last:border-b-0 hover:bg-accent/60")}
    >
      <div role="cell" className={cn("min-w-0", dim && "opacity-55")}>
        <div className="flex min-w-0 items-center gap-2">
          <span aria-hidden="true" className="size-2.5 shrink-0 rounded-[3px]" style={{ backgroundColor: color }} />
          <Link
            to={href}
            onClick={(event) => event.stopPropagation()}
            className="min-w-0 truncate text-sm font-semibold hover:underline"
          >
            {apiKey.name}
          </Link>
          <span className="shrink-0 rounded border px-1 font-mono text-[10.5px] text-muted-foreground">{apiKey.keyPrefix}</span>
        </div>
        <p className="mt-0.5 truncate pl-[18px] text-xs text-muted-foreground">{keyScope(apiKey, t)}</p>
      </div>
      <div role="cell" className="min-w-0 justify-self-end lg:justify-self-start">
        <KeyStateBadge state={state} />
        {detail ? (
          <span className={cn("mt-0.5 block max-w-48 truncate text-[11px]", KEY_TEXT[KEY_TONE[state]])} title={detail}>
            {detail}
          </span>
        ) : null}
      </div>
      <div role="cell" className={cn("col-span-2 flex min-w-0 flex-col gap-1.5 lg:col-span-1", dim && "opacity-55")}>
        {apiKey.limits.length === 0 ? (
          <span className="text-xs text-muted-foreground">{t("apis.limits.none")}</span>
        ) : (
          <>
            {apiKey.limits.slice(0, 2).map((limit) => (
              <KeyLimitMeter key={limit.id} limit={limit} color={color} />
            ))}
            {apiKey.limits.length > 2 ? (
              <span className="text-[11px] text-muted-foreground">{t("apis.limits.more", { count: apiKey.limits.length - 2 })}</span>
            ) : null}
          </>
        )}
      </div>
      <div role="cell" className={cn("flex min-w-0 items-center gap-2.5", dim && "opacity-55")}>
        <KeySparkline buckets={week?.costBuckets} color={color} />
        <div className="min-w-0 text-xs tabular-nums">
          <div className="font-semibold">{week ? formatCoveredCostShort(week.costUsd, week.coverage) : formatCurrency(0)}</div>
          <div className="text-[11px] text-muted-foreground">
            {t("apis.list.tokens", { value: formatCompactNumber(week?.tokens ?? 0) })}
          </div>
        </div>
      </div>
      <div role="cell" className={cn("min-w-0 text-xs tabular-nums", dim && "opacity-55")}>
        <div>
          <span className="font-semibold">{lifetime ? formatCoveredCostShort(lifetime.totalCostUsd, lifetime) : formatCurrency(0)}</span>
          <span className="text-[11px] text-muted-foreground"> · {formatShare(lifetimeShare)}</span>
        </div>
        <div className="my-1 h-[3px] overflow-hidden rounded-full bg-muted">
          <div className="h-full rounded-full" style={{ width: lifetimeShare + "%", backgroundColor: color }} />
        </div>
        <div className="text-[11px] text-muted-foreground">
          {t("apis.list.requests", { value: formatCompactNumber(lifetime?.requestCount ?? 0) })}
        </div>
      </div>
      <div role="cell" className="hidden text-xs text-muted-foreground lg:block">{formatLastUsed(apiKey, t)}</div>
      <div role="cell" className="hidden justify-self-end lg:block">
        <KeyRowMenu apiKey={apiKey} readOnly={readOnly} actions={actions} />
      </div>
    </div>
  );
}

export type KeysListProps = {
  apiKeys: ApiKey[];
  weeks: Map<string, KeyWeek>;
  colors: KeyColors;
  lifetimeTotal: number;
  readOnly: boolean;
  actions: KeyActions;
};

/** Every API key with its status, limits, last seven days, lifetime usage and last use. */
export function KeysList({ apiKeys, weeks, colors, lifetimeTotal, readOnly, actions }: KeysListProps) {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<KeyFilter>("all");
  const [sort, setSort] = useState<KeySort>("lastUsed");
  const states = useMemo(() => new Map(apiKeys.map((apiKey) => [apiKey.id, keyState(apiKey)])), [apiKeys]);
  const counts = Object.fromEntries(
    KEY_FILTERS.map((option) => [option, apiKeys.filter((apiKey) => matchesKeyFilter(states.get(apiKey.id)!, option)).length]),
  ) as Record<KeyFilter, number>;
  const visible = useMemo(
    () =>
      sortKeys(
        apiKeys.filter((apiKey) => matchesKeyFilter(states.get(apiKey.id)!, filter) && matchesKeySearch(apiKey, search)),
        sort,
        weeks,
      ),
    [apiKeys, states, filter, search, sort, weeks],
  );
  return (
    <section data-testid="api-keys-list" className="min-w-0 overflow-hidden rounded-xl border bg-card shadow-xs">
      <div className="flex flex-wrap items-center gap-2 border-b px-3 py-2.5">
        <div className="relative min-w-0 flex-1 basis-full sm:max-w-72 sm:basis-auto">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60" aria-hidden />
          <Input
            placeholder={t("apis.list.searchPlaceholder")}
            aria-label={t("apis.list.searchPlaceholder")}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="h-8 pl-8"
          />
        </div>
        <div role="group" aria-label={t("apis.filter.label")} className="inline-flex flex-wrap gap-0.5 rounded-lg border bg-muted p-0.5">
          {KEY_FILTERS.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={filter === option}
              onClick={() => setFilter(option)}
              className={cn(
                "inline-flex h-7 items-center gap-1.5 rounded-md px-2.5 text-xs text-muted-foreground transition-colors hover:text-foreground",
                filter === option && "bg-card font-medium text-foreground shadow-xs",
              )}
            >
              {t("apis.filter." + option)}
              <span className="text-[11px] tabular-nums opacity-75">{counts[option]}</span>
            </button>
          ))}
        </div>
        <Select value={sort} onValueChange={(value) => setSort(value as KeySort)}>
          <SelectTrigger size="sm" className="ml-auto w-44 min-w-0" aria-label={t("apis.sort.label")}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {KEY_SORTS.map((option) => (
              <SelectItem key={option} value={option}>
                {t("apis.sort." + option)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div role="table" aria-label={t("apis.page.title")}>
        <div role="row" className={cn(ROW_GRID, "hidden border-b py-2 text-[11.5px] font-medium text-muted-foreground lg:grid")}>
          <span role="columnheader">{t("apis.list.key")}</span>
          <span role="columnheader">{t("apis.list.status")}</span>
          <span role="columnheader">{t("apis.list.limits")}</span>
          <span role="columnheader">{t("apis.list.lastWeek")}</span>
          <span role="columnheader">{t("apis.list.lifetime")}</span>
          <span role="columnheader">{t("apis.list.lastUsed")}</span>
          <span />
        </div>
        {visible.length === 0 ? (
          <div className="flex flex-col items-center px-4 py-10 text-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
              <KeyRound className="h-4 w-4 text-muted-foreground" aria-hidden />
            </div>
            <p className="mt-3 text-sm font-medium text-muted-foreground">
              {apiKeys.length === 0 ? t("apis.list.emptyTitle") : t("apis.list.noMatches")}
            </p>
            <p className="mt-1 text-xs text-muted-foreground/70">
              {apiKeys.length === 0 ? t("apis.list.emptyDescription") : t("apis.list.adjustFilters")}
            </p>
          </div>
        ) : (
          visible.map((apiKey) => (
            <KeyRow
              key={apiKey.id}
              apiKey={apiKey}
              color={colors.get(keySeriesId(apiKey.id))}
              week={weeks.get(apiKey.id)}
              lifetimeTotal={lifetimeTotal}
              readOnly={readOnly}
              actions={actions}
            />
          ))
        )}
      </div>
      <p className="border-t px-4 py-2.5 text-[11px] text-muted-foreground">{t("apis.list.secretsNote")}</p>
    </section>
  );
}
