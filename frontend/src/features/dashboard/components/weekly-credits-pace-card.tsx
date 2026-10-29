import { Gauge } from "lucide-react";
import { Fragment } from "react";
import { useTranslation } from "react-i18next";

import {
  formatProUnits,
  type WeeklyCreditPace,
  type WeeklyCreditPaceUnit,
  type WeeklyCreditRunwayStatus,
} from "@/features/dashboard/utils";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { cn } from "@/lib/utils";
import { formatCompactNumber, formatDateTimeInline } from "@/utils/formatters";

type Translate = ReturnType<typeof useTranslation>["t"];

/** One independently limited pool shown under the main pace, e.g. an Antigravity model family. */
export type PaceBreakdownRow = {
  key: string;
  label: string;
  pace: WeeklyCreditPace;
  /** The pool the card's runway and schedule describe. */
  emphasized: boolean;
};

export type WeeklyCreditsPaceCardProps = {
  pace: WeeklyCreditPace | null;
  subtitle: string;
  breakdown?: PaceBreakdownRow[];
};

function formatUnitValue(value: number, unit: WeeklyCreditPaceUnit): string {
  return unit === "credits" ? formatCompactNumber(value) : formatProUnits(value);
}

function formatUnitAmount(value: number, unit: WeeklyCreditPaceUnit, t: Translate): string {
  return t(`dashboard.weeklyPace.amount.${unit}`, { value: formatUnitValue(value, unit) });
}

function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

function formatSignedPercent(value: number): string {
  return `${Math.round(Math.abs(value))}%`;
}

function formatHeadroomPercent(value: number): string {
  const clamped = Math.max(0, value);
  return clamped > 0 && clamped < 10 ? `${clamped.toFixed(1)}%` : `${Math.round(clamped)}%`;
}

function statusLabel(pace: WeeklyCreditPace, t: ReturnType<typeof useTranslation>["t"]): string {
  const deltaPercent = pace.smoothedDeltaPercent ?? pace.deltaPercent;
  if (pace.status === "on_track") return t("dashboard.weeklyPace.status.onPace");
  if (pace.status === "danger" && pace.projectedShortfallCredits > 0 && deltaPercent <= 0) {
    return t("dashboard.weeklyPace.status.recentBurnShortfall");
  }
  return deltaPercent > 0
    ? t("dashboard.weeklyPace.status.overPlanned", { percent: formatSignedPercent(deltaPercent) })
    : t("dashboard.weeklyPace.status.belowPlanned", { percent: formatSignedPercent(deltaPercent) });
}

function scheduleGapLine(pace: WeeklyCreditPace, t: ReturnType<typeof useTranslation>["t"]): string {
  const scheduleGapCredits = pace.smoothedScheduleGapCredits ?? pace.scheduleGapCredits;
  const deltaPercent = pace.smoothedDeltaPercent ?? pace.deltaPercent;
  const smoothingMinutes = pace.paceGapSmoothingMinutes ?? 0;
  const window = smoothingMinutes > 0 ? formatDurationHours(smoothingMinutes / 60, t) : null;
  if (scheduleGapCredits > 0) {
    const amount = formatUnitAmount(scheduleGapCredits, pace.unit, t);
    return window
      ? t("dashboard.weeklyPace.lines.overPlannedWindow", { amount, window })
      : t("dashboard.weeklyPace.lines.overPlannedNow", { amount });
  }
  if (deltaPercent < 0) {
    return window
      ? t("dashboard.weeklyPace.lines.belowPlannedWindow", { percent: formatSignedPercent(deltaPercent), window })
      : t("dashboard.weeklyPace.lines.belowPlannedNow", { percent: formatSignedPercent(deltaPercent) });
  }
  return t("dashboard.weeklyPace.lines.onSchedule");
}

