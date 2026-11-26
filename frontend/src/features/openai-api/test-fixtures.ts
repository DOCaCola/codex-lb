import type { OpenAIApiAccount } from "./api";

export function createOpenAIApiAccount(overrides: Partial<OpenAIApiAccount> = {}): OpenAIApiAccount {
  return {
    routingPolicy: "normal",
    id: "src_platform",
    name: "Platform",
    isEnabled: true,
    state: {
      selections: [
        { model: "gpt-6.2-astra", displayName: null },
        { model: "gpt-image-2.5-sunburst", displayName: null },
      ],
      catalog: [
        { id: "gpt-image-2.5-sunburst", kind: "image", created: 1_760_000_000 },
        { id: "gpt-6.2-astra", kind: "text", created: 1_760_000_000 },
        { id: "gpt-6-luna", kind: "text", created: 1_750_000_000 },
      ],
      catalog_updated_at: "2026-11-26T09:00:00Z",
      catalog_error: null,
      monthly_credit_usd: 50,
      credit_renews_on: 1,
    },
    credit: {
      cycleStart: "2026-11-01T00:00:00",
      cycleEnd: "2026-12-01T00:00:00",
      spentUsd: 12.5,
      monthlyCreditUsd: 50,
      remainingUsd: 37.5,
      exhaustedUntil: null,
    },
    ...overrides,
  };
}
