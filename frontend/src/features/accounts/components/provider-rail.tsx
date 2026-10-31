import { ArrowLeft, PanelLeftClose, PanelLeftOpen, Search } from "lucide-react";
import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { ProviderLogo } from "@/components/brand/provider-account-name";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AccountColorHexes } from "@/features/accounts/account-colors";
import { LimitBar } from "@/features/accounts/components/providers-list";
import { useDetailTab, type DetailTab } from "@/features/accounts/hooks/use-detail-tab";
import {
  PROVIDER_LABELS,
  accountHref,
  filterGroups,
  noticeClass,
  summaryColor,
  type LimitSummary,
  type ProviderGroup,
  type ProviderSummary,
  type SummaryTone,
} from "@/features/accounts/provider-summary";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import { formatQuotaResetLabel } from "@/utils/formatters";

const DOT: Record<SummaryTone, string> = {
  ok: "bg-emerald-500",
  warn: "bg-amber-500",
  bad: "bg-destructive",
  off: "bg-muted-foreground",
};

function RailLimit({ limit }: { limit: LimitSummary | undefined }) {
  // An empty slot keeps every entry the same height.
  if (!limit) return <div aria-hidden="true" className="h-3.5" />;
  return (
    <div className="flex h-3.5 min-w-0 items-center gap-1.5 text-[10.5px]">
      <span className="w-9 shrink-0 truncate text-muted-foreground">{limit.short}</span>
      <LimitBar limit={limit} className="h-[3px] flex-1" />
      <span className={cn("w-9 shrink-0 text-right tabular-nums", limit.percentLeft === 0 && "text-destructive")}>{limit.value}</span>
      <span className="w-14 shrink-0 truncate text-right text-muted-foreground tabular-nums">
        {limit.resetAt ? formatQuotaResetLabel(limit.resetAt) : limit.caption}
      </span>
    </div>
  );
}

function RailEntry({
  summary,
  color,
  selected,
  collapsed,
  tab,
}: {
  summary: ProviderSummary;
  color: string | undefined;
  selected: boolean;
  collapsed: boolean;
  tab: DetailTab;
}) {
  const { t } = useTranslation();
  const blurred = usePrivacyStore((s) => s.blurred);
  const accent = color ?? "var(--muted-foreground)";
  const stateText = summary.notice?.text ?? t("common.status." + summary.status, { defaultValue: summary.status });
  return (
    <Link
      to={accountHref(summary.id, tab)}
      data-rail-id={summary.id}
      aria-current={selected ? "page" : undefined}
      title={collapsed ? summary.name : undefined}
      className={cn(
        "relative flex items-start gap-2.5 border-b py-2.5 pr-3 pl-4 outline-none last:border-b-0 hover:bg-muted/50 focus-visible:bg-muted/50",
        collapsed && "justify-center px-0",
        selected && "bg-primary/8 ring-1 ring-primary/25 ring-inset hover:bg-primary/8 focus-visible:bg-primary/8",
      )}
    >
      <span aria-hidden="true" className="absolute inset-y-2.5 left-0 w-[3px] rounded-r-[3px]" style={{ backgroundColor: accent }} />
      <span className={cn("relative mt-0.5 flex shrink-0", summary.status === "paused" && "opacity-55")}>
        <ProviderLogo provider={summary.kind} color={color} size="md" />
        <span aria-hidden="true" className={cn("absolute -right-1 -bottom-1 size-2 rounded-full border-[1.5px] border-card", DOT[summary.tone])} />
      </span>
      {collapsed ? null : (
        <span className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="flex min-w-0 items-center gap-1.5">
            <span className={cn("min-w-0 truncate text-[13px] font-semibold", summary.status === "paused" && "opacity-55")}>
              <span className={cn(summary.blurName && blurred && "privacy-blur")}>{summary.name}</span>
            </span>
            {summary.plan ? (
              <span className="shrink-0 rounded border px-1 text-[9.5px] font-semibold tracking-wide text-muted-foreground uppercase">
                {summary.plan}
              </span>
            ) : null}
          </span>
          <span className={cn("flex flex-col gap-0.5", summary.status === "paused" && "opacity-55")}>
            <RailLimit limit={summary.limits[0]} />
            <RailLimit limit={summary.limits[1]} />
          </span>
          <span className="flex min-w-0 gap-2 text-[11px] whitespace-nowrap text-muted-foreground">
            <span className={cn("min-w-0 truncate", summary.notice && summary.notice.tone !== "off" && "font-medium", noticeClass(summary.notice?.tone ?? "ok"))}>
              {stateText}
            </span>
            {summary.routingPolicy && summary.routingPolicy !== "normal" ? (
              <span className="ml-auto shrink-0">
                {t(summary.routingPolicy === "burn_first" ? "common.routingPolicies.burnFirst" : "common.routingPolicies.preserve")}
              </span>
            ) : null}
          </span>
        </span>
      )}
    </Link>
  );
}

