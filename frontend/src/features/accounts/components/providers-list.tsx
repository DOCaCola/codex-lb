import { Copy, ExternalLink, Flame, MoreHorizontal, Plus, ScrollText, Search, Shield, ShieldCheck } from "lucide-react";
import { useMemo, useState, type KeyboardEvent, type MouseEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { ProviderLogo } from "@/components/brand/provider-account-name";
import { PlanBadge } from "@/components/plan-badge";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { AccountColorHexes } from "@/features/accounts/account-colors";
import type { AccountActivity } from "@/features/accounts/hooks/use-provider-activity";
import {
  PROVIDER_LABELS,
  PROVIDER_LIMIT_CAPTIONS,
  PROVIDER_ORDER,
  accountHref,
  filterGroups,
  matchesFilter,
  noticeClass,
  summaryColor,
  type LimitSummary,
  type ProviderFilter,
  type ProviderGroup,
  type ProviderKind,
  type ProviderSummary,
} from "@/features/accounts/provider-summary";
import { ACCOUNT_SORT_OPTIONS, type AccountSortMode } from "@/features/accounts/sorting";
import { ExtraUsageBadge } from "@/features/claude/account-display";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import { quotaBarColor } from "@/utils/account-status";
import { formatCompactAccountId } from "@/utils/account-identifiers";
import { formatCompactNumber, formatCurrency, formatDateTimeInline, formatQuotaResetLabel, formatSlug } from "@/utils/formatters";

/** Fill bar of a limit with the even-pace tick. */
export function LimitBar({ limit, className }: { limit: LimitSummary; className?: string }) {
  const percent = limit.percentLeft;
  return (
    <div className={cn("relative h-[5px] rounded-full bg-muted", className)}>
      {percent !== null ? (
        <div className={cn("h-full rounded-full", quotaBarColor(percent))} style={{ width: percent + "%" }} />
      ) : null}
      {limit.pacePercent !== null ? (
        <span
          aria-hidden="true"
          title="Even pace through the window"
          className="absolute -top-[3px] h-[11px] w-0.5 -translate-x-1/2 rounded-[1px] bg-foreground/55"
          style={{ left: limit.pacePercent + "%" }}
        />
      ) : null}
    </div>
  );
}

function limitMeta(limit: LimitSummary): string | null {
  const parts = [limit.resetAt ? formatQuotaResetLabel(limit.resetAt) : limit.caption, limit.stale ? "stale" : null];
  const text = parts.filter(Boolean).join(" · ");
  return text || null;
}

function LimitMeter({ limit, className }: { limit: LimitSummary; className?: string }) {
  const meta = limitMeta(limit);
  return (
    <div className={cn("min-w-0", className)}>
      <div className="mb-1 flex min-w-0 items-baseline justify-between gap-2 text-xs">
        <span className="min-w-0 truncate">
          <span className="mr-1 text-muted-foreground lg:hidden">{limit.label}</span>
          <b className={cn("font-semibold tabular-nums", limit.percentLeft === 0 && "text-destructive")}>{limit.value}</b>
        </span>
        {meta ? <span className="shrink-0 truncate text-muted-foreground tabular-nums">{meta}</span> : null}
      </div>
      <LimitBar limit={limit} />
    </div>
  );
}

const ROW_GRID =
  "grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 px-4 lg:grid-cols-[minmax(13rem,1.6fr)_minmax(8rem,.9fr)_minmax(9rem,1fr)_minmax(9rem,1fr)_minmax(7rem,.7fr)_6.5rem_2.25rem] lg:gap-x-4";

function RoutingCell({ summary }: { summary: ProviderSummary }) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  const policy = summary.routingPolicy;
  const policyLabel =
    policy === "burn_first"
      ? t("common.routingPolicies.burnFirst")
      : policy === "preserve"
        ? t("common.routingPolicies.preserve")
        : policy === "normal"
          ? t("common.routingPolicies.normal")
          : null;
  const PolicyIcon = policy === "burn_first" ? Flame : policy === "preserve" ? Shield : null;
  const codex = summary.entry.kind === "codex" ? summary.entry.account : null;
  const warmup = codex?.limitWarmup;
  const warmupMeta = codex
    ? warmup
      ? [formatSlug(warmup.status), formatSlug(warmup.model), formatDateTimeInline(warmup.completedAt ?? warmup.attemptedAt, dateDisplayFormat)].join(" | ")
      : t("accounts.listItem.noAttempts")
    : undefined;
  return (
    <div className="min-w-0 text-xs text-muted-foreground">
      {policyLabel ? (
        <span className="inline-flex items-center gap-1 text-foreground/80">
          {PolicyIcon ? <PolicyIcon className="h-3 w-3" aria-hidden="true" /> : null}
          {policyLabel}
        </span>
      ) : (
        <span>—</span>
      )}
      <span className="block truncate text-[11px]" title={warmupMeta}>
        {summary.warmupEnabled === null
          ? summary.models
          : summary.warmupEnabled
            ? t("accounts.listItem.warmupOn")
            : t("accounts.listItem.warmupOff")}
      </span>
    </div>
  );
}