function forecastLine(pace: WeeklyCreditPace, t: ReturnType<typeof useTranslation>["t"]): string {
  if (pace.projectedShortfallCredits > 0) {
    return t("dashboard.weeklyPace.lines.projectedShortfall", {
      credits: formatCompactNumber(pace.projectedShortfallCredits),
    });
  }
  if (pace.forecastBurnRateCreditsPerHour === 0) {
    return t("dashboard.weeklyPace.lines.noShortfall");
  }
  if (pace.projectedMinimumRemainingCredits != null) {
    return t("dashboard.weeklyPace.lines.lowWaterMark", {
      credits: formatCompactNumber(pace.projectedMinimumRemainingCredits),
    });
  }
  return t("dashboard.weeklyPace.lines.poolCoversPace");
}

function formatDurationHours(hours: number, t: ReturnType<typeof useTranslation>["t"]): string {
  const totalMinutes = Math.max(1, Math.ceil(hours * 60));
  const days = Math.floor(totalMinutes / 1440);
  const hoursPart = Math.floor((totalMinutes % 1440) / 60);
  const minutesPart = totalMinutes % 60;

  if (days > 0) {
    return hoursPart > 0
      ? t("formatters.duration.daysHours", { days, hours: hoursPart })
      : t("formatters.duration.days", { count: days });
  }
  if (hoursPart > 0) {
    return minutesPart > 0
      ? t("formatters.duration.hoursMinutes", { hours: hoursPart, minutes: minutesPart })
      : t("formatters.duration.hours", { count: hoursPart });
  }
  return t("formatters.duration.minutes", { count: minutesPart });
}

const VERDICT_LABEL_KEYS: Record<WeeklyCreditRunwayStatus, string> = {
  safe: "dashboard.weeklyPace.verdict.safe",
  tight: "dashboard.weeklyPace.verdict.tight",
  runs_dry: "dashboard.weeklyPace.verdict.runsDry",
};

const VERDICT_BADGE_CLASSES: Record<WeeklyCreditRunwayStatus, string> = {
  safe: "border-border bg-muted/40 text-muted-foreground",
  tight: "border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  runs_dry: "border-red-500/25 bg-red-500/10 text-red-700 dark:text-red-300",
};

const VERDICT_FILL_CLASSES: Record<WeeklyCreditRunwayStatus, string> = {
  safe: "bg-primary/50",
  tight: "bg-amber-500/60",
  runs_dry: "bg-red-500/60",
};

const VERDICT_MARKER_CLASSES: Record<WeeklyCreditRunwayStatus, string> = {
  safe: "bg-primary",
  tight: "bg-amber-500",
  runs_dry: "bg-red-500",
};

const TIMELINE_MIN_HORIZON_HOURS = 48;

type RunwayTick = {
  leftPercent: number;
  creditsReturned: number;
  atLabel: string;
};

type RunwayTimeline = {
  etaAtLabel: string | null;
  horizonHours: number;
  etaPercent: number | null;
  resetTicks: RunwayTick[];
};

function buildRunwayTimeline(
  etaHours: number | null,
  reliefHours: number | null,
  resetEvents: WeeklyCreditPace["resetEvents"],
  formatAbsolute: (epochMs: number) => string,
): RunwayTimeline {
  const nowMs = Date.now();
  // A tiny positive burn rate can push the ETA past the representable Date
  // range; formatting would throw, so the absolute label is skipped instead.
  const etaDate = etaHours != null ? new Date(nowMs + etaHours * 3_600_000) : null;
  const etaAtLabel = etaDate != null && Number.isFinite(etaDate.getTime()) ? formatAbsolute(etaDate.getTime()) : null;
  const upcomingResets = (resetEvents ?? []).flatMap((event): { hoursFromNow: number; atMs: number; creditsReturned: number }[] => {
    const atMs = Date.parse(event.at);
    if (!Number.isFinite(atMs)) {
      return [];
    }
    const hoursFromNow = (atMs - nowMs) / 3_600_000;
    return hoursFromNow < 0 ? [] : [{ hoursFromNow, atMs, creditsReturned: event.creditsReturned }];
  });
  // The horizon stretches to the latest reset event so later relief from the
  // backend's seven-day event window is never silently dropped off the rail.
  const horizonHours = Math.max(
    etaHours ?? 0,
    reliefHours ?? 0,
    ...upcomingResets.map((event) => event.hoursFromNow),
    TIMELINE_MIN_HORIZON_HOURS,
  );
  const etaPercent = etaHours != null ? Math.min(100, Math.max(0, (etaHours / horizonHours) * 100)) : null;
  const resetTicks = upcomingResets.map(
    (event): RunwayTick => ({
      leftPercent: Math.min(100, (event.hoursFromNow / horizonHours) * 100),
      creditsReturned: event.creditsReturned,
      atLabel: formatAbsolute(event.atMs),
    }),
  );
  return { etaAtLabel, horizonHours, etaPercent, resetTicks };
}

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, value));
}

