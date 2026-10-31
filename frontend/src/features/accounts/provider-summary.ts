import type { TFunction } from "i18next";

import { isEmailLabel } from "@/components/blur-email";
import type { AccountProvider } from "@/components/brand/account-provider";
import type { AccountColorHexes, AccountColorTarget } from "@/features/accounts/account-colors";
import { type AccountSubscriptionEnd, findSubscriptionEnd } from "@/features/accounts/account-subscriptions";
import type { DetailTab } from "@/features/accounts/hooks/use-detail-tab";
import type { AccountRoutingPolicy, AccountSummary } from "@/features/accounts/schemas";
import { sortAccountsForDisplay, type AccountSortMode } from "@/features/accounts/sorting";
import type { AntigravityAccount, AntigravityWindow } from "@/features/antigravity/api";
import {
  FAMILY_LABELS,
  SHORT_FAMILY_LABELS,
  WINDOW_LABELS,
  antigravityStatus,
  bindingWindow,
  modelSummary as antigravityModelSummary,
  quotaFamilies,
} from "@/features/antigravity/display-values";
import type { ClaudeAccount } from "@/features/claude/api";
import { claudeStatus } from "@/features/claude/display-values";
import type { ModelSource } from "@/features/model-sources/schemas";
import { OPENAI_COMPATIBLE_LABEL, modelCountLabel, modelSourceStatus } from "@/features/model-sources/display-values";
import type { OpenRouterAccount } from "@/features/openrouter/api";
import { keyAllowance, money, openRouterBalance, openRouterStatus } from "@/features/openrouter/display-values";
import type { AccountQuotaDisplayPreference } from "@/hooks/use-account-quota-display";
import { normalizeStatus, type DashboardAccountStatus } from "@/utils/account-status";
import { formatPercentNullable, formatQuotaResetLabel, formatSlug, parseDate } from "@/utils/formatters";

export type ProviderKind = AccountProvider;

/** Display order of the provider groups on the Providers page and in its account rail. */
export const PROVIDER_ORDER: readonly ProviderKind[] = ["codex", "claude", "antigravity", "openrouter", "openai_compatible"];

export const PROVIDER_LABELS: Record<ProviderKind, string> = {
  codex: "Codex",
  claude: "Claude",
  antigravity: "Antigravity",
  openrouter: "OpenRouter",
  openai_compatible: OPENAI_COMPATIBLE_LABEL,
};

/** Column captions of the two limit columns, per provider. */
export const PROVIDER_LIMIT_CAPTIONS: Record<ProviderKind, readonly [string, string] | null> = {
  codex: ["Weekly", "5 hours"],
  claude: ["Weekly", "5 hours"],
  antigravity: ["Lowest model", "Second lowest"],
  openrouter: ["Balance", "Key allowance"],
  openai_compatible: null,
};

export type ProviderSources = {
  accounts: AccountSummary[];
  claudeAccounts: ClaudeAccount[];
  antigravityAccounts: AntigravityAccount[];
  openRouterAccounts: OpenRouterAccount[];
  modelSources: ModelSource[];
};

export type ProviderEntry =
  | { kind: "codex"; account: AccountSummary }
  | { kind: "claude"; account: ClaudeAccount }
  | { kind: "antigravity"; account: AntigravityAccount }
  | { kind: "openrouter"; account: OpenRouterAccount }
  | { kind: "openai_compatible"; account: ModelSource };

export type LimitSummary = {
  key: string;
  /** Full label, for example "Weekly" or "Gemini 4 Argon · 5h". */
  label: string;
  /** Narrow label for the account rail. */
  short: string;
  /** Share left, 0–100; null when unknown. Drives the bar. */
  percentLeft: number | null;
  /** Headline value, for example "41%" or "$42.18". */
  value: string;
  /** Next reset of a quota window. */
  resetAt: string | null;
  /** Static caption shown instead of a reset time, for example "of $100.00". */
  caption: string | null;
  /** Share that should be left now at an even pace through the window; null when not applicable. */
  pacePercent: number | null;
  stale: boolean;
};

export type SummaryTone = "ok" | "warn" | "bad" | "off";

export type ProviderNotice = { tone: Exclude<SummaryTone, "ok">; text: string };

