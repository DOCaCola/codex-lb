export function formatLimitWarmupWindow(window: string): string {
  return window === "primary" || window === "primary_idle" ? "5h" : "weekly";
}
