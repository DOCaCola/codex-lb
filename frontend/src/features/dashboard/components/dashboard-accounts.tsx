import { Play, RotateCcw, ShieldCheck, Users } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ProviderLogo } from "@/components/brand/provider-account-name";
import { EmptyState } from "@/components/empty-state";
import { PlanBadge } from "@/components/plan-badge";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import type { AccountColorHexes } from "@/features/accounts/account-colors";
import type { AccountActivity } from "@/features/accounts/hooks/use-provider-activity";
import {
  PROVIDER_LABELS,
  accountHref,
  noticeClass,
  type LimitSummary,
  type ProviderNotice,
  type ProviderSummary,
  summaryColor,
  type SummaryTone,
} from "@/features/accounts/provider-summary";
import { ExtraUsageBadge } from "@/features/claude/account-display";
import { accountSubscriptionCredits } from "@/features/dashboard/account-credit-display";
import type { AccountSummary } from "@/features/dashboard/schemas";
import { money } from "@/features/openrouter/display-values";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import { formatCompactAccountId } from "@/utils/account-identifiers";
import { formatCurrency, formatDateTimeInline, formatNumber, formatResetCountdown, formatTimeRemaining } from "@/utils/formatters";

export type DashboardAccountActions = {
  readOnly: boolean;
  onResume: (summary: ProviderSummary) => void;
  onResetCredit: (account: AccountSummary) => void;
};

export type DashboardAccountsProps = {
  summaries: ProviderSummary[];
  colors: AccountColorHexes;
  /** Per-account activity of the reports API; undefined while loading. */
  activity: Map<string, AccountActivity> | undefined;
  /** False when the user cannot read activity, so no daily cost is shown. */
  activityAvailable: boolean;
  actions: DashboardAccountActions;
};

const DOT: Record<SummaryTone, string> = {
  ok: "bg-emerald-500",
  warn: "bg-amber-500",
  bad: "bg-red-500",
  off: "bg-muted-foreground",
};

const STRIP: Record<ProviderNotice["tone"], string> = {
  warn: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  bad: "bg-red-500/12 text-red-600 dark:text-red-400",
  off: "bg-muted text-muted-foreground",
};

/** Today's cost: OpenRouter reports its own daily spend; other providers use recorded requests. */
function todayCost(summary: ProviderSummary, activity: Map<string, AccountActivity> | undefined, available: boolean): string | null {
  if (summary.entry.kind === "openrouter") return money(summary.entry.account.state.key?.usage_daily);
  if (!available) return null;
  return formatCurrency(activity?.get(summary.activityKey)?.today.costUsd ?? 0);
}

/** Labels that fit the limit column; Antigravity families use their short names. */
function limitLabel(summary: ProviderSummary, limit: LimitSummary): string {
  return summary.kind === "antigravity" ? limit.short : limit.label;
}

function LimitFill({ limit, color }: { limit: LimitSummary; color: string | undefined }) {
  const percent = limit.percentLeft;
  return (
    <div className="relative h-[5px] rounded-full bg-muted">
      {percent !== null ? (
        <div
          className={cn("h-full rounded-full", percent === 0 ? "bg-destructive" : !color && "bg-primary")}
          style={{ width: percent + "%", backgroundColor: percent === 0 ? undefined : color }}
        />
      ) : null}
      {limit.pacePercent !== null ? (
        <span
          aria-hidden="true"
          className="absolute -top-[3px] h-[11px] w-0.5 -translate-x-1/2 rounded-[1px] bg-foreground/50"
          style={{ left: limit.pacePercent + "%" }}
        />
      ) : null}
    </div>
  );
}

function LimitMeta({ limit }: { limit: LimitSummary }) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  const countdown = formatResetCountdown(limit.resetAt);
  const text = [countdown ?? limit.caption, limit.stale ? t("dashboard.accounts.stale") : null].filter(Boolean).join(" · ");
  return (
    <span
      className="truncate text-right text-[11.5px] whitespace-nowrap text-muted-foreground tabular-nums"
      title={limit.resetAt ? t("dashboard.remaining.resetsAt", { time: formatDateTimeInline(limit.resetAt, dateDisplayFormat) }) : undefined}
    >
      {text}
    </span>
  );
}

function AccountLogo({ summary, color }: { summary: ProviderSummary; color: string | undefined }) {
  return (
    <span className="relative inline-grid shrink-0">
      <ProviderLogo provider={summary.kind} color={color} size="md" />
      <span
        aria-hidden
        className={cn("absolute -right-[3px] -bottom-[3px] size-[9px] rounded-full border-[1.5px] border-card", DOT[summary.tone])}
      />
    </span>
  );
}

