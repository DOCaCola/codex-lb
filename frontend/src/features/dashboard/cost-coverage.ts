import { formatCurrency } from "@/utils/formatters";

export type CostCoverage = {
  pricedRequests?: number;
  unpricedRequests?: number;
  unmeteredRequests?: number;
  coverageUnknown?: boolean;
};

export function isCostCoverageComplete(coverage: CostCoverage): boolean {
  return !coverage.unpricedRequests && !coverage.unmeteredRequests && !coverage.coverageUnknown;
}

/**
 * Compact form for values, cells and chart labels. An incomplete known
 * subtotal is a lower bound on the real cost, so it reads "≥ $X"; pair it
 * with `formatCoveredCost` as a tooltip or `formatCostCoverageNote` as a
 * detail line.
 */
export function formatCoveredCostShort(costUsd: number, coverage: CostCoverage): string {
  const full = formatCoveredCost(costUsd, coverage);
  if (full === "No usage" || full === "Unknown" || isCostCoverageComplete(coverage)) return full;
  return `≥ ${formatCurrency(costUsd)}`;
}

/** Short detail line for an incomplete subtotal, or null when coverage is complete. */
export function formatCostCoverageNote(coverage: CostCoverage): string | null {
  if (isCostCoverageComplete(coverage)) return null;
  const parts = [
    coverage.unpricedRequests ? `${coverage.unpricedRequests} unpriced` : null,
    coverage.unmeteredRequests ? `${coverage.unmeteredRequests} unmetered` : null,
    coverage.coverageUnknown ? "older totals unverified" : null,
  ].filter(Boolean);
  return `Known cost only · ${parts.join(" · ")}`;
}

export function formatCoveredCost(costUsd: number, coverage: CostCoverage): string {
  const priced = coverage.pricedRequests ?? 0;
  const unpriced = coverage.unpricedRequests ?? 0;
  const unmetered = coverage.unmeteredRequests ?? 0;
  const unknown = coverage.coverageUnknown ?? false;
  if (!priced && !unpriced && !unmetered && !unknown) return "No usage";
  if (!unpriced && !unmetered && !unknown) return formatCurrency(costUsd);
  // Historical rollups can hold a known dollar sum without per-request
  // counts; only "no known cost at all" is Unknown.
  if (!priced && costUsd <= 0) return "Unknown";
  if (!priced && !unpriced && !unmetered) return `${formatCurrency(costUsd)} known · coverage unavailable`;
  const parts = [
    priced ? `${priced} priced` : null,
    unpriced ? `${unpriced} unpriced` : null,
    unmetered ? `${unmetered} unmetered` : null,
    unknown ? "historical coverage unknown" : null,
  ].filter(Boolean).join(", ");
  return `${formatCurrency(costUsd)} known · incomplete (${parts})`;
}