export type ProviderSummary = {
  entry: ProviderEntry;
  kind: ProviderKind;
  id: string;
  name: string;
  /** Blur the name in privacy mode. */
  blurName: boolean;
  subtitle: string | null;
  blurSubtitle: boolean;
  plan: string | null;
  /** Plan key for the plan badge colours. */
  planKey: string;
  status: DashboardAccountStatus;
  tone: SummaryTone;
  /** One-line explanation when the account needs attention. */
  notice: ProviderNotice | null;
  limits: LimitSummary[];
  routingPolicy: AccountRoutingPolicy | null;
  models: string | null;
  resetCredits: number;
  trustedAccess: boolean;
  warmupEnabled: boolean | null;
  colorTarget: AccountColorTarget;
  /** Filter value of the account on the Logs page. */
  logsAccountId: string;
  /** Account key of the reports API. */
  activityKey: string;
  searchText: string;
};

export type ProviderGroup = { kind: ProviderKind; summaries: ProviderSummary[] };

export type ProviderFilter = "all" | "attention" | "paused";

export type SummaryContext = {
  quotaDisplay: AccountQuotaDisplayPreference;
  subscriptionEnds: AccountSubscriptionEnd[] | undefined;
  t: TFunction;
  now?: number;
};

const FIVE_HOURS_MINUTES = 300;
const WEEK_MINUTES = 10_080;

const STATUS_TONE: Record<DashboardAccountStatus, SummaryTone> = {
  active: "ok",
  paused: "off",
  limited: "warn",
  exceeded: "bad",
  reauth: "bad",
  deactivated: "bad",
};

/** Share of the window that is still ahead, which is the share of quota an even pace leaves now. */
export function linearPacePercent(resetAt: string | null | undefined, windowMinutes: number | null | undefined, now: number): number | null {
  const reset = parseDate(resetAt)?.getTime();
  if (reset === undefined || !windowMinutes) return null;
  const windowMs = windowMinutes * 60_000;
  return Math.max(0, Math.min(100, ((reset - now) / windowMs) * 100));
}

function clampPercent(value: number | null | undefined): number | null {
  return value == null || !Number.isFinite(value) ? null : Math.max(0, Math.min(100, value));
}

function percentLimit(
  key: string,
  label: string,
  short: string,
  percentLeft: number | null | undefined,
  resetAt: string | null | undefined,
  pacePercent: number | null,
  stale = false,
): LimitSummary {
  const left = clampPercent(percentLeft);
  return {
    key,
    label,
    short,
    percentLeft: left,
    value: formatPercentNullable(left),
    resetAt: resetAt ?? null,
    caption: null,
    pacePercent,
    stale,
  };
}

/** The windows a list row shows: both, or the one the compact-row preference selects when both exist. */
function preferredWindows<T>(weekly: T | null, fiveHour: T | null, preference: AccountQuotaDisplayPreference): T[] {
  if (weekly && fiveHour) {
    if (preference === "weekly") return [weekly];
    if (preference === "5h") return [fiveHour];
    return [weekly, fiveHour];
  }
  return [weekly, fiveHour].filter((value): value is T => value !== null);
}

function exhaustedNotice(limits: LimitSummary[], tone: "warn" | "bad"): ProviderNotice | null {
  const drained = limits.find((limit) => limit.percentLeft === 0);
  if (!drained) return null;
  return {
    tone,
    text: drained.resetAt ? `${drained.label} limit · back in ${formatQuotaResetLabel(drained.resetAt)}` : `${drained.label} limit reached`,
  };
}

function subscriptionNotice(ends: AccountSubscriptionEnd[] | undefined, target: AccountColorTarget, now: number): ProviderNotice | null {
  const endsAt = findSubscriptionEnd(ends, target);
  if (endsAt === null) return null;
  const end = Date.parse(endsAt);
  if (end <= now) return null;
  const date = new Date(end).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  return { tone: "warn", text: `Subscription ends ${date}` };
}

function statusNotice(status: DashboardAccountStatus, t: TFunction): ProviderNotice | null {
  if (status === "paused") return { tone: "off", text: t("providers.notice.paused") };
  if (status === "reauth") return { tone: "bad", text: t("providers.notice.reauth") };
  if (status === "deactivated") return { tone: "bad", text: t("common.status.deactivated") };
  return null;
}