function AccountTitle({ summary, link }: { summary: ProviderSummary; link: boolean }) {
  const { t } = useTranslation();
  const blurred = usePrivacyStore((s) => s.blurred);
  const codex = summary.entry.kind === "codex" ? summary.entry.account : null;
  const name = <span className={cn(summary.blurName && blurred && "privacy-blur")}>{summary.name}</span>;
  return (
    <span className="flex min-w-0 items-center gap-1.5 text-[13.5px] font-semibold whitespace-nowrap">
      {link ? (
        <Link
          to={accountHref(summary.id)}
          title={t("dashboard.accounts.open", { name: summary.name })}
          className="min-w-0 truncate after:absolute after:inset-0 after:content-[''] focus-visible:outline-none"
        >
          {name}
        </Link>
      ) : (
        <span className="min-w-0 truncate">{name}</span>
      )}
      {summary.plan ? <PlanBadge plan={summary.planKey}>{summary.plan}</PlanBadge> : null}
      {codex?.securityWorkAuthorized ? (
        <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-emerald-600" aria-label={t("accounts.actions.trustedAccess")} />
      ) : null}
      {summary.entry.kind === "claude" ? <ExtraUsageBadge account={summary.entry.account} /> : null}
    </span>
  );
}

function AccountSubtitle({ summary }: { summary: ProviderSummary }) {
  const blurred = usePrivacyStore((s) => s.blurred);
  const codex = summary.entry.kind === "codex" ? summary.entry.account : null;
  return (
    <span className="block truncate text-xs text-muted-foreground">
      {PROVIDER_LABELS[summary.kind]}
      {summary.subtitle ? (
        <>
          {" · "}
          <span className={cn(summary.blurSubtitle && blurred && "privacy-blur")}>{summary.subtitle}</span>
        </>
      ) : null}
      {codex?.isEmailDuplicate ? " · ID " + formatCompactAccountId(codex.accountId) : null}
    </span>
  );
}

function ResetCreditButton({ account, actions }: { account: AccountSummary; actions: DashboardAccountActions }) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  const count = account.availableResetCredits ?? 0;
  const status = account.status;
  const blocked = status === "paused" || status === "reauth" || status === "deactivated";
  const expiry = account.resetCreditNearestExpiresAt ? formatTimeRemaining(account.resetCreditNearestExpiresAt) : null;
  const title = blocked
    ? t(status === "paused" ? "dashboard.accounts.resetCreditTitles.resumeRequired" : "dashboard.accounts.resetCreditTitles.reauthRequired")
    : actions.readOnly
      ? t("dashboard.accounts.resetCreditTitles.unavailable")
      : expiry
        ? t("dashboard.accounts.resetCreditTitles.withExpiry", {
            count,
            time: formatDateTimeInline(account.resetCreditNearestExpiresAt, dateDisplayFormat),
          })
        : t("dashboard.accounts.resetCreditTitles.redeem", { count });
  return (
    <Button
      type="button"
      size="xs"
      variant="outline"
      className="relative z-10 h-6 shrink-0 gap-1 bg-card px-2 text-xs font-normal"
      title={title}
      disabled={actions.readOnly || blocked}
      onClick={() => actions.onResetCredit(account)}
    >
      <RotateCcw className="h-3 w-3" aria-hidden />
      {t("dashboard.accounts.resets", { count })}
      {expiry ? (
        <span className={cn("tabular-nums", expiry.expiringSoon ? "font-medium text-destructive" : "text-muted-foreground")}>
          · {expiry.label}
        </span>
      ) : null}
    </Button>
  );
}

/** The remedy for an account that needs attention, when there is one. */
function StripAction({ summary, actions }: { summary: ProviderSummary; actions: DashboardAccountActions }) {
  const { t } = useTranslation();
  if (summary.status === "paused") {
    return (
      <Button
        type="button"
        size="xs"
        variant="outline"
        className="relative z-10 h-[22px] gap-1 bg-card px-2 text-xs font-normal"
        disabled={actions.readOnly}
        onClick={() => actions.onResume(summary)}
      >
        <Play className="h-3 w-3" aria-hidden />
        {t("common.actions.resume")}
      </Button>
    );
  }
  if (summary.status === "reauth" || summary.status === "deactivated") {
    return (
      <Button asChild size="xs" variant="outline" className="relative z-10 h-[22px] gap-1 bg-card px-2 text-xs font-normal">
        <Link to={accountHref(summary.id)}>
          <RotateCcw className="h-3 w-3" aria-hidden />
          {t("common.actions.reauthenticateShort")}
        </Link>
      </Button>
    );
  }
  if (summary.entry.kind === "codex" && summary.resetCredits > 0 && (summary.status === "limited" || summary.status === "exceeded")) {
    return <ResetCreditButton account={summary.entry.account} actions={actions} />;
  }
  return null;
}

