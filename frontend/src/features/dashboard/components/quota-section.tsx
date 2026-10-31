import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { ProviderLogo } from "@/components/brand/provider-account-name";
import { ChartToggle } from "@/components/chart-toggle";
import type { ProviderSummary } from "@/features/accounts/provider-summary";
import type { AntigravityAccount } from "@/features/antigravity/api";
import { FAMILY_LABELS } from "@/features/antigravity/display-values";
import type { KeyColors } from "@/features/apis/key-summary";
import type { ClaudeAccount } from "@/features/claude/api";
import { AntigravityRemainingCard } from "@/features/dashboard/components/antigravity-remaining-card";
import {
  QuotaRemainingCard,
  type RemainingCell,
  type RemainingRow,
} from "@/features/dashboard/components/quota-remaining-card";
import { TopConsumersCard } from "@/features/dashboard/components/top-consumers-card";
import { WeeklyCreditsPaceCard } from "@/features/dashboard/components/weekly-credits-pace-card";
import type { AccountSummary } from "@/features/dashboard/schemas";
import {
  buildAntigravityQuotaBars,
  buildClaudeQuotaRing,
  formatProUnits,
  tightestAntigravityPace,
  type DashboardView,
  type QuotaProvider,
  type RemainingItem,
} from "@/features/dashboard/utils";
import { useDashboardPreferencesStore } from "@/hooks/use-dashboard-preferences";
import { formatCompactNumber } from "@/utils/formatters";

export type QuotaSectionProps = {
  view: DashboardView;
  codexAccounts: AccountSummary[];
  primaryCapacityCredits: number;
  secondaryCapacityCredits: number;
  claudeAccounts: ClaudeAccount[];
  antigravityAccounts: AntigravityAccount[];
  /** Account summaries by account ID, with both quota windows. */
  summaries: ReadonlyMap<string, ProviderSummary>;
  /** Chart colours by model-source account ID (Claude and Antigravity). */
  modelSourceColors: ReadonlyMap<string, string>;
  keyColors: KeyColors;
};

type Translate = ReturnType<typeof useTranslation>["t"];

type NotPooled = {
  planUnknown?: string[];
  planUnweighted?: string[];
  quotaUnknown: string[];
};

function notPooledNote(t: Translate, { planUnknown = [], planUnweighted = [], quotaUnknown }: NotPooled): string | null {
  const reasons = [
    planUnknown.length > 0 ? t("dashboard.usage.notPooledPlanUnknown", { names: planUnknown.join(", ") }) : null,
    planUnweighted.length > 0 ? t("dashboard.usage.notPooledPlanUnweighted", { names: planUnweighted.join(", ") }) : null,
    quotaUnknown.length > 0 ? t("dashboard.usage.notPooledQuotaUnknown", { names: quotaUnknown.join(", ") }) : null,
  ].filter((reason): reason is string => reason !== null);
  const count = planUnknown.length + planUnweighted.length + quotaUnknown.length;
  return count === 0 ? null : t("dashboard.usage.notPooled", { count, reasons: reasons.join(" · ") });
}

/** Window notes, labelled by window when both have one. */
function windowNotes(t: Translate, fiveHour: string | null, weekly: string | null): string[] {
  if (fiveHour && weekly) {
    return fiveHour === weekly
      ? [fiveHour]
      : [t("dashboard.remaining.fiveHours") + ": " + fiveHour, t("dashboard.remaining.weekly") + ": " + weekly];
  }
  return [fiveHour, weekly].filter((note): note is string => note !== null);
}

function limitReset(summary: ProviderSummary | undefined, key: string): string | null {
  return summary?.limits.find((limit) => limit.key === key)?.resetAt ?? null;
}

function cellOf(items: Map<string, RemainingItem>, id: string, resetAt: string | null, missing: string): RemainingCell {
  const item = items.get(id);
  return item ? { value: item.value, resetAt } : { missing };
}

function byId(items: RemainingItem[]): Map<string, RemainingItem> {
  return new Map(items.map((item) => [item.accountId, item]));
}