function codexSummary(account: AccountSummary, context: SummaryContext, now: number): ProviderSummary {
  const usage = account.usage;
  const hasPrimary = account.windowMinutesPrimary != null || usage?.primaryRemainingPercent != null || account.resetAtPrimary != null;
  const hasSecondary = account.windowMinutesSecondary != null || usage?.secondaryRemainingPercent != null || account.resetAtSecondary != null;
  const hasMonthly = account.windowMinutesMonthly != null || usage?.monthlyRemainingPercent != null || account.resetAtMonthly != null;
  const weekly = hasSecondary
    ? percentLimit(
        "weekly",
        "Weekly",
        "Week",
        usage?.secondaryRemainingPercent,
        account.resetAtSecondary,
        linearPacePercent(account.resetAtSecondary, account.windowMinutesSecondary ?? WEEK_MINUTES, now),
      )
    : null;
  const fiveHour = hasPrimary ? percentLimit("5h", "5h", "5h", usage?.primaryRemainingPercent, account.resetAtPrimary, null) : null;
  const limits =
    hasMonthly && !hasPrimary && !hasSecondary
      ? [percentLimit("monthly", "Monthly", "Month", usage?.monthlyRemainingPercent, account.resetAtMonthly, null)]
      : preferredWindows(weekly, fiveHour, context.quotaDisplay);
  const status = normalizeStatus(account.status);
  const alias = account.alias?.trim() || "";
  const name = alias || account.displayName || account.email;
  const target = { accountId: account.accountId };
  return {
    entry: { kind: "codex", account },
    kind: "codex",
    id: account.accountId,
    name,
    blurName: !alias && isEmailLabel(name, account.email),
    subtitle: name === account.email ? null : account.email,
    blurSubtitle: true,
    plan: formatSlug(account.planType),
    planKey: account.planType,
    status,
    tone: STATUS_TONE[status],
    notice:
      statusNotice(status, context.t) ??
      (status === "limited" || status === "exceeded" ? exhaustedNotice([weekly, fiveHour].filter((v) => v !== null), STATUS_TONE[status] === "bad" ? "bad" : "warn") : null) ??
      subscriptionNotice(context.subscriptionEnds, target, now),
    limits,
    routingPolicy: status === "reauth" || status === "deactivated" ? null : (account.routingPolicy ?? "normal"),
    models: null,
    resetCredits: account.availableResetCredits ?? 0,
    trustedAccess: account.securityWorkAuthorized === true,
    warmupEnabled: account.limitWarmupEnabled,
    colorTarget: target,
    logsAccountId: account.accountId,
    activityKey: `account:${account.accountId}`,
    searchText: `${account.email} ${account.alias ?? ""} ${account.displayName} ${account.accountId} ${account.planType} codex openai chatgpt`,
  };
}

function claudeSummary(account: ClaudeAccount, context: SummaryContext, now: number): ProviderSummary {
  const window = (name: ClaudeAccount["quota"]["windows"][number]["name"]) =>
    account.quota.windows.find((candidate) => candidate.name === name) ?? null;
  const toLimit = (source: NonNullable<ReturnType<typeof window>>, key: string, label: string, short: string, minutes: number, pace: boolean) =>
    percentLimit(
      key,
      label,
      short,
      source.utilization === null ? null : 100 - source.utilization,
      source.resetsAt,
      pace ? linearPacePercent(source.resetsAt, minutes, now) : null,
      source.freshness === "stale",
    );
  const sevenDay = window("seven_day");
  const fiveHour = window("five_hour");
  const weekly = sevenDay ? toLimit(sevenDay, "weekly", "Weekly", "Week", WEEK_MINUTES, true) : null;
  const short = fiveHour ? toLimit(fiveHour, "5h", "5h", "5h", FIVE_HOURS_MINUTES, false) : null;
  const status = normalizeStatus(claudeStatus(account));
  const target = { modelSourceId: account.id };
  const plan = context.t(`claude.subscription.${account.planType}`);
  return {
    entry: { kind: "claude", account },
    kind: "claude",
    id: account.id,
    name: account.name,
    blurName: true,
    subtitle: account.accountEmail,
    blurSubtitle: true,
    plan,
    planKey: account.planType,
    status,
    tone: STATUS_TONE[status],
    notice:
      statusNotice(status, context.t) ??
      (status === "limited" || status === "exceeded" ? exhaustedNotice([weekly, short].filter((v) => v !== null), STATUS_TONE[status] === "bad" ? "bad" : "warn") : null) ??
      (account.state.usage_error ? { tone: "warn", text: context.t("providers.notice.usageUnavailable") } : null) ??
      subscriptionNotice(context.subscriptionEnds, target, now),
    limits: preferredWindows(weekly, short, context.quotaDisplay),
    routingPolicy: account.routingPolicy,
    models: account.state.all_models ? "All models" : `${account.state.selections.length} ${account.state.selections.length === 1 ? "model" : "models"}`,
    resetCredits: 0,
    trustedAccess: false,
    warmupEnabled: null,
    colorTarget: target,
    logsAccountId: `source:${account.id}`,
    activityKey: `source:${account.id}`,
    searchText: `${account.name} ${account.id} ${account.accountEmail ?? ""} claude anthropic ${account.planType.replaceAll("_", " ")} ${plan}`,
  };
}

