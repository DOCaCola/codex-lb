import { Fragment, useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { ProviderSummary } from "@/features/accounts/provider-summary";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import { formatDateTimeInline, formatResetCountdown, parseDate } from "@/utils/formatters";

type Upcoming = { summary: ProviderSummary; at: string };

/** The earliest future time among candidates. */
function earliest(candidates: Upcoming[], now: number): Upcoming | null {
  return candidates
    .filter((candidate) => (parseDate(candidate.at)?.getTime() ?? 0) > now)
    .reduce<Upcoming | null>((best, candidate) => (best === null || Date.parse(candidate.at) < Date.parse(best.at) ? candidate : best), null);
}

function Names({ summaries }: { summaries: ProviderSummary[] }) {
  const blurred = usePrivacyStore((s) => s.blurred);
  return summaries.map((summary, index) => (
    <Fragment key={summary.kind + ":" + summary.id}>
      {index > 0 ? ", " : null}
      <span className={cn(summary.blurName && blurred && "privacy-blur")}>{summary.name}</span>
    </Fragment>
  ));
}

/**
 * One sentence of account health under the page title: how many accounts can
 * take work, which cannot and until when, and the next 5-hour reset.
 */
export function DashboardStatusLine({ summaries }: { summaries: ProviderSummary[] }) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(timer);
  }, []);
  if (summaries.length === 0) return null;
  const ready = summaries.filter((summary) => summary.status === "active");
  const limited = summaries.filter((summary) => summary.status === "limited" || summary.status === "exceeded");
  const paused = summaries.filter((summary) => summary.status === "paused");
  const signIn = summaries.filter((summary) => summary.status === "reauth" || summary.status === "deactivated");
  const firstBack = earliest(
    limited.flatMap((summary) =>
      summary.limits.filter((limit) => limit.percentLeft === 0 && limit.resetAt).map((limit) => ({ summary, at: limit.resetAt as string })),
    ),
    now,
  );
  const nextFiveHour = earliest(
    summaries.flatMap((summary) =>
      summary.limits
        .filter((limit) => limit.key === "5h" && limit.resetAt && limit.percentLeft !== null && limit.percentLeft < 100)
        .map((limit) => ({ summary, at: limit.resetAt as string })),
    ),
    now,
  );
  const timeTitle = (at: string) => formatDateTimeInline(at, dateDisplayFormat);

  const parts: ReactNode[] = [
    <span key="ready">{t("providers.page.ready", { ready: ready.length, total: summaries.length })}</span>,
  ];
  if (limited.length > 0) {
    parts.push(
      <span key="limited" className="text-destructive">
        <Names summaries={limited} /> {t("dashboard.status.limited")}
        {firstBack ? (
          <span title={timeTitle(firstBack.at)}> · {t("dashboard.status.firstBack", { countdown: formatResetCountdown(firstBack.at) })}</span>
        ) : null}
      </span>,
    );
  }
  if (paused.length > 0) {
    parts.push(
      <span key="paused">
        <Names summaries={paused} /> {t("dashboard.status.paused")}
      </span>,
    );
  }
  if (signIn.length > 0) {
    parts.push(
      <span key="sign-in" className="text-destructive">
        <Names summaries={signIn} /> {t("dashboard.status.signIn", { count: signIn.length })}
      </span>,
    );
  }
  if (nextFiveHour) {
    parts.push(
      <span key="next" title={timeTitle(nextFiveHour.at)}>
        {t("dashboard.status.nextFiveHourReset")} <b className="font-medium text-foreground">{formatResetCountdown(nextFiveHour.at)}</b> (
        <Names summaries={[nextFiveHour.summary]} />)
      </span>,
    );
  }
  return (
    <p data-testid="dashboard-status-line" className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[13px] text-muted-foreground">
      {parts.map((part, index) => (
        <Fragment key={index}>
          {index > 0 ? <span aria-hidden>·</span> : null}
          {part}
        </Fragment>
      ))}
    </p>
  );
}