function TodayCell({ activity }: { activity: AccountActivity | undefined | null }) {
  const { t } = useTranslation();
  if (activity === null) return <span className="text-xs text-muted-foreground">—</span>;
  const today = activity?.today;
  return (
    <div className="text-right text-xs tabular-nums">
      <span>{t("providers.list.requests", { value: formatCompactNumber(today?.requests ?? 0) })}</span>
      <span className="block text-[11px] text-muted-foreground">{formatCurrency(today?.costUsd ?? 0)}</span>
    </div>
  );
}

function RowMenu({ summary }: { summary: ProviderSummary }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          aria-label={t("providers.list.rowActions", { name: summary.name })}
          onClick={(event: MouseEvent) => event.stopPropagation()}
        >
          <MoreHorizontal className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" onClick={(event: MouseEvent) => event.stopPropagation()}>
        <DropdownMenuItem onSelect={() => navigate(accountHref(summary.id))}>
          <ExternalLink />
          {t("providers.list.open")}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate("/logs?accountId=" + encodeURIComponent(summary.logsAccountId))}>
          <ScrollText />
          {t("providers.detail.openLogs")}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => void navigator.clipboard.writeText(summary.id)}>
          <Copy />
          {t("providers.detail.copyId")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function AccountRow({
  summary,
  color,
  activity,
  showResetCreditBadges,
}: {
  summary: ProviderSummary;
  color: string | undefined;
  activity: AccountActivity | undefined | null;
  showResetCreditBadges: boolean;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const blurred = usePrivacyStore((s) => s.blurred);
  const href = accountHref(summary.id);
  const codex = summary.entry.kind === "codex" ? summary.entry.account : null;
  const duplicateId = codex?.isEmailDuplicate ? "ID " + formatCompactAccountId(codex.accountId) : null;
  const statusHint = codex && summary.status === "active" ? t("accounts.listItem.statusActiveHint") : undefined;
  const dim = summary.status === "paused";
  const open = () => navigate(href);
  const onKeyDown = (event: KeyboardEvent) => {
    if (event.target === event.currentTarget && event.key === "Enter") open();
  };
  return (
    <div
      role="row"
      data-testid="provider-account-row"
      tabIndex={-1}
      onClick={open}
      onKeyDown={onKeyDown}
      className={cn(ROW_GRID, "cursor-pointer border-b py-2.5 last:border-b-0 hover:bg-accent/60")}
    >
      <div className={cn("flex min-w-0 items-center gap-2.5", dim && "opacity-55")}>
        <ProviderLogo provider={summary.kind} color={color} size="md" />
        <div className="min-w-0">
          <div className="flex min-w-0 items-center gap-1.5">
            <Link
              to={href}
              onClick={(event) => event.stopPropagation()}
              className="min-w-0 truncate text-sm font-semibold hover:underline"
            >
              <span className={cn(summary.blurName && blurred && "privacy-blur")}>{summary.name}</span>
            </Link>
            {summary.plan ? <PlanBadge plan={summary.planKey}>{summary.plan}</PlanBadge> : null}
            {showResetCreditBadges && summary.resetCredits > 0 ? (
              <span
                title={t("accounts.actions.resetWithCount", { count: summary.resetCredits })}
                className="grid h-4 min-w-4 shrink-0 place-items-center rounded-full bg-primary px-1 text-[10px] font-medium text-primary-foreground"
              >
                {summary.resetCredits > 99 ? "99+" : summary.resetCredits}
              </span>
            ) : null}
            {summary.trustedAccess ? (
              <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-emerald-600" aria-label={t("accounts.actions.trustedAccess")} />
            ) : null}
            {summary.entry.kind === "claude" ? <ExtraUsageBadge account={summary.entry.account} /> : null}
          </div>
          {summary.subtitle || duplicateId ? (
            <p className="truncate text-xs text-muted-foreground">
              {summary.subtitle ? <span className={cn(summary.blurSubtitle && blurred && "privacy-blur")}>{summary.subtitle}</span> : null}
              {summary.subtitle && duplicateId ? " · " : null}
              {duplicateId}
            </p>
          ) : null}
        </div>
      </div>
      <div className="col-start-2 row-start-1 min-w-0 justify-self-end lg:col-start-auto lg:row-start-auto lg:justify-self-start">
        <StatusBadge status={summary.status} title={statusHint} />
        {summary.notice ? (
          <span className={cn("mt-0.5 block max-w-48 truncate text-[11px]", noticeClass(summary.notice.tone))} title={summary.notice.text}>
            {summary.notice.text}
          </span>
        ) : null}
      </div>
      {summary.limits.length === 0 ? (
        <span className={cn("col-span-2 text-xs text-muted-foreground", dim && "opacity-55")}>—</span>
      ) : summary.limits.length === 1 ? (
        <LimitMeter limit={summary.limits[0]} className={cn("col-span-2", dim && "opacity-55")} />
      ) : (
        summary.limits.map((limit) => <LimitMeter key={limit.key} limit={limit} className={cn(dim && "opacity-55")} />)
      )}
      <div className="hidden lg:block">
        <TodayCell activity={activity} />
      </div>
      <div className="hidden lg:block">
        <RoutingCell summary={summary} />
      </div>
      <div className="hidden justify-self-end lg:block">
        <RowMenu summary={summary} />
      </div>
    </div>
  );
}

export type ProvidersListProps = {
  groups: ProviderGroup[];
  activity: Map<string, AccountActivity> | undefined;
  activityAvailable: boolean;
  colors: AccountColorHexes;
  sortMode: AccountSortMode;
  onSortModeChange: (mode: AccountSortMode) => void;
  showResetCreditBadges: boolean;
  readOnly: boolean;
  onAdd: () => void;
};

/** Every account, grouped by provider, with its limits, today's activity and routing. */
export function ProvidersList({
  groups,
  activity,
  activityAvailable,
  colors,
  sortMode,
  onSortModeChange,
  showResetCreditBadges,
  readOnly,
  onAdd,
}: ProvidersListProps) {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<ProviderFilter>("all");
  const all = useMemo(() => groups.flatMap((group) => group.summaries), [groups]);
  const counts: Record<ProviderFilter, number> = {
    all: all.length,
    attention: all.filter((summary) => matchesFilter(summary, "attention")).length,
    paused: all.filter((summary) => matchesFilter(summary, "paused")).length,
  };
  const visible = useMemo(() => filterGroups(groups, filter, search), [groups, filter, search]);
  const connected = new Set(groups.map((group) => group.kind));
  const missing = PROVIDER_ORDER.filter((kind) => !connected.has(kind));
  const filters: { value: ProviderFilter; label: string }[] = [
    { value: "all", label: t("providers.filter.all") },
    { value: "attention", label: t("providers.filter.attention") },
    { value: "paused", label: t("providers.filter.paused") },
  ];
  const activityOf = (summary: ProviderSummary) => (activityAvailable ? activity?.get(summary.activityKey) : null);
  return (
    <section data-testid="providers-list" className="min-w-0 overflow-hidden rounded-xl border bg-card shadow-xs">
      <div className="flex flex-wrap items-center gap-2 border-b px-3 py-2.5">
        <div className="relative min-w-0 flex-1 basis-full sm:max-w-72 sm:basis-auto">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60" aria-hidden />
          <Input
            placeholder={t("accounts.list.searchPlaceholder")}
            aria-label={t("accounts.list.searchPlaceholder")}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="h-8 pl-8"
          />
        </div>
        <div role="group" aria-label={t("providers.filter.label")} className="inline-flex gap-0.5 rounded-lg border bg-muted p-0.5">
          {filters.map((option) => (
            <button
              key={option.value}
              type="button"
              aria-pressed={filter === option.value}
              onClick={() => setFilter(option.value)}
              className={cn(
                "inline-flex h-7 items-center gap-1.5 rounded-md px-2.5 text-xs text-muted-foreground transition-colors hover:text-foreground",
                filter === option.value && "bg-card font-medium text-foreground shadow-xs",
              )}
            >
              {option.label}
              <span className="text-[11px] tabular-nums opacity-75">{counts[option.value]}</span>
            </button>
          ))}
        </div>
        <Select value={sortMode} onValueChange={(mode) => onSortModeChange(mode as AccountSortMode)}>
          <SelectTrigger size="sm" className="ml-auto w-56 min-w-0" aria-label={t("accounts.list.sortAria")}>
            <SelectValue placeholder={t("accounts.list.sortPlaceholder")} />
          </SelectTrigger>
          <SelectContent>
            {ACCOUNT_SORT_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {t("accounts.sort." + option.value, { defaultValue: option.label })}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div role="table" aria-label={t("providers.page.title")}>
        <div role="row" className={cn(ROW_GRID, "hidden border-b py-2 text-[11.5px] font-medium text-muted-foreground lg:grid")}>
          <span role="columnheader">{t("providers.list.account")}</span>
          <span role="columnheader">{t("providers.list.status")}</span>
          <span role="columnheader" className="col-span-2">{t("providers.list.limits")}</span>
          <span role="columnheader" className="text-right">{t("providers.list.today")}</span>
          <span role="columnheader">{t("providers.list.routing")}</span>
          <span />
        </div>
        {visible.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="text-sm font-medium text-muted-foreground">
              {all.length === 0 ? t("accounts.list.emptyTitle") : t("accounts.list.noMatches")}
            </p>
            <p className="mt-1 text-xs text-muted-foreground/70">
              {all.length === 0 ? t("accounts.list.emptyDescription") : t("accounts.list.adjustFilters")}
            </p>
          </div>
        ) : (
          visible.map((group) => (
            <div key={group.kind} role="rowgroup" aria-label={PROVIDER_LABELS[group.kind]}>
              <GroupRow kind={group.kind} count={group.summaries.length} readOnly={readOnly} onAdd={onAdd} />
              {group.summaries.map((summary) => (
                <AccountRow
                  key={summary.id}
                  summary={summary}
                  color={summaryColor(summary, colors)}
                  activity={activityOf(summary)}
                  showResetCreditBadges={showResetCreditBadges}
                />
              ))}
            </div>
          ))
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2 border-t px-4 py-2.5 text-xs text-muted-foreground">
        {missing.length > 0 && !readOnly ? (
          <>
            <span>{t("providers.list.notConnected")}</span>
            {missing.map((kind) => (
              <button
                key={kind}
                type="button"
                onClick={onAdd}
                className="inline-flex h-6 items-center gap-1.5 rounded-md border border-dashed px-2 text-xs hover:bg-accent hover:text-foreground"
              >
                <ProviderLogo provider={kind} />
                {PROVIDER_LABELS[kind]}
              </button>
            ))}
          </>
        ) : null}
        {all.some((summary) => summary.kind === "codex") ? (
          <span className="basis-full text-[11px] leading-snug text-muted-foreground/80">{t("accounts.list.statusEligibilityNote")}</span>
        ) : null}
      </div>
    </section>
  );
}

function GroupRow({ kind, count, readOnly, onAdd }: { kind: ProviderKind; count: number; readOnly: boolean; onAdd: () => void }) {
  const { t } = useTranslation();
  const captions = PROVIDER_LIMIT_CAPTIONS[kind];
  return (
    <div role="row" className={cn(ROW_GRID, "border-b bg-muted/60 py-1.5 text-[13px] dark:bg-muted/30")}>
      <div className="flex min-w-0 items-center gap-2">
        <ProviderLogo provider={kind} />
        <b className="font-semibold">{PROVIDER_LABELS[kind]}</b>
        <span className="text-xs text-muted-foreground">{count}</span>
      </div>
      <span className="hidden lg:block" />
      {captions ? (
        captions.map((caption) => (
          <span key={caption} className="hidden text-[11.5px] text-muted-foreground lg:block">
            {caption}
          </span>
        ))
      ) : (
        <span className="hidden lg:col-span-2 lg:block" />
      )}
      <span className="hidden lg:block" />
      <span className="hidden lg:block" />
      <div className="justify-self-end">
        {readOnly ? null : (
          <Button
            type="button"
            size="icon-xs"
            variant="ghost"
            aria-label={t("providers.list.addTo", { provider: PROVIDER_LABELS[kind] })}
            onClick={onAdd}
          >
            <Plus className="size-3.5" />
          </Button>
        )}
      </div>
    </div>
  );
}