const remainingOf = (window: AntigravityWindow) => Math.max(0, 100 - window.usedPercent);

function antigravitySummary(account: AntigravityAccount, context: SummaryContext, now: number): ProviderSummary {
  const binding = quotaFamilies(account)
    .flatMap((family) => {
      const window = bindingWindow(account, family);
      return window ? [{ family, window }] : [];
    })
    .sort((a, b) => remainingOf(a.window) - remainingOf(b.window));
  const limits = binding.slice(0, 2).map(({ family, window }) =>
    percentLimit(
      family,
      `${FAMILY_LABELS[family]} · ${WINDOW_LABELS[window.window]}`,
      SHORT_FAMILY_LABELS[family],
      remainingOf(window),
      window.resetsAt,
      window.window === "weekly" ? linearPacePercent(window.resetsAt, WEEK_MINUTES, now) : null,
    ),
  );
  const status = normalizeStatus(antigravityStatus(account, now));
  const target = { modelSourceId: account.id };
  const plan = context.t(`antigravity.plan.${account.planType}`);
  const holdNotice: ProviderNotice | null = account.hold
    ? { tone: "bad", text: context.t(`providers.notice.hold.${account.hold}`) }
    : null;
  return {
    entry: { kind: "antigravity", account },
    kind: "antigravity",
    id: account.id,
    name: account.name,
    blurName: true,
    subtitle: account.email,
    blurSubtitle: true,
    plan,
    planKey: account.planType.startsWith("ultra") ? "ultra" : account.planType,
    status,
    tone: STATUS_TONE[status],
    notice:
      holdNotice ??
      statusNotice(status, context.t) ??
      (account.state.verification ? { tone: "warn", text: context.t("providers.notice.verification") } : null) ??
      (status === "limited" || status === "exceeded" ? exhaustedNotice(limits, STATUS_TONE[status] === "bad" ? "bad" : "warn") : null) ??
      subscriptionNotice(context.subscriptionEnds, target, now),
    limits,
    routingPolicy: account.routingPolicy,
    models: antigravityModelSummary(account),
    resetCredits: 0,
    trustedAccess: false,
    warmupEnabled: null,
    colorTarget: target,
    logsAccountId: `source:${account.id}`,
    activityKey: `source:${account.id}`,
    searchText: `${account.name} ${account.id} ${account.email} antigravity google gemini ${account.planType.replaceAll("_", " ")} ${plan}`,
  };
}