// The schedule row compares live usage with the straight-line weekly
// schedule. It stays neutral: status emphasis belongs to the runway verdict.
function ScheduleRow({ pace }: { pace: WeeklyCreditPace }) {
  const { t } = useTranslation();
  const usedPercent = clampPercent(pace.actualUsedPercent);
  const scheduledPercent = clampPercent(pace.scheduledUsedPercent);
  const deltaPercent = pace.smoothedDeltaPercent ?? pace.deltaPercent;
  const roundedGap = Math.round(Math.abs(deltaPercent));
  const gapLabel =
    roundedGap === 0
      ? t("dashboard.weeklyPace.status.onPace")
      : t(deltaPercent > 0 ? "dashboard.weeklyPace.status.overPlanned" : "dashboard.weeklyPace.status.belowPlanned", {
          percent: `${roundedGap}%`,
        });
  const scheduleGapCredits = pace.smoothedScheduleGapCredits ?? pace.scheduleGapCredits;
  const lowerPercent = Math.min(usedPercent, scheduledPercent);
  const gapWidth = Math.abs(usedPercent - scheduledPercent);
  const overSchedule = usedPercent > scheduledPercent;

  return (
    <div className="border-t border-dashed pt-3.5" data-testid="runway-schedule-row">
      <div className="mb-2.5 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 text-xs">
        <div className="flex gap-3.5 tabular-nums text-muted-foreground">
          <span>
            {t("dashboard.weeklyPace.usedNow")}
            <span className="ml-1 font-semibold text-foreground">{formatPercent(pace.actualUsedPercent)}</span>
          </span>
          <span>
            {t("dashboard.weeklyPace.scheduledByNow")}
            <span className="ml-1 font-semibold text-foreground">{formatPercent(pace.scheduledUsedPercent)}</span>
          </span>
        </div>
        <span className="whitespace-nowrap font-medium tabular-nums">{gapLabel}</span>
      </div>
      <div className="relative h-2 rounded-full bg-muted">
        <div className="absolute inset-y-0 left-0 rounded-full bg-muted-foreground/45" style={{ width: `${lowerPercent}%` }} />
        {gapWidth > 0 ? (
          <div
            data-testid={overSchedule ? "runway-schedule-over" : "runway-schedule-under"}
            className={cn(
              "absolute inset-y-0 rounded-r-full",
              overSchedule
                ? "bg-[repeating-linear-gradient(-45deg,color-mix(in_oklab,var(--muted-foreground)_70%,transparent)_0_3px,color-mix(in_oklab,var(--muted-foreground)_40%,transparent)_3px_6px)]"
                : "ring-1 ring-inset ring-muted-foreground/45",
            )}
            style={{ left: `${lowerPercent}%`, width: `${gapWidth}%` }}
          />
        ) : null}
        <div
          data-testid="runway-schedule-marker"
          className="absolute -top-[3px] h-3.5 w-0.5 -translate-x-px rounded-full bg-foreground/70"
          style={{ left: `${scheduledPercent}%` }}
        />
      </div>
      <div className="mt-1.5 flex items-center justify-between gap-3 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-4 rounded-full bg-muted-foreground/45" />
          {t("dashboard.weeklyPace.actual")}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-0.5 rounded-full bg-foreground/70" />
          {t("dashboard.weeklyPace.scheduleMarker")}
        </span>
      </div>
      {scheduleGapCredits > 0 ? (
        <p className="mt-2 text-xs tabular-nums text-muted-foreground">{scheduleGapLine(pace, t)}</p>
      ) : null}
    </div>
  );
}

