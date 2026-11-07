import { findSubscriptionEnd, type AccountSubscriptionEnd } from "@/features/accounts/account-subscriptions";
import type { LimitSummary, ProviderSummary } from "@/features/accounts/provider-summary";
import type { QuotaFamily } from "@/features/antigravity/api";
import type { DashboardView, WeeklyCreditPace, WeeklyCreditPaceUnit } from "@/features/dashboard/utils";
import type { UpcomingHorizon } from "@/hooks/use-dashboard-preferences";

export const UPCOMING_HORIZON_MS: Record<UpcomingHorizon, number> = {
  "24h": 24 * 3_600_000,
  "7d": 7 * 24 * 3_600_000,
};

/** Events at most this far apart happen at the same moment. */
const SAME_MOMENT_MS = 60_000;
/** A window with this share left or more is barely used; its reset is not worth a row. */
const BARELY_USED_PERCENT_LEFT = 80;
/** Below this share left, a window's refill is worth a row. */
const LOW_PERCENT_LEFT = 20;

export type UpcomingProvider = "codex" | "claude" | "antigravity";

/** One weekly pool: Codex, Claude, or an Antigravity model family. */
export type UpcomingPool = { provider: UpcomingProvider; family: QuotaFamily | null; pace: WeeklyCreditPace };

export type UpcomingKind = "back" | "reset" | "refill" | "runsDry" | "lapse" | "subscriptionEnd";

export type UpcomingAmount = { value: number; unit: WeeklyCreditPaceUnit };

export type UpcomingEvent = {
  kind: UpcomingKind;
  /** Epoch milliseconds. */
  at: number;
  provider: UpcomingProvider;
  /** The Antigravity family of a pool event. */
  family: QuotaFamily | null;
  /** Label of the account window the event is about, for example "Weekly" or "Gemini · 5h". */
  window: string | null;
  accounts: ProviderSummary[];
  /** Credits a reset returns, a subscription end removes per week, or a lapse leaves unspent. */
  amount: UpcomingAmount | null;
  /** Share of the pool a reset returns. */
  poolPercent: number | null;
  /** Share left of a refilling window. */
  percentLeft: number | null;
};

export type UpcomingSources = {
  summaries: ProviderSummary[];
  subscriptionEnds: AccountSubscriptionEnd[] | undefined;
  pools: UpcomingPool[];
  now: number;
  horizonMs: number;
};

const ESTIMATED_KINDS: ReadonlySet<UpcomingKind> = new Set(["runsDry", "lapse"]);

/** Run-outs and lapses are forecasts from the recent burn rate. */
export function isEstimate(event: UpcomingEvent): boolean {
  return ESTIMATED_KINDS.has(event.kind);
}

/** The weekly pools of the dashboard view. */
export function upcomingPools(
  view: Pick<DashboardView, "weeklyCreditPace" | "claudeWeeklyPace" | "antigravityWeeklyPace">,
): UpcomingPool[] {
  return [
    ...(view.weeklyCreditPace ? [{ provider: "codex" as const, family: null, pace: view.weeklyCreditPace }] : []),
    ...(view.claudeWeeklyPace ? [{ provider: "claude" as const, family: null, pace: view.claudeWeeklyPace }] : []),
    ...view.antigravityWeeklyPace.map(({ family, pace }) => ({ provider: "antigravity" as const, family, pace })),
  ];
}

function isTimed(summary: ProviderSummary): summary is ProviderSummary & { kind: UpcomingProvider } {
  return summary.kind === "codex" || summary.kind === "claude" || summary.kind === "antigravity";
}

const sameMoment = (a: number, b: number) => Math.abs(a - b) <= SAME_MOMENT_MS;

function event(kind: UpcomingKind, at: number, provider: UpcomingProvider, fields: Partial<UpcomingEvent>): UpcomingEvent {
  return {
    kind,
    at,
    provider,
    family: null,
    window: null,
    accounts: [],
    amount: null,
    poolPercent: null,
    percentLeft: null,
    ...fields,
  };
}

/** The pool's weekly window on an account: the "weekly" limit, or the family's limit for Antigravity. */
function isPoolWindow(pool: UpcomingPool, limit: LimitSummary): boolean {
  return pool.family === null ? limit.key === "weekly" : limit.key === pool.family;
}

const windowKey = (summary: ProviderSummary, limit: LimitSummary) => `${summary.kind}:${summary.id}:${limit.key}`;

function sumAmounts(a: UpcomingAmount | null, b: UpcomingAmount | null): UpcomingAmount | null {
  return a && b ? { value: a.value + b.value, unit: a.unit } : (a ?? b);
}

function sumNullable(a: number | null, b: number | null): number | null {
  return a !== null && b !== null ? a + b : (a ?? b);
}

function minNullable(a: number | null, b: number | null): number | null {
  return a !== null && b !== null ? Math.min(a, b) : (a ?? b);
}

/** Events of one kind, pool and window at the same moment share a row. */
function mergeSimultaneous(events: UpcomingEvent[]): UpcomingEvent[] {
  const merged: UpcomingEvent[] = [];
  for (const next of [...events].sort((a, b) => a.at - b.at)) {
    const index = merged.findIndex(
      (row) =>
        row.kind === next.kind &&
        row.provider === next.provider &&
        row.family === next.family &&
        row.window === next.window &&
        sameMoment(row.at, next.at),
    );
    if (index === -1) {
      merged.push(next);
      continue;
    }
    const row = merged[index];
    merged[index] = {
      ...row,
      accounts: [...row.accounts, ...next.accounts],
      amount: sumAmounts(row.amount, next.amount),
      poolPercent: sumNullable(row.poolPercent, next.poolPercent),
      percentLeft: minNullable(row.percentLeft, next.percentLeft),
    };
  }
  return merged;
}

