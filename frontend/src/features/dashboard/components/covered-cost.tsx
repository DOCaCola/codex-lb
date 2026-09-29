import { type CostCoverage, formatCoveredCost, formatCoveredCostShort } from "@/features/dashboard/cost-coverage";

export type CoveredCostProps = {
  costUsd: number;
  coverage: CostCoverage;
  className?: string;
};

/** Compact cost for tight spaces; the full coverage explanation is the hover title. */
export function CoveredCost({ costUsd, coverage, className }: CoveredCostProps) {
  const full = formatCoveredCost(costUsd, coverage);
  const short = formatCoveredCostShort(costUsd, coverage);
  return (
    <span className={className} title={short === full ? undefined : full}>
      {short}
    </span>
  );
}