function CodexFooter({ account, actions, resetInStrip }: { account: AccountSummary; actions: DashboardAccountActions; resetInStrip: boolean }) {
  const { t } = useTranslation();
  const subscription = Math.max(0, Math.round(accountSubscriptionCredits(account) ?? 0));
  const purchased = Math.max(0, Math.round(account.creditsBalance ?? 0));
  const showCredits = subscription > 0 || purchased > 0 || account.creditsUnlimited;
  const showReset = (account.availableResetCredits ?? 0) > 0 && !resetInStrip;
  if (!showCredits && !showReset) return null;
  return (
    <div className="flex min-h-[34px] items-center gap-2 border-t pt-[9px] text-xs text-muted-foreground" data-testid="account-card-footer">
      {showCredits ? (
        <span className="min-w-0 truncate whitespace-nowrap" title={t("dashboard.accounts.creditsTitle")}>
          {t("dashboard.accounts.credits", {
            subscription: formatNumber(subscription),
            purchased: account.creditsUnlimited ? t("common.states.unlimited") : formatNumber(purchased),
          })}
        </span>
      ) : null}
      <span className="flex-1" />
      {showReset ? <ResetCreditButton account={account} actions={actions} /> : null}
    </div>
  );
}

/** One account of any provider: limits first, then a status strip and footer only when they carry information. */
export function DashboardAccountCard({
  summary,
  color,
  today,
  actions,
}: {
  summary: ProviderSummary;
  color: string | undefined;
  today: string | null;
  actions: DashboardAccountActions;
}) {
  const { t } = useTranslation();
  const dim = summary.status === "paused";
  const codex = summary.entry.kind === "codex" ? summary.entry.account : null;
  const strip = summary.notice;
  const stripAction = strip ? <StripAction summary={summary} actions={actions} /> : null;
  const resetInStrip = !!codex && summary.resetCredits > 0 && (summary.status === "limited" || summary.status === "exceeded");
  return (
    <article
      data-testid="dashboard-account-card"
      data-provider={summary.kind}
      style={{ "--account-color": color ?? "var(--border)" } as CSSProperties}
      className="relative flex min-w-0 flex-col gap-[11px] overflow-hidden rounded-xl border bg-card px-3.5 pt-[13px] pb-[11px] shadow-xs transition-colors before:absolute before:inset-y-0 before:left-0 before:w-[3px] before:bg-[var(--account-color)] hover:border-[color-mix(in_oklch,var(--account-color)_45%,var(--border))]"
    >
      <div className={cn("flex min-w-0 items-center gap-2.5", dim && "opacity-55")}>
        <AccountLogo summary={summary} color={color} />
        <div className="min-w-0 flex-1">
          <AccountTitle summary={summary} link />
          <AccountSubtitle summary={summary} />
        </div>
        {today !== null ? (
          <div className="shrink-0 text-right text-[13px] font-semibold tabular-nums">
            {today}
            <small className="block text-[11px] font-normal text-muted-foreground">{t("dashboard.accounts.today")}</small>
          </div>
        ) : null}
      </div>
      {summary.limits.length > 0 ? (
        <div className={cn("grid grid-cols-[minmax(52px,auto)_minmax(0,1fr)_auto_minmax(64px,auto)] items-center gap-x-2 gap-y-[7px] text-xs", dim && "opacity-55")}>
          {summary.limits.map((limit) => (
            <LimitRow key={limit.key} label={limitLabel(summary, limit)} limit={limit} color={color} />
          ))}
        </div>
      ) : null}
      {strip ? (
        <div
          className={cn("mt-auto flex h-8 items-center gap-[7px] rounded-[7px] pr-[5px] pl-2.5 text-xs font-medium", STRIP[strip.tone])}
          data-testid="account-card-strip"
        >
          <span className="min-w-0 truncate" title={strip.text}>
            {strip.label}
          </span>
          <span className="flex-1" />
          {stripAction}
        </div>
      ) : null}
      {codex ? (
        <div className={cn(!strip && "mt-auto")}>
          <CodexFooter account={codex} actions={actions} resetInStrip={resetInStrip} />
        </div>
      ) : null}
    </article>
  );
}

function LimitRow({ label, limit, color }: { label: string; limit: LimitSummary; color: string | undefined }): ReactNode {
  return (
    <>
      <span className="truncate text-muted-foreground">{label}</span>
      <LimitFill limit={limit} color={color} />
      <span className={cn("text-right font-semibold whitespace-nowrap tabular-nums", limit.percentLeft === 0 && "text-destructive")}>
        {limit.value}
      </span>
      <LimitMeta limit={limit} />
    </>
  );
}

