import { Fragment, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ProviderLogo } from "@/components/brand/provider-account-name";
import { ChartToggle } from "@/components/chart-toggle";
import type { AccountSubscriptionEnd } from "@/features/accounts/account-subscriptions";
import {
  accountHref,
  PROVIDER_LABELS,
  toneDotClass,
  type ProviderSummary,
  type SummaryTone,
} from "@/features/accounts/provider-summary";
import { FAMILY_LABELS } from "@/features/antigravity/display-values";
import { SectionHeader } from "@/features/dashboard/components/section-header";
import {
  buildUpcomingEvents,
  isEstimate,
  UPCOMING_HORIZON_MS,
  type UpcomingEvent,
  type UpcomingKind,
  type UpcomingPool,
} from "@/features/dashboard/upcoming-events";
import { formatUnitAmount } from "@/features/dashboard/utils";
import { UPCOMING_HORIZONS, useDashboardPreferencesStore } from "@/hooks/use-dashboard-preferences";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import { formatDateTimeInline, formatQuotaResetLabel, formatShortTime, formatWeekdayDate } from "@/utils/formatters";

/** Rows shown before "Show all". */
const COLLAPSED_ROWS = 8;
/** Account names a row lists before "+N more". */
const NAMED_ACCOUNTS = 3;
const DAY_MS = 86_400_000;

/** Rows under one day heading; the 24h horizon has a single group without a heading. */
type DayGroup = { day: number | null; events: UpcomingEvent[] };

const KIND_TONE: Record<UpcomingKind, SummaryTone> = {
  back: "ok",
  reset: "ok",
  refill: "ok",
  runsDry: "bad",
  lapse: "warn",
  subscriptionEnd: "warn",
};

function formatShare(percent: number): string {
  const rounded = Math.round(percent);
  return rounded < 1 ? "<1%" : `${rounded}%`;
}

function startOfDay(epochMs: number): number {
  const date = new Date(epochMs);
  date.setHours(0, 0, 0, 0);
  return date.getTime();
}

function AccountNames({ accounts }: { accounts: ProviderSummary[] }) {
  const { t } = useTranslation();
  const blurred = usePrivacyStore((s) => s.blurred);
  const named = accounts.slice(0, NAMED_ACCOUNTS);
  return (
    <>
      {named.map((summary, index) => (
        <Fragment key={summary.kind + ":" + summary.id}>
          {index > 0 ? ", " : null}
          <Link
            to={accountHref(summary.id)}
            title={t("dashboard.accounts.open", { name: summary.name })}
            className={cn("font-medium hover:underline", summary.blurName && blurred && "privacy-blur")}
          >
            {summary.name}
          </Link>
        </Fragment>
      ))}
      {accounts.length > named.length ? " " + t("dashboard.upcoming.moreAccounts", { count: accounts.length - named.length }) : null}
    </>
  );
}

function predicate(event: UpcomingEvent, t: ReturnType<typeof useTranslation>["t"]): string {
  switch (event.kind) {
    case "back":
      return event.window ? t("dashboard.upcoming.event.backWindow", { window: event.window }) : t("dashboard.upcoming.event.back");
    case "reset":
      return event.window ? t("dashboard.upcoming.event.resetWindow", { window: event.window }) : t("dashboard.upcoming.event.reset");
    case "refill":
      return t("dashboard.upcoming.event.refill", { window: event.window, percent: formatShare(event.percentLeft ?? 0) });
    case "runsDry":
      return t("dashboard.upcoming.event.runsDry");
    case "lapse":
      return t("dashboard.upcoming.event.lapse");
    case "subscriptionEnd":
      return t("dashboard.upcoming.event.subscriptionEnd");
  }
}

function Impact({ event }: { event: UpcomingEvent }) {
  const { t } = useTranslation();
  const amount = event.amount ? formatUnitAmount(event.amount.value, event.amount.unit) : null;
  const [primary, secondary] =
    event.kind === "refill"
      ? [t("dashboard.upcoming.impact.refill", { percent: formatShare(event.percentLeft ?? 0) }), null]
      : amount === null
        ? [null, null]
        : event.kind === "subscriptionEnd"
          ? [t("dashboard.upcoming.impact.loss", { amount }), t("dashboard.upcoming.impact.perWeek")]
          : event.kind === "lapse"
            ? [`~${amount}`, t("dashboard.upcoming.impact.unspent")]
            : [
                t("dashboard.upcoming.impact.gain", { amount }),
                event.poolPercent === null ? null : t("dashboard.upcoming.impact.poolShare", { percent: formatShare(event.poolPercent) }),
              ];
  if (primary === null) return <span />;
  return (
    <span className="text-right text-xs tabular-nums">
      <span className="block font-medium">{primary}</span>
      {secondary ? <span className="block text-muted-foreground">{secondary}</span> : null}
    </span>
  );
}