/** Quick navigation between accounts beside an open account page. */
export function ProviderRail({
  groups,
  selectedId,
  colors,
  collapsed,
  onToggleCollapsed,
}: {
  groups: ProviderGroup[];
  selectedId: string;
  colors: AccountColorHexes;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const tab = useDetailTab();
  const listRef = useRef<HTMLDivElement>(null);
  const [search, setSearch] = useState("");
  const visible = useMemo(() => filterGroups(groups, "all", collapsed ? "" : search), [groups, search, collapsed]);
  const order = visible.flatMap((group) => group.summaries.map((summary) => summary.id));
  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const index = order.indexOf(selectedId);
    const next = order[Math.min(order.length - 1, Math.max(0, index + (event.key === "ArrowDown" ? 1 : -1)))];
    if (!next || next === selectedId) return;
    navigate(accountHref(next, tab));
    requestAnimationFrame(() => listRef.current?.querySelector<HTMLElement>("[data-rail-id=\"" + CSS.escape(next) + "\"]")?.focus());
  };
  return (
    <nav
      aria-label={t("providers.rail.label")}
      data-testid="provider-rail"
      className={cn(
        // Height leaves room for the breadcrumb above the unscrolled rail and the fixed status bar below it.
        "sticky top-[4.5rem] hidden max-h-[calc(100dvh-11rem)] min-w-0 flex-col overflow-hidden rounded-xl border bg-card shadow-xs lg:flex",
      )}
    >
      <div className={cn("flex items-center gap-1.5 px-3 pt-2.5 pb-1.5", collapsed && "justify-center px-0")}>
        {collapsed ? null : (
          <Link to="/providers" className="flex flex-1 items-center gap-1.5 text-[12.5px] whitespace-nowrap text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" />
            {t("providers.rail.all")}
          </Link>
        )}
        <Button
          type="button"
          size="icon-xs"
          variant="ghost"
          aria-label={t(collapsed ? "providers.rail.expand" : "providers.rail.collapse")}
          aria-expanded={!collapsed}
          onClick={onToggleCollapsed}
        >
          {collapsed ? <PanelLeftOpen className="size-3.5" /> : <PanelLeftClose className="size-3.5" />}
        </Button>
      </div>
      {collapsed ? null : (
        <div className="relative mx-2.5 mb-2">
          <Search className="pointer-events-none absolute top-1/2 left-2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60" aria-hidden />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("providers.rail.find")}
            aria-label={t("providers.rail.find")}
            className="h-7 pl-7 text-xs"
          />
        </div>
      )}
      <div ref={listRef} onKeyDown={onKeyDown} data-testid="provider-rail-scroll" className="min-h-0 flex-1 overflow-y-auto border-t">
        {visible.map((group) => {
          const ready = group.summaries.filter((summary) => summary.tone === "ok").length;
          return (
            <div key={group.kind}>
              <div
                className={cn(
                  "flex items-center gap-1.5 border-b bg-muted/60 px-3 py-1.5 text-[11.5px] font-semibold text-muted-foreground dark:bg-muted/30",
                  collapsed && "justify-center px-0",
                )}
                title={collapsed ? PROVIDER_LABELS[group.kind] : undefined}
              >
                <ProviderLogo provider={group.kind} />
                {collapsed ? null : (
                  <>
                    <span>{PROVIDER_LABELS[group.kind]}</span>
                    <span className="ml-auto font-normal">{t("providers.rail.ready", { ready, total: group.summaries.length })}</span>
                  </>
                )}
              </div>
              {group.summaries.map((summary) => (
                <RailEntry
                  key={summary.id}
                  summary={summary}
                  color={summaryColor(summary, colors)}
                  selected={summary.id === selectedId}
                  collapsed={collapsed}
                  tab={tab}
                />
              ))}
            </div>
          );
        })}
        {visible.length === 0 ? <p className="px-3 py-6 text-center text-xs text-muted-foreground">{t("accounts.list.noMatches")}</p> : null}
      </div>
    </nav>
  );
}
