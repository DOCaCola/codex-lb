import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { keySeriesId } from "@/features/apis/key-summary";
import { TopConsumersCard } from "@/features/dashboard/components/top-consumers-card";
import type { WeeklyCreditApiKeyAttribution } from "@/features/dashboard/utils";

const EMPTY_BUCKETS = Array.from({ length: 12 }, () => 0);

function consumer(overrides: Partial<WeeklyCreditApiKeyAttribution> & Pick<WeeklyCreditApiKeyAttribution, "name">): WeeklyCreditApiKeyAttribution {
  return {
    requests: 0,
    billableTokens: 0,
    cachedTokens: 0,
    dominantModel: "gpt-5.2",
    costCoverage: { knownCostUsd: 0, pricedRequests: 0, unpricedRequests: 0, unmeteredRequests: 0, coverageUnknown: false },
    costBuckets: EMPTY_BUCKETS,
    ...overrides,
  };
}

describe("TopConsumersCard", () => {
  it("ranks consumers with requests, tokens, a cost trend and cost", () => {
    render(
      <TopConsumersCard
        provider="codex"
        keyColors={new Map([[keySeriesId("key_hermes_prod"), "#2563eb"]])}
        consumers={[
          consumer({
            apiKeyId: "key_hermes_prod",
            name: "hermes-prod",
            requests: 12_400,
            billableTokens: 9_800_000,
            cachedTokens: 4_000_000,
            dominantModel: "gpt-5.2-codex",
            costCoverage: { knownCostUsd: 44_248.05, pricedRequests: 12_399, unpricedRequests: 1, unmeteredRequests: 0, coverageUnknown: false },
            costBuckets: [...EMPTY_BUCKETS.slice(1), 44_248.05],
          }),
          consumer({
            apiKeyId: "key_batch_eval",
            name: "batch-eval",
            requests: 800,
            billableTokens: 14_200_000,
            costCoverage: { knownCostUsd: 0, pricedRequests: 800, unpricedRequests: 0, unmeteredRequests: 0, coverageUnknown: false },
          }),
        ]}
      />,
    );

    expect(screen.getByText("Top consumers")).toBeInTheDocument();
    expect(screen.getByText("Codex · last 2h")).toBeInTheDocument();
    const [first, second] = screen.getAllByTestId("top-consumer-row");
    expect(within(first).getByText("1")).toBeInTheDocument();
    expect(within(first).getByText("hermes-prod").parentElement).toHaveAttribute("title", "gpt-5.2-codex");
    expect(first).toHaveTextContent("12.4K req · 9.8M tok");
    expect(first.querySelector("path[stroke]")).toHaveAttribute("stroke", "#2563eb");
    const cost = within(first).getByText("$44,248.05");
    expect(cost).toHaveAttribute("title", "Est. API Cost · last 2h: $44,248.05 known · incomplete (12399 priced, 1 unpriced)");
    expect(within(second).getByText("batch-eval")).toBeInTheDocument();
    expect(within(second).getByText("$0.00")).toBeInTheDocument();
    expect(screen.getByText("Est. API Cost")).toBeInTheDocument();
  });

  it("renders rows with colliding key names", () => {
    render(
      <TopConsumersCard
        provider="claude"
        keyColors={new Map()}
        consumers={[
          consumer({ name: "(unnamed)", requests: 500, costCoverage: { knownCostUsd: 0, pricedRequests: 0, unpricedRequests: 500, unmeteredRequests: 0, coverageUnknown: false } }),
          consumer({ name: "(unnamed)", requests: 300, costCoverage: { knownCostUsd: 0, pricedRequests: 0, unpricedRequests: 300, unmeteredRequests: 0, coverageUnknown: false } }),
        ]}
      />,
    );

    expect(screen.getByText("Claude · last 2h")).toBeInTheDocument();
    expect(screen.getAllByText("(unnamed)")).toHaveLength(2);
    expect(screen.getAllByText("Unknown")).toHaveLength(2);
  });

  it("states when there were no requests", () => {
    render(<TopConsumersCard provider="codex" consumers={[]} keyColors={new Map()} />);

    expect(screen.getByText("No requests in the last 2h")).toBeInTheDocument();
  });
});