function PaceBreakdown({ rows }: { rows: PaceBreakdownRow[] }) {
  const { t } = useTranslation();
  return (
    <div className="border-t border-dashed pt-3.5" data-testid="pace-breakdown">
      <div className="grid grid-cols-[auto_minmax(0,1fr)_auto_auto] items-center gap-x-2.5 gap-y-1.5 text-xs">
        {rows.map((row) => {
          const status = row.pace.runwayStatus ?? "safe";
          const etaHours = row.pace.depletionEtaHours;
          return (
            <Fragment key={row.key}>
              <span aria-hidden className={cn("h-2 w-2 rounded-full", VERDICT_MARKER_CLASSES[status])} />
              <span className={cn("truncate", row.emphasized && "font-semibold")}>{row.label}</span>
              <span className="text-right tabular-nums text-muted-foreground">
                {t("dashboard.weeklyPace.breakdownLeft", {
                  percent: formatHeadroomPercent(row.pace.headroomPercent ?? 100 - row.pace.actualUsedPercent),
                })}
              </span>
              <span className="text-right tabular-nums text-muted-foreground">
                {etaHours != null && Number.isFinite(etaHours)
                  ? t("dashboard.weeklyPace.runsOutIn", { duration: formatDurationHours(etaHours, t) })
                  : t("dashboard.weeklyPace.breakdownSteady")}
              </span>
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}

function RunwayWeeklyCreditsPaceCard({
  pace,
  subtitle,
  breakdown,
  runwayStatus,
  headroomPercent,
  headroomCredits,
}: {
  pace: WeeklyCreditPace;
  subtitle: string;
  breakdown: PaceBreakdownRow[] | undefined;
  runwayStatus: WeeklyCreditRunwayStatus;
  headroomPercent: number;
  headroomCredits: number;
}) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((state) => state.dateDisplayFormat);
  const unit = pace.unit;

  const burnRate = pace.burnRateRecentCreditsPerHour ?? null;
  const etaHours = pace.depletionEtaHours != null && Number.isFinite(pace.depletionEtaHours) ? pace.depletionEtaHours : null;
  const reliefHours = pace.nextReliefInHours != null && Number.isFinite(pace.nextReliefInHours) ? pace.nextReliefInHours : null;
  const reliefCredits = pace.nextReliefCredits ?? null;
  const saturated =
    pace.saturatedAccountCount != null && pace.accountCount > 0 && pace.saturatedAccountCount === pace.accountCount;
  const runsDry = runwayStatus === "runs_dry";

  // The depletion/reset tooltips are read-only timestamps, so they follow the
  // dashboard's date-display and 12/24-hour preferences via the shared
  // formatter rather than a locale-default Intl instance.
  const { etaAtLabel, horizonHours, etaPercent, resetTicks } = buildRunwayTimeline(
    etaHours,
    reliefHours,
    pace.resetEvents,
    (epochMs) => formatDateTimeInline(new Date(epochMs).toISOString(), dateDisplayFormat),
  );

  const burnRateLine =
    burnRate != null && burnRate > 0
      ? t(saturated ? "dashboard.weeklyPace.atBurnRateFloor" : "dashboard.weeklyPace.atBurnRate", {
          credits: formatUnitValue(burnRate, unit),
        })
      : null;

  return (
    <section className="@container/weekly-pace rounded-xl border bg-card p-5" aria-label={t("dashboard.weeklyPace.title")}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold">{t("dashboard.weeklyPace.title")}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
        </div>
        <span
          data-testid="weekly-runway-verdict"
          className={cn(
            "inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
            VERDICT_BADGE_CLASSES[runwayStatus],
          )}
        >
          {t(VERDICT_LABEL_KEYS[runwayStatus])}
        </span>
      </div>

      <div className="space-y-4">
        <div className="min-h-16">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
            <p className="text-[1.625rem] font-semibold tabular-nums tracking-[-0.02em]">
              {formatHeadroomPercent(headroomPercent)}
            </p>
            <p className="text-xs tabular-nums text-muted-foreground">
              {t("dashboard.weeklyPace.heroLeft", { amount: formatUnitAmount(Math.max(0, headroomCredits), unit, t) })}
            </p>
          </div>
          <p className="mt-1 text-xs tabular-nums text-muted-foreground">
            {etaHours != null ? (
              <span
                title={etaAtLabel ?? undefined}
                className={cn(runsDry && "font-medium text-red-600 dark:text-red-400")}
              >
                {t("dashboard.weeklyPace.runsOutIn", { duration: formatDurationHours(etaHours, t) })}
              </span>
            ) : burnRate == null ? (
              // null burn rate means "too few recent samples to measure",
              // which must read differently from a measured zero burn.
              <span>{t("dashboard.weeklyPace.burnNotMeasured")}</span>
            ) : (
              <span>{t("dashboard.weeklyPace.steadyState")}</span>
            )}
            {burnRateLine ? <span className="ml-1.5">{burnRateLine}</span> : null}
          </p>
          {saturated ? (
            <p className="mt-1 text-[11px] text-muted-foreground">{t("dashboard.weeklyPace.saturatedFloor")}</p>
          ) : null}
        </div>

        <div className="min-h-5 text-xs">
          {runsDry && etaHours != null && reliefHours != null ? (
            <p className="font-medium tabular-nums text-red-600 dark:text-red-400">
              {t("dashboard.weeklyPace.runsDryBeforeRelief", {
                eta: formatDurationHours(etaHours, t),
                relief: formatDurationHours(reliefHours, t),
              })}
            </p>
          ) : reliefHours != null ? (
            <p className="tabular-nums text-muted-foreground">
              {t("dashboard.weeklyPace.reliefLine", {
                duration: formatDurationHours(reliefHours, t),
                amount: formatUnitAmount(Math.max(0, reliefCredits ?? 0), unit, t),
              })}
            </p>
          ) : null}
        </div>

        <div>
          <div className="relative h-1.5 rounded-full bg-muted" data-testid="runway-timeline">
            {etaPercent != null ? (
              <div
                className={cn("h-full rounded-full", VERDICT_FILL_CLASSES[runwayStatus])}
                style={{ width: `${etaPercent}%` }}
              />
            ) : null}
            {resetTicks.map((tick, index) => (
              <div
                key={`reset-${index}`}
                data-testid="runway-reset-tick"
                title={t("dashboard.weeklyPace.resetTickTooltip", {
                  amount: formatUnitAmount(tick.creditsReturned, unit, t),
                  time: tick.atLabel,
                })}
                className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 rounded-full bg-foreground/50"
                style={{ left: `${tick.leftPercent}%` }}
              />
            ))}
            {etaPercent != null ? (
              <div
                data-testid="runway-eta-marker"
                title={etaAtLabel ?? undefined}
                className={cn(
                  "absolute top-1/2 h-3 w-0.5 -translate-y-1/2 rounded-full",
                  VERDICT_MARKER_CLASSES[runwayStatus],
                )}
                style={{ left: `${etaPercent}%` }}
              />
            ) : null}
          </div>
          <div className="mt-1 flex items-center justify-between text-[10px] text-muted-foreground">
            <span>{t("dashboard.weeklyPace.timelineNow")}</span>
            <span className="tabular-nums">{formatDurationHours(horizonHours, t)}</span>
          </div>
        </div>

        <ScheduleRow pace={pace} />
        {breakdown ? <PaceBreakdown rows={breakdown} /> : null}
      </div>
    </section>
  );
}

function LegacyWeeklyCreditsPaceCard({
  pace,
  subtitle,
  breakdown,
}: {
  pace: WeeklyCreditPace;
  subtitle: string;
  breakdown: PaceBreakdownRow[] | undefined;
}) {
  const { t } = useTranslation();
  const statusClass =
    pace.status === "danger"
      ? "border-red-500/25 bg-red-500/10 text-red-700 dark:text-red-300"
      : pace.status === "ahead"
        ? "border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-300"
        : pace.status === "behind"
          ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
          : "border-border bg-muted/40 text-muted-foreground";
  const actualBarWidth = Math.max(0, Math.min(100, pace.actualUsedPercent));
  const scheduledMarkerLeft = Math.max(0, Math.min(100, pace.scheduledUsedPercent));
  const actualBarClass =
    pace.status === "danger" ? "bg-red-500" : pace.status === "ahead" ? "bg-amber-500" : "bg-primary";

  return (
    <section className="rounded-xl border bg-card p-5" aria-label={t("dashboard.weeklyPace.title")}>
      <div className="mb-4 flex justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{t("dashboard.weeklyPace.title")}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
        </div>
        <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg", statusClass)}>
          <Gauge className="h-4 w-4" aria-hidden="true" />
        </div>
      </div>

      <div className="space-y-4">
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="min-w-0 rounded-md bg-muted/30 px-3 py-2">
	              <p className="text-muted-foreground">{t("dashboard.weeklyPace.usedNow")}</p>
              <p className="mt-1 text-sm font-semibold tabular-nums">{formatPercent(pace.actualUsedPercent)}</p>
            </div>
            <div className="min-w-0 rounded-md bg-muted/30 px-3 py-2">
	              <p className="text-muted-foreground">{t("dashboard.weeklyPace.scheduledByNow")}</p>
              <p className="mt-1 text-sm font-semibold tabular-nums">{formatPercent(pace.scheduledUsedPercent)}</p>
            </div>
            <div className="min-w-0 rounded-md bg-muted/30 px-3 py-2">
	              <p className="text-muted-foreground">{t("dashboard.weeklyPace.paceGap")}</p>
	              <p className="mt-1 text-sm font-semibold tabular-nums">{statusLabel(pace, t)}</p>
            </div>
          </div>
          <div className="relative h-1.5 rounded-full bg-muted">
            <div className={cn("h-full rounded-full", actualBarClass)} style={{ width: `${actualBarWidth}%` }} />
            <div
              className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 rounded-full bg-foreground/70"
              style={{ left: `${scheduledMarkerLeft}%` }}
            />
          </div>
          <div className="flex items-center justify-between gap-3 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className={cn("h-1.5 w-4 rounded-full", actualBarClass)} />
	              {t("dashboard.weeklyPace.actual")}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-0.5 rounded-full bg-foreground/70" />
	              {t("dashboard.weeklyPace.scheduleMarker")}
            </span>
          </div>
          <div className="rounded-lg border bg-background/60 px-3 py-2 text-xs text-muted-foreground">
	            <p>{scheduleGapLine(pace, t)}</p>
	            <p className="mt-1">{forecastLine(pace, t)}</p>
          </div>
        </div>
        {breakdown ? <PaceBreakdown rows={breakdown} /> : null}
      </div>
    </section>
  );
}

export function WeeklyCreditsPaceCard({ pace, subtitle, breakdown }: WeeklyCreditsPaceCardProps) {
  if (!pace) {
    return null;
  }
  // The runway layout renders only when the backend sent the full companion
  // set; a partial payload falls back to the legacy layout instead of
  // masking gaps with synthesized stand-in numbers.
  if (pace.runwayStatus != null && pace.headroomPercent != null && pace.headroomCredits != null) {
    return (
      <RunwayWeeklyCreditsPaceCard
        pace={pace}
        subtitle={subtitle}
        breakdown={breakdown}
        runwayStatus={pace.runwayStatus}
        headroomPercent={pace.headroomPercent}
        headroomCredits={pace.headroomCredits}
      />
    );
  }
  return <LegacyWeeklyCreditsPaceCard pace={pace} subtitle={subtitle} breakdown={breakdown} />;
}