function NoAccounts() {
  const { t } = useTranslation();
  return (
    <EmptyState
      icon={Users}
      title={t("dashboard.accounts.emptyTitle")}
      description={t("dashboard.accounts.emptyDescription")}
      action={
        <Button asChild size="sm">
          <Link to="/providers">{t("dashboard.accounts.emptyAction")}</Link>
        </Button>
      }
    />
  );
}

export function DashboardAccountCards({ summaries, colors, activity, activityAvailable, actions }: DashboardAccountsProps) {
  if (summaries.length === 0) return <NoAccounts />;
  return (
    <div data-testid="dashboard-account-cards" className="grid grid-cols-[repeat(auto-fill,minmax(min(300px,100%),1fr))] gap-3">
      {summaries.map((summary) => (
        <DashboardAccountCard
          key={summary.kind + ":" + summary.id}
          summary={summary}
          color={summaryColor(summary, colors)}
          today={todayCost(summary, activity, activityAvailable)}
          actions={actions}
        />
      ))}
    </div>
  );
}

function ListLimit({ limit, label, color }: { limit: LimitSummary | undefined; label: string; color: string | undefined }) {
  if (!limit) return <div className="hidden lg:block" />;
  return (
    <div className="min-w-0">
      <div className="mb-1 flex min-w-0 items-baseline justify-between gap-2 text-xs">
        <b className={cn("font-semibold tabular-nums", limit.percentLeft === 0 && "text-destructive")}>{limit.value}</b>
        <span className="flex min-w-0 items-baseline gap-1 text-muted-foreground">
          <span className="truncate">{label} ·</span>
          <LimitMeta limit={limit} />
        </span>
      </div>
      <LimitFill limit={limit} color={color} />
    </div>
  );
}

const LIST_GRID =
  "grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 px-4 lg:grid-cols-[minmax(12.5rem,1.5fr)_minmax(8rem,.9fr)_minmax(9.5rem,1fr)_minmax(9.5rem,1fr)_5.5rem]";

export function DashboardAccountList({ summaries, colors, activity, activityAvailable, actions }: DashboardAccountsProps) {
  const { t } = useTranslation();
  if (summaries.length === 0) return <NoAccounts />;
  return (
    <div role="table" data-testid="dashboard-account-list" className="overflow-hidden rounded-xl border bg-card shadow-xs">
      <div role="row" className={cn(LIST_GRID, "hidden border-b py-2 text-[11.5px] font-medium text-muted-foreground lg:grid")}>
        <span role="columnheader">{t("providers.list.account")}</span>
        <span role="columnheader">{t("providers.list.status")}</span>
        <span role="columnheader" className="col-span-2">
          {t("providers.list.limits")}
        </span>
        <span role="columnheader" className="text-right">
          {t("providers.list.today")}
        </span>
      </div>
      {summaries.map((summary) => {
        const color = summaryColor(summary, colors);
        const today = todayCost(summary, activity, activityAvailable);
        const [first, second] = summary.limits;
        return (
          <div
            role="row"
            key={summary.kind + ":" + summary.id}
            data-testid="dashboard-account-row"
            className={cn(LIST_GRID, "relative border-b py-2.5 text-[12.5px] last:border-b-0 hover:bg-accent/60")}
          >
            <div className={cn("flex min-w-0 items-center gap-2.5", summary.status === "paused" && "opacity-55")}>
              <AccountLogo summary={summary} color={color} />
              <div className="min-w-0">
                <AccountTitle summary={summary} link />
                <span className="block truncate text-xs text-muted-foreground">{PROVIDER_LABELS[summary.kind]}</span>
              </div>
            </div>
            <div className="relative z-10 flex min-w-0 items-center gap-2 justify-self-end lg:justify-self-start">
              <div className="min-w-0">
                <StatusBadge status={summary.status} />
                {summary.notice ? (
                  <span className={cn("mt-0.5 block max-w-48 truncate text-[11px]", noticeClass(summary.notice.tone))} title={summary.notice.text}>
                    {summary.notice.label}
                  </span>
                ) : null}
              </div>
              <StripAction summary={summary} actions={actions} />
            </div>
            <div className="col-span-2 grid gap-2 sm:grid-cols-2 lg:contents">
              <ListLimit limit={first} label={first ? limitLabel(summary, first) : ""} color={color} />
              <ListLimit limit={second} label={second ? limitLabel(summary, second) : ""} color={color} />
            </div>
            <span className="hidden text-right font-semibold tabular-nums lg:block">{today ?? "—"}</span>
          </div>
        );
      })}
    </div>
  );
}
