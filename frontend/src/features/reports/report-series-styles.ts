import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import type { AccountProvider } from "@/components/brand/account-provider";
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { useThemeStore } from "@/hooks/use-theme";
import { buildDonutPalette } from "@/utils/colors";

import { accountFilterKey, type AccountIdentity } from "./report-model";
import type { ReportsResponse } from "./schemas";

/** User-agent bucket of requests that sent none; drawn grey instead of taking a palette colour. */
export const MISSING_USER_AGENT = "Missing User-Agent";

export const UNATTRIBUTED_ACCOUNT_KEY = "unattributed";

export type SeriesStyle = {
  label: string;
  color: string;
  provider: AccountProvider | null;
};

export type AccountSeries = SeriesStyle & {
  /** Account filter key; null for usage whose account no longer exists. */
  filterKey: string | null;
};

export type ReportSeriesStyles = {
  neutral: string;
  palette: string[];
  account: (identity: AccountIdentity & { provider: AccountProvider | null; name: string | null }) => AccountSeries;
  model: (model: string) => SeriesStyle;
  useragent: (useragent: string) => SeriesStyle;
};

/**
 * Accounts keep their chart colour; models and user agents take palette
 * colours by their cost rank in the report, so the trend and the breakdown
 * agree on them.
 */
export function useReportSeriesStyles(report: ReportsResponse | undefined): ReportSeriesStyles {
  const { t } = useTranslation();
  const isDark = useThemeStore((state) => state.theme === "dark");
  const accountColors = useAccountColorHexes();
  return useMemo(() => {
    const neutral = isDark ? "#525252" : "#cbd5e1";
    const models = report?.byModel.map((entry) => entry.model) ?? [];
    const useragents = (report?.byUseragent ?? [])
      .map((entry) => entry.useragent)
      .filter((useragent) => useragent !== MISSING_USER_AGENT);
    const palette = buildDonutPalette(Math.max(6, models.length, useragents.length), isDark);
    const modelIndex = new Map(models.map((model, index) => [model, index]));
    const useragentIndex = new Map(useragents.map((useragent, index) => [useragent, index]));
    return {
      neutral,
      palette,
      account: (identity) => {
        const filterKey = accountFilterKey(identity);
        const color = identity.modelSourceId
          ? accountColors.modelSources.get(identity.modelSourceId)
          : identity.accountId
            ? accountColors.accounts.get(identity.accountId)
            : undefined;
        return {
          filterKey,
          label: filterKey ? (identity.name ?? identity.modelSourceId ?? identity.accountId ?? "") : t("reports.unattributed"),
          color: color ?? neutral,
          provider: filterKey ? identity.provider : null,
        };
      },
      model: (model) => {
        const index = modelIndex.get(model);
        return { label: model, color: index === undefined ? neutral : palette[index], provider: null };
      },
      useragent: (useragent) => {
        const index = useragentIndex.get(useragent);
        return {
          label: useragent,
          color: index === undefined ? neutral : palette[index],
          provider: null,
        };
      },
    };
  }, [accountColors, isDark, report, t]);
}
