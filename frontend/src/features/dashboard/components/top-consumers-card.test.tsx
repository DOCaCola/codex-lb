import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TopConsumersCard } from "@/features/dashboard/components/top-consumers-card";

describe("TopConsumersCard", () => {
  it("lists consumers with requests, tokens, dominant model and cost", () => {
    render(
      <TopConsumersCard
        provider="codex"
        consumers={[
          {
            apiKeyId: "key_hermes_prod",
            name: "hermes-prod",
            requests: 12_400,
            billableTokens: 9_800_000,
            cachedTokens: 4_000_000,
            dominantModel: "gpt-5.2-codex",
            costCoverage: { knownCostUsd: 44_248.05, pricedRequests: 12_399, unpricedRequests: 1, unmeteredRequests: 0, coverageUnknown: false },
          },
          {
            apiKeyId: "key_batch_eval",
            name: "batch-eval",
            requests: 800,
            billableTokens: 14_200_000,
            cachedTokens: 0,
            dominantModel: "gpt-5.2",
            costCoverage: { knownCostUsd: 0, pricedRequests: 800, unpricedRequests: 0, unmeteredRequests: 0, coverageUnknown: false },
          },
        ]}
      />,
    );

    expect(screen.getByText("Top consumers")).toBeInTheDocument();
    expect(screen.getByText("Codex · last 2h")).toBeInTheDocument();
    expect(screen.getByText("hermes-prod")).toBeInTheDocument();
    expect(screen.getByText("12.4K req")).toBeInTheDocument();
    expect(screen.getByText("9.8M tok")).toBeInTheDocument();
    expect(screen.getByText("gpt-5.2-codex")).toBeInTheDocument();
    expect(screen.getByText("batch-eval")).toBeInTheDocument();
    expect(screen.getByText("Est. API Cost")).toBeInTheDocument();
    const cost = screen.getByText("$44,248.05");
    expect(cost).toHaveAttribute("title", "Est. API Cost · last 2h: $44,248.05 known · incomplete (12399 priced, 1 unpriced)");
    expect(cost.textContent).not.toContain("known");
    expect(screen.getByText("$0.00")).toBeInTheDocument();
  });

  it("renders rows with colliding key names", () => {
    render(
      <TopConsumersCard
        provider="claude"
        consumers={[
          { name: "(unnamed)", requests: 500, billableTokens: 1_000_000, cachedTokens: 0, dominantModel: "claude-opus-5-5",
            costCoverage: { knownCostUsd: 0, pricedRequests: 0, unpricedRequests: 500, unmeteredRequests: 0, coverageUnknown: false } },
          { name: "(unnamed)", requests: 300, billableTokens: 2_000_000, cachedTokens: 0, dominantModel: "claude-sonnet-5",
            costCoverage: { knownCostUsd: 0, pricedRequests: 0, unpricedRequests: 300, unmeteredRequests: 0, coverageUnknown: false } },
        ]}
      />,
    );

    expect(screen.getByText("Claude · last 2h")).toBeInTheDocument();
    expect(screen.getAllByText("(unnamed)")).toHaveLength(2);
    expect(screen.getByText("500 req")).toBeInTheDocument();
    expect(screen.getByText("300 req")).toBeInTheDocument();
    expect(screen.getAllByText("Unknown")).toHaveLength(2);
  });

  it("states when there were no requests", () => {
    render(<TopConsumersCard provider="codex" consumers={[]} />);

    expect(screen.getByText("No requests in the last 2h")).toBeInTheDocument();
  });
});
