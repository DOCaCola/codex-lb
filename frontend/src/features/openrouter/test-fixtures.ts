import type { OpenRouterAccount } from "./api";

export function createOpenRouterAccount(
  overrides: Partial<OpenRouterAccount> = {},
): OpenRouterAccount {
  return {
    id: "src_research",
    name: "Research",
    isEnabled: true,
    hasManagementKey: true,
    state: {
      selections: [],
      catalog: [],
      catalog_updated_at: "2026-09-25T12:00:00Z",
      catalog_error: null,
      key_updated_at: "2026-09-25T12:00:00Z",
      key_error: null,
      credits_updated_at: "2026-09-25T12:00:00Z",
      credits_error: null,
      credits: { total_credits: 100, total_usage: 24.5 },
      key: {
        limit: 50,
        limit_remaining: 42.25,
        limit_reset: "monthly",
        usage: 7.75,
        usage_daily: 1.25,
        usage_weekly: 4.5,
        usage_monthly: 7.75,
        free_model_daily_requests: { used: 12, limit: 1000, remaining: 988 },
      },
    },
    ...overrides,
  };
}