function EventRow({ event, now }: { event: UpcomingEvent; now: number }) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  const estimate = isEstimate(event);
  const iso = new Date(event.at).toISOString();
  const pool = PROVIDER_LABELS[event.provider] + (event.family ? ` · ${FAMILY_LABELS[event.family]}` : "");
  return (
    <li className="grid grid-cols-[4.75rem_minmax(0,1fr)_auto] items-center gap-3 px-4 py-2" data-testid="upcoming-event">
      <span className="tabular-nums" title={formatDateTimeInline(iso, dateDisplayFormat)}>
        <span className="block text-sm font-medium">
          {estimate ? <span title={t("dashboard.upcoming.estimate")}>~</span> : null}
          {formatShortTime(event.at, dateDisplayFormat)}
        </span>
        <span className="block text-[11px] text-muted-foreground">
          {formatQuotaResetLabel(iso, now, event.kind === "subscriptionEnd" ? "expiry" : "cooldown")}
        </span>
      </span>
      <span className="flex min-w-0 items-center gap-2 text-sm">
        <span aria-hidden="true" className={cn("size-2 shrink-0 rounded-full", toneDotClass(KIND_TONE[event.kind]))} />
        <ProviderLogo provider={event.provider} />
        <span className="min-w-0">
          {event.accounts.length > 0 ? (
            <AccountNames accounts={event.accounts} />
          ) : (
            <span className="font-medium">{t("dashboard.upcoming.pool", { pool })}</span>
          )}{" "}
          <span className="text-muted-foreground">{predicate(event, t)}</span>
        </span>
      </span>
      <Impact event={event} />
    </li>
  );
}

export type UpcomingEventsSectionProps = {
  summaries: ProviderSummary[];
  subscriptionEnds: AccountSubscriptionEnd[] | undefined;
  pools: UpcomingPool[];
};

/** "Coming up": the next moments that change Codex, Claude or Antigravity capacity. */
export function UpcomingEventsSection({ summaries, subscriptionEnds, pools }: UpcomingEventsSectionProps) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  const horizon = useDashboardPreferencesStore((s) => s.upcomingHorizon);
  const setHorizon = useDashboardPreferencesStore((s) => s.setUpcomingHorizon);
  const [expanded, setExpanded] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(timer);
  }, []);
  const events = useMemo(
    () => buildUpcomingEvents({ summaries, subscriptionEnds, pools, now, horizonMs: UPCOMING_HORIZON_MS[horizon] }),
    [summaries, subscriptionEnds, pools, now, horizon],
  );
  const visible = expanded ? events : events.slice(0, COLLAPSED_ROWS);
  const days: DayGroup[] =
    horizon === "7d"
      ? visible.reduce<DayGroup[]>((groups, event) => {
          const day = startOfDay(event.at);
          const last = groups.at(-1);
          if (last?.day === day) last.events.push(event);
          else groups.push({ day, events: [event] });
          return groups;
        }, [])
      : [{ day: null, events: visible }];
  const today = startOfDay(now);
  const dayLabel = (day: number) => {
    const offset = Math.round((day - today) / DAY_MS);
    if (offset === 0) return t("dashboard.upcoming.today");
    if (offset === 1) return t("dashboard.upcoming.tomorrow");
    return formatWeekdayDate(day, dateDisplayFormat);
  };

  return (
    <section className="flex flex-col gap-2.5" data-testid="upcoming-section">
      <SectionHeader
        title={t("dashboard.upcoming.title")}
        hint={events.length > 0 ? t(`dashboard.upcoming.hint.${horizon}`, { count: events.length }) : undefined}
      >
        <ChartToggle
          label={t("dashboard.upcoming.horizon")}
          value={horizon}
          onChange={setHorizon}
          options={UPCOMING_HORIZONS.map((value) => ({ value, label: value }))}
        />
      </SectionHeader>
      <div className="rounded-xl border bg-card py-1">
        {events.length === 0 ? (
          <p className="px-4 py-2.5 text-sm text-muted-foreground">{t(`dashboard.upcoming.empty.${horizon}`)}</p>
        ) : (
          days.map((group) => (
            <Fragment key={group.day ?? "all"}>
              {group.day !== null ? (
                <h3 className="px-4 pt-2.5 pb-1 text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
                  {dayLabel(group.day)}
                </h3>
              ) : null}
              <ol className="divide-y divide-border/60">
                {group.events.map((event) => (
                  <EventRow key={`${event.kind}:${event.provider}:${event.family}:${event.window}:${event.at}`} event={event} now={now} />
                ))}
              </ol>
            </Fragment>
          ))
        )}
        {events.length > COLLAPSED_ROWS ? (
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="mx-4 my-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
          >
            {expanded ? t("dashboard.upcoming.showLess") : t("dashboard.upcoming.showAll", { count: events.length })}
          </button>
        ) : null}
      </div>
    </section>
  );
}