function openRouterSummary(account: OpenRouterAccount, context: SummaryContext): ProviderSummary {
  const { key, key_error, credits, credits_error } = account.state;
  const balance = openRouterBalance(account);
  const balanceLimit: LimitSummary = {
    key: "balance",
    label: "Balance",
    short: "Bal.",
    percentLeft: credits && credits.total_credits > 0 && balance !== null ? clampPercent((balance / credits.total_credits) * 100) : null,
    value: account.hasManagementKey ? money(balance) : "No management key",
    resetAt: null,
    caption: credits ? `of ${money(credits.total_credits)}` : null,
    pacePercent: null,
    stale: !!credits && !!credits_error,
  };
  const allowanceLimit: LimitSummary = {
    key: "allowance",
    label: "Key allowance",
    short: "Key",
    percentLeft: key && key.limit !== null && key.limit > 0 && key.limit_remaining !== null ? clampPercent((key.limit_remaining / key.limit) * 100) : null,
    value: keyAllowance(account),
    resetAt: null,
    caption: key && key.limit !== null ? `of ${money(key.limit)}${key.limit_reset ? ` · ${key.limit_reset}` : ""}` : null,
    pacePercent: null,
    stale: !!key && !!key_error,
  };
  const status = normalizeStatus(openRouterStatus(account));
  const plan = key === null ? "Unknown" : key.is_free_tier ? "Free" : "Paid";
  const monitoringStale = !!(account.state.key_error || account.state.credits_error || account.state.catalog_error);
  return {
    entry: { kind: "openrouter", account },
    kind: "openrouter",
    id: account.id,
    name: account.name,
    blurName: true,
    subtitle: account.state.all_models ? "All conversation models" : `${account.state.selections.length} ${account.state.selections.length === 1 ? "model" : "models"} selected`,
    blurSubtitle: false,
    plan,
    planKey: plan.toLowerCase(),
    status,
    tone: STATUS_TONE[status],
    notice: statusNotice(status, context.t) ?? (monitoringStale ? { tone: "warn", text: context.t("providers.notice.monitoringStale") } : null),
    limits: [balanceLimit, allowanceLimit],
    routingPolicy: account.routingPolicy,
    models: null,
    resetCredits: 0,
    trustedAccess: false,
    warmupEnabled: null,
    colorTarget: { modelSourceId: account.id },
    logsAccountId: `source:${account.id}`,
    activityKey: `source:${account.id}`,
    searchText: `${account.name} ${account.id} openrouter ${plan}`,
  };
}

function modelSourceSummary(source: ModelSource, context: SummaryContext): ProviderSummary {
  const status = normalizeStatus(modelSourceStatus(source));
  return {
    entry: { kind: "openai_compatible", account: source },
    kind: "openai_compatible",
    id: source.id,
    name: source.name,
    blurName: true,
    subtitle: source.baseUrl,
    blurSubtitle: false,
    plan: null,
    planKey: "unknown",
    status,
    tone: STATUS_TONE[status],
    notice: statusNotice(status, context.t),
    limits: [],
    routingPolicy: null,
    models: modelCountLabel(source),
    resetCredits: 0,
    trustedAccess: false,
    warmupEnabled: null,
    colorTarget: { modelSourceId: source.id },
    logsAccountId: `source:${source.id}`,
    activityKey: `source:${source.id}`,
    searchText: `${source.name} ${source.id} ${source.baseUrl} openai-compatible openai compatible`,
  };
}

const STATUS_ORDER: Record<DashboardAccountStatus, number> = {
  active: 0,
  paused: 1,
  limited: 2,
  exceeded: 3,
  reauth: 4,
  deactivated: 5,
};

function nextReset(summary: ProviderSummary, now: number): number {
  const resets = summary.limits
    .map((limit) => parseDate(limit.resetAt)?.getTime() ?? Number.POSITIVE_INFINITY)
    .filter((reset) => reset > now);
  return resets.length > 0 ? Math.min(...resets) : Number.POSITIVE_INFINITY;
}

function limitLeft(summary: ProviderSummary, key: string): number {
  return summary.limits.find((limit) => limit.key === key)?.percentLeft ?? Number.POSITIVE_INFINITY;
}

/** Known values first, then by direction; unknown values sort last either way. */
function compareKnown(left: number, right: number, direction: "asc" | "desc"): number {
  const leftKnown = Number.isFinite(left);
  const rightKnown = Number.isFinite(right);
  if (leftKnown !== rightKnown) return leftKnown ? -1 : 1;
  if (left === right) return 0;
  return direction === "desc" ? right - left : left - right;
}

/**
 * Order of provider accounts within their group. Codex accounts keep their own
 * sort, which also weighs reset credits; the other providers apply the same
 * sort modes to their summaries.
 */
