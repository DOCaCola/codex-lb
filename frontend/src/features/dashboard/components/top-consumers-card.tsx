import { useTranslation } from "react-i18next";

import { formatCoveredCost, formatCoveredCostShort } from "@/features/dashboard/cost-coverage";
import type { QuotaProvider, WeeklyCreditApiKeyAttribution } from "@/features/dashboard/utils";
import { formatCompactNumber, formatModelLabel } from "@/utils/formatters";

export type TopConsumersCardProps = {
  provider: QuotaProvider;
  consumers: WeeklyCreditApiKeyAttribution[];
};

export function TopConsumersCard({ provider, consumers }: TopConsumersCardProps) {
  const { t } = useTranslation();

  return (
    <section
      className="@container/top-consumers min-w-0 rounded-xl border bg-card p-5"
      aria-label={t("dashboard.topConsumers.title")}
      data-testid="top-consumers-card"
    >
      <div className="mb-4 flex justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold">{t("dashboard.topConsumers.title")}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {t(provider === "codex" ? "dashboard.topConsumers.subtitleCodex" : "dashboard.topConsumers.subtitleClaude")}
          </p>
        </div>
        <p
          className="shrink-0 text-[11px] font-medium text-muted-foreground"
          title={t("dashboard.topConsumers.costDescription")}
        >
          {t("dashboard.topConsumers.cost")}
        </p>
      </div>

      {consumers.length === 0 ? (
        <p className="text-xs text-muted-foreground">{t("dashboard.topConsumers.empty")}</p>
      ) : (
        <ul className="space-y-1.5">
          {consumers.map((apiKey, index) => (
            <li
              // Key names are not unique; unattributed rows carry no id.
              key={apiKey.apiKeyId ?? `${apiKey.name}-${index}`}
              // Respond to the card's width, not the viewport: the card is one
              // column of the quota grid even on a large dashboard.
              className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 text-xs text-muted-foreground @min-[20rem]/top-consumers:grid @min-[20rem]/top-consumers:grid-cols-[minmax(0,1fr)_auto_auto_auto]"
            >
              <span className="w-full min-w-0 @min-[20rem]/top-consumers:w-auto">
                <span className="block truncate font-medium text-foreground">{apiKey.name}</span>
                <span className="block truncate text-[10px] text-foreground/70">
                  {formatModelLabel(apiKey.dominantModel, null)}
                </span>
              </span>
              <span className="tabular-nums @min-[20rem]/top-consumers:text-right">
                {t("dashboard.topConsumers.requests", { value: formatCompactNumber(apiKey.requests) })}
              </span>
              <span className="tabular-nums @min-[20rem]/top-consumers:text-right">
                {t("dashboard.topConsumers.tokens", { value: formatCompactNumber(apiKey.billableTokens) })}
              </span>
              <span
                className="ml-auto max-w-full break-words text-right tabular-nums text-foreground/70"
                title={t("dashboard.topConsumers.costTooltip", {
                  cost: formatCoveredCost(apiKey.costCoverage.knownCostUsd, apiKey.costCoverage),
                })}
              >
                {formatCoveredCostShort(apiKey.costCoverage.knownCostUsd, apiKey.costCoverage)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
