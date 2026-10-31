import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EMPTY_REPORT } from "../test-fixtures";
import { ReportsSummaryCards } from "./reports-summary-cards";

const summary = {
  ...EMPTY_REPORT.summary,
  pricedRequests: 1500,
  totalCostUsd: 15,
  totalInputTokens: 1_000_000,
  totalCachedTokens: 900_000,
  totalOutputTokens: 600_000,
  totalRequests: 1500,
  totalErrors: 30,
  totalCancelled: 15,
  totalConversations: 50,
  activeAccounts: 3,
  avgCostPerDay: 2.14,
  avgRequestsPerDay: 214.3,
};

const comparison = {
  canCompare: true,
  previous: { ...EMPTY_REPORT.comparison.previous, pricedRequests: 1000, totalCostUsd: 10, totalTokens: 3_200_000, totalRequests: 1000 },
};

describe("ReportsSummaryCards", () => {
  it("shows five cards with neutral deltas that name the previous window", () => {
    render(<ReportsSummaryCards summary={summary} comparison={comparison} />);

    expect(screen.getAllByTestId(/^report-summary-card-/).map((card) => card.dataset.testid)).toEqual([
      "report-summary-card-cost",
      "report-summary-card-tokens",
      "report-summary-card-requests",
      "report-summary-card-conversations",
      "report-summary-card-errors",
    ]);
    const costDelta = within(screen.getByTestId("report-summary-card-cost")).getByText("▲ 50%");
    expect(costDelta).toHaveClass("text-muted-foreground");
    expect(costDelta).toHaveAttribute("title", "Previous window: $10.00");
    expect(within(screen.getByTestId("report-summary-card-tokens")).getByText("▼ 50%")).toHaveClass("text-muted-foreground");
    expect(within(screen.getByTestId("report-summary-card-requests")).getByText("▲ 50%")).toBeInTheDocument();
    expect(screen.getByTestId("report-summary-card-requests")).toHaveTextContent("214 per day · 3 accounts");
    expect(screen.getByTestId("report-summary-card-tokens")).toHaveTextContent("90.0% cached · 600K output");
    expect(screen.getByTestId("report-summary-card-conversations")).toHaveTextContent("30 requests each on average");
    expect(screen.getByTestId("report-summary-card-errors")).toHaveTextContent("2.00%");
    expect(screen.getByTestId("report-summary-card-errors")).toHaveTextContent("15 cancelled (1.0%)");
  });

  it("omits the cost delta while either window has unpriced requests", () => {
    render(<ReportsSummaryCards summary={{ ...summary, unpricedRequests: 2 }} comparison={comparison} />);

    expect(within(screen.getByTestId("report-summary-card-cost")).queryByText(/%/)).not.toBeInTheDocument();
    expect(within(screen.getByTestId("report-summary-card-requests")).getByText("▲ 50%")).toBeInTheDocument();
  });

  it("shows no deltas when the previous window cannot be compared", () => {
    render(<ReportsSummaryCards summary={summary} comparison={{ ...comparison, canCompare: false }} />);

    expect(screen.queryByText(/[▲▼]/)).not.toBeInTheDocument();
  });

  it("explains the token total in the details marker", () => {
    render(<ReportsSummaryCards summary={summary} comparison={comparison} />);

    expect(screen.getByTestId("report-summary-details-tokens").getAttribute("title")).toContain("Cached input 900,000");
  });
});