function compareSummaries(mode: AccountSortMode, now: number) {
  const byName = (left: ProviderSummary, right: ProviderSummary) =>
    left.name.localeCompare(right.name, undefined, { sensitivity: "base" });
  return (left: ProviderSummary, right: ProviderSummary): number => {
    let comparison = 0;
    if (mode === "name_asc") comparison = byName(left, right);
    else if (mode === "name_desc") comparison = byName(right, left);
    else if (mode === "status_asc" || mode === "status_desc")
      comparison = compareKnown(STATUS_ORDER[left.status], STATUS_ORDER[right.status], mode === "status_desc" ? "desc" : "asc");
    else if (mode === "reset_latest") comparison = compareKnown(nextReset(left, now), nextReset(right, now), "desc");
    else if (mode === "quota_5h_asc" || mode === "quota_5h_desc")
      comparison = compareKnown(limitLeft(left, "5h"), limitLeft(right, "5h"), mode.endsWith("desc") ? "desc" : "asc");
    else if (mode === "quota_7d_asc" || mode === "quota_7d_desc")
      comparison = compareKnown(limitLeft(left, "weekly"), limitLeft(right, "weekly"), mode.endsWith("desc") ? "desc" : "asc");
    if (comparison !== 0) return comparison;
    return compareKnown(nextReset(left, now), nextReset(right, now), "asc") || byName(left, right);
  };
}

/** Summary of one account. */
export function summarizeEntry(entry: ProviderEntry, context: SummaryContext): ProviderSummary {
  const now = context.now ?? Date.now();
  switch (entry.kind) {
    case "codex":
      return codexSummary(entry.account, context, now);
    case "claude":
      return claudeSummary(entry.account, context, now);
    case "antigravity":
      return antigravitySummary(entry.account, context, now);
    case "openrouter":
      return openRouterSummary(entry.account, context);
    case "openai_compatible":
      return modelSourceSummary(entry.account, context);
  }
}

/** Every account as a summary, grouped by provider in display order and sorted within each group. */
export function buildProviderGroups(sources: ProviderSources, sortMode: AccountSortMode, context: SummaryContext): ProviderGroup[] {
  const now = context.now ?? Date.now();
  const compare = compareSummaries(sortMode, now);
  const groups: Record<ProviderKind, ProviderSummary[]> = {
    codex: sortAccountsForDisplay(sources.accounts, context.quotaDisplay, sortMode).map((account) => codexSummary(account, context, now)),
    claude: sources.claudeAccounts.map((account) => claudeSummary(account, context, now)).sort(compare),
    antigravity: sources.antigravityAccounts.map((account) => antigravitySummary(account, context, now)).sort(compare),
    openrouter: sources.openRouterAccounts.map((account) => openRouterSummary(account, context)).sort(compare),
    openai_compatible: sources.modelSources.map((source) => modelSourceSummary(source, context)).sort(compare),
  };
  return PROVIDER_ORDER.map((kind) => ({ kind, summaries: groups[kind] })).filter((group) => group.summaries.length > 0);
}

export function needsAttention(summary: ProviderSummary): boolean {
  return summary.tone === "bad" || summary.tone === "warn" || summary.notice?.tone === "bad" || summary.notice?.tone === "warn";
}

export function matchesFilter(summary: ProviderSummary, filter: ProviderFilter): boolean {
  if (filter === "attention") return needsAttention(summary);
  if (filter === "paused") return summary.status === "paused";
  return true;
}

export function matchesSearch(summary: ProviderSummary, search: string): boolean {
  const needle = search.trim().toLowerCase();
  return !needle || `${summary.name} ${summary.searchText}`.toLowerCase().includes(needle);
}

export function filterGroups(groups: ProviderGroup[], filter: ProviderFilter, search: string): ProviderGroup[] {
  return groups
    .map((group) => ({ ...group, summaries: group.summaries.filter((summary) => matchesFilter(summary, filter) && matchesSearch(summary, search)) }))
    .filter((group) => group.summaries.length > 0);
}

/** Chart colour of an account, which also colours its logo. */
export function summaryColor(summary: ProviderSummary, colors: AccountColorHexes): string | undefined {
  return summary.kind === "codex" ? colors.accounts.get(summary.id) : colors.modelSources.get(summary.id);
}

export function accountHref(id: string, tab: DetailTab = "overview"): string {
  const href = "/providers/" + encodeURIComponent(id);
  return tab === "settings" ? href + "/settings" : href;
}

const NOTICE_TEXT: Record<SummaryTone, string> = {
  ok: "text-muted-foreground",
  off: "text-muted-foreground",
  warn: "text-amber-600 dark:text-amber-400",
  bad: "text-destructive",
};

export function noticeClass(tone: SummaryTone): string {
  return NOTICE_TEXT[tone];
}

