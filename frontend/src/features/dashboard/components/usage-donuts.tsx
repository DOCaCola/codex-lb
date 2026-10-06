import { lazy, Suspense } from "react";
import { useTranslation } from "react-i18next";

import type { DonutChartItem, DonutChartProps } from "@/components/donut-chart";
import { formatProUnits, type QuotaProvider, type RemainingItem, type SafeLineView } from "@/features/dashboard/utils";

const DonutChart = lazy(() =>
  import("@/components/donut-chart").then((module) => ({
    default: (props: DonutChartProps) => <module.DonutChart {...props} />,
  })),
);

export type UsageDonutsProps = {
	provider: QuotaProvider;
	primaryItems: RemainingItem[];
	secondaryItems: RemainingItem[];
	primaryTotal: number;
	secondaryTotal: number;
	primaryCenterValue?: number;
	secondaryCenterValue?: number;
	safeLinePrimary?: SafeLineView | null;
	safeLineSecondary?: SafeLineView | null;
	primaryNote?: string;
	secondaryNote?: string;
};

function chartItems(items: RemainingItem[]): DonutChartItem[] {
	return items.map((item) => ({
		id: item.accountId,
		label: item.label,
		labelSuffix: item.labelSuffix,
		isEmail: item.isEmail,
		value: item.value,
		color: item.color,
	}));
}

/**
 * The 5-hour and weekly rings, rendered as two siblings so the enclosing
 * quota grid decides their columns.
 */
export function UsageDonuts({
	provider,
	primaryItems,
	secondaryItems,
	primaryTotal,
	secondaryTotal,
	primaryCenterValue,
	secondaryCenterValue,
	safeLinePrimary,
	safeLineSecondary,
	primaryNote,
	secondaryNote,
}: UsageDonutsProps) {
	const { t } = useTranslation();
	const claude = provider === "claude";
	const shared = {
		subtitle: t(claude ? "dashboard.usage.subtitleClaude" : "dashboard.usage.subtitleCodex"),
		centerLayout: "credits" as const,
		centerCaption: claude ? t("components.donut.proUnits") : undefined,
		formatValue: claude ? formatProUnits : undefined,
	};

	return (
		<Suspense
			fallback={
				<>
					<div className="min-w-0 rounded-xl border bg-card" />
					<div className="min-w-0 rounded-xl border bg-card" />
				</>
			}
		>
			<DonutChart
				{...shared}
				title={t(claude ? "dashboard.usage.fiveHourQuota" : "dashboard.usage.fiveHourCredits")}
				items={chartItems(primaryItems)}
				total={primaryTotal}
				centerValue={primaryCenterValue}
				safeLine={safeLinePrimary}
				note={primaryNote}
			/>
			<DonutChart
				{...shared}
				title={t(claude ? "dashboard.usage.weeklyQuota" : "dashboard.usage.weeklyCredits")}
				items={chartItems(secondaryItems)}
				total={secondaryTotal}
				centerValue={secondaryCenterValue}
				safeLine={safeLineSecondary}
				note={secondaryNote}
			/>
		</Suspense>
	);
}
