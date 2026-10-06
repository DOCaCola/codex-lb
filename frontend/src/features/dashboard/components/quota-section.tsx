import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { ProviderLogo } from "@/components/brand/provider-account-name";
import { ChartToggle } from "@/components/chart-toggle";
import type { ClaudeAccount } from "@/features/claude/api";
import { TopConsumersCard } from "@/features/dashboard/components/top-consumers-card";
import { UsageDonuts } from "@/features/dashboard/components/usage-donuts";
import { WeeklyCreditsPaceCard } from "@/features/dashboard/components/weekly-credits-pace-card";
import {
  buildClaudeQuotaRing,
  type ClaudeQuotaRing,
  type DashboardView,
  type QuotaProvider,
} from "@/features/dashboard/utils";
import { useDashboardPreferencesStore } from "@/hooks/use-dashboard-preferences";

export type QuotaSectionProps = {
  view: DashboardView;
  primaryCapacityCredits: number;
  secondaryCapacityCredits: number;
  claudeAccounts: ClaudeAccount[];
  /** Chart colours by Claude account ID. */
  claudeAccountColors: ReadonlyMap<string, string>;
};

function useNotPooledNote(ring: ClaudeQuotaRing): string | undefined {
  const { t } = useTranslation();
  const count = ring.planUnknown.length + ring.quotaUnknown.length;
  if (count === 0) {
    return undefined;
  }
  const reasons = [
    ring.planUnknown.length > 0
      ? t("dashboard.usage.notPooledPlanUnknown", { names: ring.planUnknown.join(", ") })
      : null,
    ring.quotaUnknown.length > 0
      ? t("dashboard.usage.notPooledQuotaUnknown", { names: ring.quotaUnknown.join(", ") })
      : null,
  ].filter((reason): reason is string => reason !== null);
  return t("dashboard.usage.notPooled", { count, reasons: reasons.join(" · ") });
}

export function QuotaSection({
  view,
  primaryCapacityCredits,
  secondaryCapacityCredits,
  claudeAccounts,
  claudeAccountColors,
}: QuotaSectionProps) {
  const { t } = useTranslation();
  const preferredProvider = useDashboardPreferencesStore((s) => s.quotaProvider);
  const setQuotaProvider = useDashboardPreferencesStore((s) => s.setQuotaProvider);
  const hasClaude = claudeAccounts.length > 0;
  const provider: QuotaProvider = hasClaude ? preferredProvider : "codex";

  const fiveHourRing = useMemo(
    () => buildClaudeQuotaRing(claudeAccounts, "five_hour", claudeAccountColors),
    [claudeAccounts, claudeAccountColors],
  );
  const weeklyRing = useMemo(
    () => buildClaudeQuotaRing(claudeAccounts, "seven_day", claudeAccountColors),
    [claudeAccounts, claudeAccountColors],
  );
  const fiveHourNote = useNotPooledNote(fiveHourRing);
  const weeklyNote = useNotPooledNote(weeklyRing);

  return (
    <section className="space-y-4" data-testid="quota-section" data-provider={provider}>
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-[13px] font-medium uppercase tracking-wider text-muted-foreground">
          {t("dashboard.quota.title")}
        </h2>
        <div className="h-px min-w-8 flex-1 bg-border" />
        {hasClaude ? (
          <ChartToggle
            label={t("dashboard.quota.provider")}
            value={provider}
            onChange={setQuotaProvider}
            options={[
              { value: "codex", label: t("dashboard.quota.codex"), icon: <ProviderLogo provider="codex" /> },
              { value: "claude", label: t("dashboard.quota.claude"), icon: <ProviderLogo provider="claude" /> },
            ]}
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
            <WeeklyCreditsPaceCard pace={view.weeklyCreditPace} />
            <TopConsumersCard provider="codex" consumers={view.topConsumers.codex} />
          </>
        ) : (
          <>
            <UsageDonuts
              provider="claude"
              primaryItems={fiveHourRing.items}
              secondaryItems={weeklyRing.items}
              primaryTotal={fiveHourRing.total}
              secondaryTotal={weeklyRing.total}
              primaryCenterValue={fiveHourRing.remaining}
              secondaryCenterValue={weeklyRing.remaining}
              primaryNote={fiveHourNote}
              secondaryNote={weeklyNote}
            />
            <WeeklyCreditsPaceCard pace={view.claudeWeeklyPace} />
            <TopConsumersCard provider="claude" consumers={view.topConsumers.claude} />
          </>
        )}
      </div>
    </section>
  );
}
