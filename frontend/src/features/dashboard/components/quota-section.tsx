import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { ProviderLogo } from "@/components/brand/provider-account-name";
import { ChartToggle } from "@/components/chart-toggle";
import type { AntigravityAccount } from "@/features/antigravity/api";
import { FAMILY_LABELS } from "@/features/antigravity/display-values";
import type { ClaudeAccount } from "@/features/claude/api";
import { AntigravityQuotaBarsCard } from "@/features/dashboard/components/antigravity-quota-bars";
import { TopConsumersCard } from "@/features/dashboard/components/top-consumers-card";
import { UsageDonuts } from "@/features/dashboard/components/usage-donuts";
import { WeeklyCreditsPaceCard } from "@/features/dashboard/components/weekly-credits-pace-card";
import {
  buildAntigravityQuotaBars,
  buildClaudeQuotaRing,
  tightestAntigravityPace,
  type DashboardView,
  type QuotaProvider,
} from "@/features/dashboard/utils";
import { useDashboardPreferencesStore } from "@/hooks/use-dashboard-preferences";

export type QuotaSectionProps = {
  view: DashboardView;
  primaryCapacityCredits: number;
  secondaryCapacityCredits: number;
  claudeAccounts: ClaudeAccount[];
  antigravityAccounts: AntigravityAccount[];
  /** Chart colours by model-source account ID (Claude and Antigravity). */
  modelSourceColors: ReadonlyMap<string, string>;
};

type Translate = ReturnType<typeof useTranslation>["t"];

type NotPooled = {
  planUnknown?: string[];
  planUnweighted?: string[];
  quotaUnknown: string[];
};

function notPooledNote(t: Translate, { planUnknown = [], planUnweighted = [], quotaUnknown }: NotPooled): string | undefined {
  const reasons = [
    planUnknown.length > 0 ? t("dashboard.usage.notPooledPlanUnknown", { names: planUnknown.join(", ") }) : null,
    planUnweighted.length > 0 ? t("dashboard.usage.notPooledPlanUnweighted", { names: planUnweighted.join(", ") }) : null,
    quotaUnknown.length > 0 ? t("dashboard.usage.notPooledQuotaUnknown", { names: quotaUnknown.join(", ") }) : null,
  ].filter((reason): reason is string => reason !== null);
  const count = planUnknown.length + planUnweighted.length + quotaUnknown.length;
  return count === 0 ? undefined : t("dashboard.usage.notPooled", { count, reasons: reasons.join(" · ") });
}

export function QuotaSection({
  view,
  primaryCapacityCredits,
  secondaryCapacityCredits,
  claudeAccounts,
  antigravityAccounts,
  modelSourceColors,
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

  const fiveHourRing = useMemo(
    () => buildClaudeQuotaRing(claudeAccounts, "five_hour", modelSourceColors),
    [claudeAccounts, modelSourceColors],
  );
  const weeklyRing = useMemo(
    () => buildClaudeQuotaRing(claudeAccounts, "seven_day", modelSourceColors),
    [claudeAccounts, modelSourceColors],
  );
  const fiveHourBars = useMemo(
    () => buildAntigravityQuotaBars(antigravityAccounts, "five_hour", modelSourceColors),
    [antigravityAccounts, modelSourceColors],
  );
  const weeklyBars = useMemo(
    () => buildAntigravityQuotaBars(antigravityAccounts, "weekly", modelSourceColors),
    [antigravityAccounts, modelSourceColors],
  );
  const antigravityPace = tightestAntigravityPace(view.antigravityWeeklyPace);

  return (
    <section className="space-y-4" data-testid="quota-section" data-provider={provider}>
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-[13px] font-medium uppercase tracking-wider text-muted-foreground">
          {t("dashboard.quota.title")}
        </h2>
        <div className="h-px min-w-8 flex-1 bg-border" />
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
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {provider === "codex" ? (
          <>
            <UsageDonuts
              provider="codex"
              primaryItems={view.primaryUsageItems}
              secondaryItems={view.secondaryUsageItems}
              primaryTotal={primaryCapacityCredits}
              secondaryTotal={secondaryCapacityCredits}
              primaryCenterValue={view.primaryTotal}
              secondaryCenterValue={view.secondaryTotal}
              safeLinePrimary={view.safeLinePrimary}
              safeLineSecondary={view.safeLineSecondary}
            />
            <WeeklyCreditsPaceCard pace={view.weeklyCreditPace} subtitle={t("dashboard.weeklyPace.subtitleCodex")} />
            <TopConsumersCard provider="codex" consumers={view.topConsumers.codex} />
          </>
        ) : provider === "claude" ? (
          <>
            <UsageDonuts
              provider="claude"
              primaryItems={fiveHourRing.items}
              secondaryItems={weeklyRing.items}
              primaryTotal={fiveHourRing.total}
              secondaryTotal={weeklyRing.total}
              primaryCenterValue={fiveHourRing.remaining}
              secondaryCenterValue={weeklyRing.remaining}
              primaryNote={notPooledNote(t, fiveHourRing)}
              secondaryNote={notPooledNote(t, weeklyRing)}
            />
            <WeeklyCreditsPaceCard pace={view.claudeWeeklyPace} subtitle={t("dashboard.weeklyPace.subtitleClaude")} />
            <TopConsumersCard provider="claude" consumers={view.topConsumers.claude} />
          </>
        ) : (
          <>
            <AntigravityQuotaBarsCard
              title={t("dashboard.usage.fiveHourQuota")}
              bars={fiveHourBars}
              note={notPooledNote(t, fiveHourBars)}
            />
            <AntigravityQuotaBarsCard
              title={t("dashboard.usage.weeklyQuota")}
              bars={weeklyBars}
              note={notPooledNote(t, weeklyBars)}
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
            <TopConsumersCard provider="antigravity" consumers={view.topConsumers.antigravity} />
          </>
        )}
      </div>
    </section>
  );
}

