import type { TFunction } from "i18next";

const COST_RANK: Record<string, number> = {
  flex: 0,
  default: 1,
  auto: 1,
  priority: 2,
  ultrafast: 3,
};

/** The billable tier worth showing; the standard tier is implicit. */
export function visibleServiceTier(
  tier: string | null | undefined,
): string | null {
  const normalized = tier?.trim().toLowerCase();
  return normalized && normalized !== "default" && normalized !== "auto"
    ? normalized
    : null;
}

/** True when the request was billed on a cheaper tier than it asked for. */
export function isServiceTierDowngrade(
  requested: string | null | undefined,
  billed: string | null | undefined,
): boolean {
  const requestedRank = COST_RANK[requested?.trim().toLowerCase() ?? ""];
  const billedRank = COST_RANK[billed?.trim().toLowerCase() ?? ""];
  return (
    requestedRank !== undefined &&
    billedRank !== undefined &&
    billedRank < requestedRank
  );
}

/** Readable tier name, e.g. ``priority`` -> "Fast"; empty without a tier. */
export function serviceTierLabel(
  tier: string | null | undefined,
  t: TFunction,
): string {
  const normalized = tier?.trim().toLowerCase();
  return normalized
    ? t(`common.serviceTier.${normalized}`, { defaultValue: normalized })
    : "";
}
