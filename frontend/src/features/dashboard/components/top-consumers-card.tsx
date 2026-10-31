import { useTranslation } from "react-i18next";

import { KeySparkline } from "@/features/apis/components/key-parts";
import { keySeriesId, type KeyColors } from "@/features/apis/key-summary";
import { formatCoveredCost, formatCoveredCostShort } from "@/features/dashboard/cost-coverage";
import type { QuotaProvider, WeeklyCreditApiKeyAttribution } from "@/features/dashboard/utils";
import { formatCompactNumber, formatModelLabel } from "@/utils/formatters";

export type TopConsumersCardProps = {
  provider: QuotaProvider;
  consumers: WeeklyCreditApiKeyAttribution[];
  /** API-key colours of the API Keys page; empty when the user cannot read keys. */
  keyColors: KeyColors;
};

const SUBTITLE_KEYS: Record<QuotaProvider, string> = {
  codex: "dashboard.topConsumers.subtitleCodex",
  claude: "dashboard.topConsumers.subtitleClaude",
  antigravity: "dashboard.topConsumers.subtitleAntigravity",
};

const ROW_GRID = "grid grid-cols-[minmax(0,1fr)_72px_58px] items-center gap-3";

/** The API keys that used the provider most in the last two hours, with their cost over that window. */
export function TopConsumersCard({ provider, consumers, keyColors }: TopConsumersCardProps) {
  const { t } = useTranslation();

  return (
    <section
      className="flex min-w-0 flex-col gap-3.5 rounded-xl border bg-card px-[18px] py-4"
      aria-label={t("dashboard.topConsumers.title")}
      data-testid="top-consumers-card"
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold">{t("dashboard.topConsumers.title")}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">{t(SUBTITLE_KEYS[provider])}</p>
        </div>
        <p className="ml-auto shrink-0 text-[11.5px] text-muted-foreground" title={t("dashboard.topConsumers.costDescription")}>
          {t("dashboard.topConsumers.cost")}
        </p>
      </div>

      {consumers.length === 0 ? (
        <p className="py-5 text-center text-[12.5px] text-muted-foreground">{t("dashboard.topConsumers.empty")}</p>
      ) : (
        <div className="flex flex-col gap-2.5">
          <ol className="flex flex-col gap-2.5">
            {consumers.map((consumer, index) => {
              const color = consumer.apiKeyId ? keyColors.get(keySeriesId(consumer.apiKeyId)) : undefined;
              return (
                <li
                  // Key names are not unique; unattributed rows carry no id.
                  key={consumer.apiKeyId ?? consumer.name + "-" + index}
                  className={ROW_GRID + " border-b pb-2.5 text-[12.5px] last:border-b-0 last:pb-0"}
                  data-testid="top-consumer-row"
                >
                  <span className="min-w-0">
                    <span className="flex min-w-0 items-center gap-1.5 font-medium" title={formatModelLabel(consumer.dominantModel, null)}>
                      <span className="w-3 shrink-0 text-[11px] text-muted-foreground tabular-nums">{index + 1}</span>
                      <span
                        aria-hidden
                        className="h-2 w-2 shrink-0 rounded-[2px] bg-muted-foreground"
                        style={color ? { backgroundColor: color } : undefined}
                      />
                      <span className="truncate">{consumer.name}</span>
                    </span>
                    <span className="mt-0.5 block truncate pl-[26px] text-[11.5px] text-muted-foreground tabular-nums">
                      {t("dashboard.topConsumers.requests", { value: formatCompactNumber(consumer.requests) })}
                      {" · "}
                      {t("dashboard.topConsumers.tokens", { value: formatCompactNumber(consumer.billableTokens) })}
                    </span>
                  </span>
                  <KeySparkline buckets={consumer.costBuckets} color={color ?? "var(--muted-foreground)"} />
                  <span
                    className="text-right font-semibold tabular-nums"
                    title={t("dashboard.topConsumers.costTooltip", {
                      cost: formatCoveredCost(consumer.costCoverage.knownCostUsd, consumer.costCoverage),
                    })}
                  >
                    {formatCoveredCostShort(consumer.costCoverage.knownCostUsd, consumer.costCoverage)}
                  </span>
                </li>
              );
            })}
          </ol>
          <div className={ROW_GRID + " -mt-1 text-[10px] text-muted-foreground"} aria-hidden>
            <span />
            <span className="flex justify-between">
              <span>{t("dashboard.topConsumers.axisStart")}</span>
              <span>{t("dashboard.topConsumers.axisEnd")}</span>
            </span>
            <span />
          </div>
        </div>
      )}
    </section>
  );
}
