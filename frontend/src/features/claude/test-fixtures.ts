import type { ClaudeAccount } from "./api";

type ClaudeQuotaWindowEntry = ClaudeAccount["quota"]["windows"][number];

export function createClaudeQuotaWindow(
  overrides: Partial<ClaudeQuotaWindowEntry> & Pick<ClaudeQuotaWindowEntry, "name">,
): ClaudeQuotaWindowEntry {
  return {
    utilization: 0,
    resetsAt: null,
    freshness: "fresh",
    exhausted: false,
    ...overrides,
  };
}

export function createClaudeAccount(overrides: Partial<ClaudeAccount> = {}): ClaudeAccount {
  return {
    planType: "pro",
    quotaWeight: 1,
    maxConcurrency: null,
    routingPolicy: "normal",
    id: "claude-test",
    name: "Claude Test",
    isEnabled: true,
    credentialStatus: "ready",
    expiresAt: "2026-09-25T20:00:00Z",
    extraUsageEnabled: false,
    state: {
      subscription: null,
      subscription_updated_at: null,
      subscription_error: null,
      all_models: false,
      reasoning_restrictions: {},
      selections: [],
      catalog: [],
      catalog_updated_at: null,
      catalog_error: null,
      usage_updated_at: null,
      usage_error: null,
    },
    quota: {
      observedAt: null,
      models: [],
      windows: [
        createClaudeQuotaWindow({ name: "five_hour" }),
        createClaudeQuotaWindow({ name: "seven_day" }),
      ],
    },
    ...overrides,
  };
}
