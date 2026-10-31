import { formatCurrency, formatNumber } from "@/utils/formatters";

import type { TrendMetric } from "./report-model";

const compactFormatter = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const compactUsdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

/** Token counts and other large quantities, e.g. 16.4B. */
export function formatCompact(value: number): string {
  return compactFormatter.format(value);
}

/** Axis ticks only; full-value USD displays use formatCurrency. */
export function formatCompactUsd(value: number): string {
  return compactUsdFormatter.format(value);
}

/** Share of a whole; tiny non-zero shares stay visible as <0.1%. */
export function formatShare(ratio: number, fractionDigits = 1): string {
  if (ratio > 0 && ratio < 0.001) return "<0.1%";
  return `${(ratio * 100).toFixed(fractionDigits)}%`;
}

export function formatMilliseconds(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)} ms`;
}

export function formatTokensPerSecond(value: number): string {
  return formatNumber(Math.round(value));
}

/** Full value of a trend metric, as shown in tooltips. */
export function formatMetricValue(metric: TrendMetric, value: number): string {
  return metric === "cost" ? formatCurrency(value) : formatNumber(Math.round(value));
}

export function formatMetricTick(metric: TrendMetric, value: number): string {
  return metric === "cost" ? formatCompactUsd(value) : formatCompact(value);
}