/**
 * The moments within the horizon that change Codex, Claude or Antigravity capacity, ordered by time: limited
 * accounts coming back, weekly pool resets, low windows refilling, projected run-outs, credits lapsing unspent and
 * subscription ends. Pace hours count from `now`, the moment the dashboard renders them.
 */
export function buildUpcomingEvents({ summaries, subscriptionEnds, pools, now, horizonMs }: UpcomingSources): UpcomingEvent[] {
  const inHorizon = (at: number) => at > now && at <= now + horizonMs;
  const timed = summaries.filter(isTimed);
  const covered = new Set<string>();

  const returns = timed.flatMap((summary) => {
    const until = summary.notice?.until;
    if ((summary.status !== "limited" && summary.status !== "exceeded") || until?.kind !== "cooldown") return [];
    const at = Date.parse(until.at);
    if (!inHorizon(at)) return [];
    const window = summary.limits.find((limit) => limit.resetAt === until.at);
    if (window) covered.add(windowKey(summary, window));
    return [event("back", at, summary.kind, { window: window?.label ?? null, accounts: [summary] })];
  });

  const resets: UpcomingEvent[] = [];
  for (const pool of pools) {
    for (const reset of pool.pace.resetEvents ?? []) {
      const at = Date.parse(reset.at);
      if (!inHorizon(at) || reset.creditsReturned <= 0) continue;
      const amount = { value: reset.creditsReturned, unit: pool.pace.unit };
      const poolPercent = (reset.creditsReturned / pool.pace.totalFullCredits) * 100;
      const windows = timed
        .filter((summary) => summary.kind === pool.provider)
        .flatMap((summary) => summary.limits.map((limit) => ({ summary, limit })))
        .filter(({ limit }) => isPoolWindow(pool, limit) && limit.resetAt !== null && sameMoment(Date.parse(limit.resetAt), at));
      // A limited account coming back as its weekly window resets gets the credits on its return row.
      const back = returns.find(
        (row) => row.amount === null && sameMoment(row.at, at) && windows.some(({ summary }) => summary === row.accounts[0]),
      );
      if (back) {
        back.amount = amount;
        back.poolPercent = poolPercent;
        continue;
      }
      const match = windows.find(({ summary, limit }) => !covered.has(windowKey(summary, limit)));
      if (match) {
        covered.add(windowKey(match.summary, match.limit));
        if (match.limit.percentLeft !== null && match.limit.percentLeft >= BARELY_USED_PERCENT_LEFT) continue;
      }
      resets.push(
        event("reset", at, pool.provider, {
          family: match ? null : pool.family,
          window: match?.limit.label ?? null,
          accounts: match ? [match.summary] : [],
          amount,
          poolPercent,
        }),
      );
    }
  }

  const refills = timed.flatMap((summary) =>
    summary.status !== "active"
      ? []
      : summary.limits.flatMap((limit) => {
          if (limit.resetAt === null || limit.percentLeft === null || limit.percentLeft >= LOW_PERCENT_LEFT) return [];
          const at = Date.parse(limit.resetAt);
          if (!inHorizon(at) || covered.has(windowKey(summary, limit))) return [];
          return [event("refill", at, summary.kind, { window: limit.label, accounts: [summary], percentLeft: limit.percentLeft })];
        }),
  );

  const forecasts = pools.flatMap(({ provider, family, pace }) => {
    const rows: UpcomingEvent[] = [];
    if (pace.runwayStatus === "runs_dry" && pace.depletionEtaHours != null) {
      rows.push(event("runsDry", now + pace.depletionEtaHours * 3_600_000, provider, { family }));
    }
    if (pace.runwayStatus === "lapses" && pace.lapsingCredits != null && pace.lapseInHours != null) {
      rows.push(
        event("lapse", now + pace.lapseInHours * 3_600_000, provider, {
          family,
          amount: { value: pace.lapsingCredits, unit: pace.unit },
        }),
      );
    }
    return rows.filter((row) => inHorizon(row.at));
  });

  // Antigravity families are separate pools, so an account's end has no single weekly amount there.
  const poolEnds = new Map(
    pools.filter((pool) => pool.family === null).map((pool) => [pool.provider, { unit: pool.pace.unit, ends: [...(pool.pace.subscriptionEnds ?? [])] }]),
  );
  const ends = timed.flatMap((summary) => {
    const endsAt = findSubscriptionEnd(subscriptionEnds, summary.colorTarget);
    if (endsAt === null) return [];
    const at = Date.parse(endsAt);
    if (!inHorizon(at)) return [];
    const pool = poolEnds.get(summary.kind);
    const index = pool ? pool.ends.findIndex((end) => sameMoment(Date.parse(end.at), at)) : -1;
    const amount = pool && index !== -1 ? { value: pool.ends.splice(index, 1)[0].weeklyCredits, unit: pool.unit } : null;
    return [event("subscriptionEnd", at, summary.kind, { accounts: [summary], amount })];
  });

  return mergeSimultaneous([...returns, ...resets, ...refills, ...forecasts, ...ends]);
}
