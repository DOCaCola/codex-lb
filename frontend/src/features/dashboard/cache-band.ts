export type CacheBand = "high" | "mid" | "low" | "none";

// Agent LB's three cache-read bands; "none" is a request without a measured prompt.
export function cacheBand(ratio: number | null): CacheBand {
  if (ratio === null) return "none";
  if (ratio >= 0.8) return "high";
  if (ratio >= 0.3) return "mid";
  return "low";
}
