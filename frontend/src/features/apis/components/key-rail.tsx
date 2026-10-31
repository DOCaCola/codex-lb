import { ArrowLeft, KeyRound, PanelLeftClose, PanelLeftOpen, Search } from "lucide-react";
import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ApiKey } from "@/features/api-keys/schemas";
import { LimitTrack } from "@/features/apis/components/key-parts";
import {
  KEY_DOT,
  KEY_TEXT,
  KEY_TONE,
  formatLastUsed,
  keyHref,
  keySeriesId,
  keyState,
  keyStateDetail,
  limitName,
  limitPercent,
  matchesKeySearch,
  useKeyTab,
  type KeyColors,
  type KeyTab,
  type KeyWeek,
} from "@/features/apis/key-summary";
import { formatCoveredCostShort } from "@/features/dashboard/cost-coverage";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/utils/formatters";

function RailEntry({
  apiKey,
  color,
  week,
  selected,
  collapsed,
  tab,
}: {
  apiKey: ApiKey;
  color: string | undefined;
  week: KeyWeek | undefined;
  selected: boolean;
  collapsed: boolean;
  tab: KeyTab;
}) {
  const { t } = useTranslation();
  const state = keyState(apiKey);
  const tone = KEY_TONE[state];
  const dim = state === "disabled" || state === "expired";
  const limit = apiKey.limits[0];
  const percent = limit ? limitPercent(limit) : 0;
  const detail = keyStateDetail(apiKey, state, t);
  return (
    <Link
      to={keyHref(apiKey.id, tab)}
      data-rail-id={apiKey.id}
      aria-current={selected ? "page" : undefined}
      title={collapsed ? apiKey.name : undefined}
      className={cn(
        "relative flex items-start gap-2.5 border-b py-2.5 pr-3 pl-4 outline-none last:border-b-0 hover:bg-muted/50 focus-visible:bg-muted/50",
        collapsed && "justify-center px-0",
        selected && "bg-primary/8 ring-1 ring-primary/25 ring-inset hover:bg-primary/8 focus-visible:bg-primary/8",
      )}
    >
      <span aria-hidden="true" className="absolute inset-y-2.5 left-0 w-[3px] rounded-r-[3px]" style={{ backgroundColor: color }} />
      <span className={cn("relative mt-0.5 flex shrink-0", dim && "opacity-55")}>
        <KeyRound className="size-4" style={{ color }} aria-hidden="true" />
        <span aria-hidden="true" className={cn("absolute -right-1 -bottom-1 size-2 rounded-full border-[1.5px] border-card", KEY_DOT[tone])} />
      </span>
      {collapsed ? null : (
        <span className="flex min-w-0 flex-1 flex-col gap-1">
          <span className={cn("flex min-w-0 items-center gap-1.5", dim && "opacity-55")}>
            <span className="min-w-0 truncate text-[13px] font-semibold">{apiKey.name}</span>
            <span className="shrink-0 font-mono text-[10px] text-muted-foreground">{apiKey.keyPrefix}</span>
            <span className="ml-auto shrink-0 text-[11px] tabular-nums text-muted-foreground">
              {week ? formatCoveredCostShort(week.costUsd, week.coverage) : formatCurrency(0)}
            </span>
          </span>
          {/* An empty slot keeps every entry the same height. */}
          {limit ? (
            <span className={cn("flex h-3.5 min-w-0 items-center gap-1.5 text-[10.5px]", dim && "opacity-55")}>
              <span className="w-24 shrink-0 truncate text-muted-foreground">{limitName(limit, t)}</span>
              <LimitTrack percent={percent} color={color} className="h-[3px] flex-1" />
              <span className={cn("w-9 shrink-0 text-right tabular-nums", percent >= 100 && "text-destructive")}>
                {Math.round(percent)}%
              </span>
            </span>
          ) : (
            <span aria-hidden="true" className="h-3.5" />
          )}
          <span className="flex min-w-0 gap-2 text-[11px] whitespace-nowrap text-muted-foreground">
            <span className={cn("min-w-0 truncate", tone !== "ok" && tone !== "off" && "font-medium", KEY_TEXT[tone])}>
              {t("apis.state." + state)}
              {detail ? " · " + detail : null}
            </span>
            <span className="ml-auto shrink-0">{formatLastUsed(apiKey, t)}</span>
          </span>
        </span>
      )}
    </Link>
  );
}

/** Quick navigation between keys beside an open key page. */
export function KeyRail({
  apiKeys,
  selectedId,
  colors,
  weeks,
  collapsed,
  onToggleCollapsed,
}: {
  apiKeys: ApiKey[];
  selectedId: string;
  colors: KeyColors;
  weeks: Map<string, KeyWeek>;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const tab = useKeyTab();
  const listRef = useRef<HTMLDivElement>(null);
  const [search, setSearch] = useState("");
  const visible = useMemo(
    () => (collapsed ? apiKeys : apiKeys.filter((apiKey) => matchesKeySearch(apiKey, search))),
    [apiKeys, search, collapsed],
  );
  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const index = visible.findIndex((apiKey) => apiKey.id === selectedId);
    const next = visible[Math.min(visible.length - 1, Math.max(0, index + (event.key === "ArrowDown" ? 1 : -1)))];
    if (!next || next.id === selectedId) return;
    navigate(keyHref(next.id, tab));
    requestAnimationFrame(() =>
      listRef.current?.querySelector<HTMLElement>("[data-rail-id=\"" + CSS.escape(next.id) + "\"]")?.focus(),
    );
  };
  return (
    <nav
      aria-label={t("apis.rail.label")}
      data-testid="api-key-rail"
      className="sticky top-[4.5rem] hidden max-h-[calc(100dvh-11rem)] min-w-0 flex-col overflow-hidden rounded-xl border bg-card shadow-xs lg:flex"
    >
      <div className={cn("flex items-center gap-1.5 px-3 pt-2.5 pb-1.5", collapsed && "justify-center px-0")}>
        {collapsed ? null : (
          <Link to="/keys" className="flex flex-1 items-center gap-1.5 text-[12.5px] whitespace-nowrap text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" />
            {t("apis.rail.all")}
          </Link>
        )}
        <Button
          type="button"
          size="icon-xs"
          variant="ghost"
          aria-label={t(collapsed ? "apis.rail.expand" : "apis.rail.collapse")}
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
            placeholder={t("apis.rail.find")}
            aria-label={t("apis.rail.find")}
            className="h-7 pl-7 text-xs"
          />
        </div>
      )}
      <div ref={listRef} onKeyDown={onKeyDown} className="min-h-0 flex-1 overflow-y-auto border-t">
        {visible.map((apiKey) => (
          <RailEntry
            key={apiKey.id}
            apiKey={apiKey}
            color={colors.get(keySeriesId(apiKey.id))}
            week={weeks.get(apiKey.id)}
            selected={apiKey.id === selectedId}
            collapsed={collapsed}
            tab={tab}
          />
        ))}
        {visible.length === 0 ? <p className="px-3 py-6 text-center text-xs text-muted-foreground">{t("apis.list.noMatches")}</p> : null}
      </div>
    </nav>
  );
}