export function QuotaSection({
  view,
  codexAccounts,
  primaryCapacityCredits,
  secondaryCapacityCredits,
  claudeAccounts,
  antigravityAccounts,
  summaries,
  modelSourceColors,
  keyColors,
}: QuotaSectionProps) {
  const { t } = useTranslation();
  const preferredProvider = useDashboardPreferencesStore((s) => s.quotaProvider);
  const setQuotaProvider = useDashboardPreferencesStore((s) => s.setQuotaProvider);
  const providers: QuotaProvider[] = [
    "codex",
    ...(claudeAccounts.length > 0 ? (["claude"] as const) : []),
    ...(antigravityAccounts.length > 0 ? (["antigravity"] as const) : []),
  ];
  const provider: QuotaProvider = providers.includes(preferredProvider) ? preferredProvider : "codex";

  const codexRows = useMemo((): RemainingRow[] => {
    const fiveHour = byId(view.primaryUsageItems);
    const weekly = byId(view.secondaryUsageItems);
    return codexAccounts.map((account) => {
      const summary = summaries.get(account.accountId);
      const monthlyOnly = !weekly.has(account.accountId) && !fiveHour.has(account.accountId);
      return {
        id: account.accountId,
        name: summary?.name ?? account.email,
        blurName: summary?.blurName ?? true,
        provider: "codex",
        color: weekly.get(account.accountId)?.color ?? fiveHour.get(account.accountId)?.color,
        fiveHour: cellOf(
          fiveHour,
          account.accountId,
          limitReset(summary, "5h"),
          t(monthlyOnly ? "dashboard.remaining.monthlyPlan" : "dashboard.remaining.noLimit"),
        ),
        weekly: cellOf(weekly, account.accountId, limitReset(summary, "weekly"), t("dashboard.remaining.monthlyPlan")),
      };
    });
  }, [codexAccounts, summaries, t, view.primaryUsageItems, view.secondaryUsageItems]);

  const claude = useMemo(() => {
    const fiveHour = buildClaudeQuotaRing(claudeAccounts, "five_hour", modelSourceColors);
    const weekly = buildClaudeQuotaRing(claudeAccounts, "seven_day", modelSourceColors);
    const fiveHourItems = byId(fiveHour.items);
    const weeklyItems = byId(weekly.items);
    const rows = claudeAccounts.map((account): RemainingRow => {
      const summary = summaries.get(account.id);
      const hasFiveHour = account.quota.windows.some((window) => window.name === "five_hour");
      return {
        id: account.id,
        name: account.name,
        blurName: summary?.blurName ?? true,
        provider: "claude",
        color: modelSourceColors.get(account.id),
        fiveHour: cellOf(
          fiveHourItems,
          account.id,
          limitReset(summary, "5h"),
          t(hasFiveHour ? "dashboard.remaining.notPooled" : "dashboard.remaining.noLimit"),
        ),
        weekly: cellOf(weeklyItems, account.id, limitReset(summary, "weekly"), t("dashboard.remaining.notPooled")),
      };
    });
    return { fiveHour, weekly, rows };
  }, [claudeAccounts, modelSourceColors, summaries, t]);

  const antigravity = useMemo(
    () => ({
      fiveHour: buildAntigravityQuotaBars(antigravityAccounts, "five_hour", modelSourceColors),
      weekly: buildAntigravityQuotaBars(antigravityAccounts, "weekly", modelSourceColors),
    }),
    [antigravityAccounts, modelSourceColors],
  );
  const antigravityPace = tightestAntigravityPace(view.antigravityWeeklyPace);

  return (
    <section className="flex flex-col gap-2.5" data-testid="quota-section" data-provider={provider}>
      <div className="flex min-h-[30px] flex-wrap items-center gap-2.5">
        <h2 className="text-sm font-semibold">{t("dashboard.quota.title")}</h2>
        <span className="flex-1" />
        {providers.length > 1 ? (
          <ChartToggle
            label={t("dashboard.quota.provider")}
            value={provider}
            onChange={setQuotaProvider}
            options={providers.map((option) => ({
              value: option,
              label: t("dashboard.quota." + option),
              icon: <ProviderLogo provider={option} />,
            }))}
          />
        ) : null}
      </div>
      <div className="@container/quota">
        <div className="grid gap-4 @min-[44rem]/quota:grid-cols-2 @min-[74rem]/quota:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)_minmax(0,1fr)]">
          {provider === "codex" ? (
            <>
              <QuotaRemainingCard
                title={t("dashboard.remaining.creditsTitle")}
                subtitle={t("dashboard.usage.subtitleCodex")}
                format={formatCompactNumber}
                fiveHour={{
                  items: view.primaryUsageItems,
                  total: primaryCapacityCredits,
                  remaining: view.primaryTotal,
                  safeLine: view.safeLinePrimary,
                }}
                weekly={{
                  items: view.secondaryUsageItems,
                  total: secondaryCapacityCredits,
                  remaining: view.secondaryTotal,
                  safeLine: view.safeLineSecondary,
                }}
                rows={codexRows}
                notes={[]}
              />
              <WeeklyCreditsPaceCard pace={view.weeklyCreditPace} subtitle={t("dashboard.weeklyPace.subtitleCodex")} />
              <TopConsumersCard provider="codex" consumers={view.topConsumers.codex} keyColors={keyColors} />
            </>
          ) : provider === "claude" ? (
            <>
              <QuotaRemainingCard
                title={t("dashboard.remaining.quotaTitle")}
                subtitle={t("dashboard.usage.subtitleClaude")}
                format={formatProUnits}
                fiveHour={claude.fiveHour}
                weekly={claude.weekly}
                rows={claude.rows}
                notes={windowNotes(t, notPooledNote(t, claude.fiveHour), notPooledNote(t, claude.weekly))}
              />
              <WeeklyCreditsPaceCard pace={view.claudeWeeklyPace} subtitle={t("dashboard.weeklyPace.subtitleClaude")} />
              <TopConsumersCard provider="claude" consumers={view.topConsumers.claude} keyColors={keyColors} />
            </>
          ) : (
            <>
              <AntigravityRemainingCard
                title={t("dashboard.remaining.quotaTitle")}
                subtitle={t("dashboard.usage.subtitleAntigravity")}
                fiveHour={antigravity.fiveHour}
                weekly={antigravity.weekly}
                notes={windowNotes(t, notPooledNote(t, antigravity.fiveHour), notPooledNote(t, antigravity.weekly))}
              />
              {antigravityPace ? (
                <WeeklyCreditsPaceCard
                  pace={antigravityPace.pace}
                  subtitle={t("dashboard.weeklyPace.subtitleAntigravity", {
                    family: FAMILY_LABELS[antigravityPace.family],
                  })}
                  breakdown={
                    view.antigravityWeeklyPace.length > 1
                      ? view.antigravityWeeklyPace.map((entry) => ({
                          key: entry.family,
                          label: FAMILY_LABELS[entry.family],
                          pace: entry.pace,
                          emphasized: entry.family === antigravityPace.family,
                        }))
                      : undefined
                  }
                />
              ) : null}
              <TopConsumersCard provider="antigravity" consumers={view.topConsumers.antigravity} keyColors={keyColors} />
            </>
          )}
        </div>
      </div>
    </section>
  );
}
