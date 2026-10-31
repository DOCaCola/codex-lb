import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/utils";

import { MISSING_USER_AGENT, useReportSeriesStyles } from "../report-series-styles";
import type { ReportsResponse } from "../schemas";
import { accountEntry, EMPTY_REPORT, NO_COVERAGE_GAPS } from "../test-fixtures";
import { BreakdownSection, type BreakdownFilterKind } from "./breakdown-section";

const MODELS = Array.from({ length: 8 }, (_, index) => ({
  ...NO_COVERAGE_GAPS,
  model: `model-${index + 1}`,
  costUsd: 80 - index * 10,
  requests: index + 1,
  pricedRequests: index + 1,
}));

const REPORT: ReportsResponse = {
  ...EMPTY_REPORT,
  byModel: MODELS,
  byUseragent: [
    { ...NO_COVERAGE_GAPS, useragent: "codex_cli_rs", costUsd: 300, requests: 30 },
    { ...NO_COVERAGE_GAPS, useragent: MISSING_USER_AGENT, costUsd: 60, requests: 6 },
  ],
  byAccount: [
    accountEntry("acc-1", "Andy Alpha", 300, 30),
    { ...accountEntry("gone", "", 60, 6), accountId: null, name: null, provider: null },
  ],
};

function Harness({
  report = REPORT,
  selected = {},
  onToggle = vi.fn(),
}: {
  report?: ReportsResponse;
  selected?: Partial<Record<BreakdownFilterKind, string[]>>;
  onToggle?: (kind: BreakdownFilterKind, value: string) => void;
}) {
  const styles = useReportSeriesStyles(report);
  return (
    <BreakdownSection
      report={report}
      styles={styles}
      selected={{ accounts: [], models: [], useragents: [], ...selected }}
      onToggle={onToggle}
    />
  );
}

describe("BreakdownSection", () => {
  it("lists every entry by cost with its share of the list", () => {
    renderWithProviders(<Harness />);

    const models = within(screen.getByTestId("reports-breakdown-models")).getAllByRole("button");
    expect(models).toHaveLength(8);
    expect(models[0]).toHaveTextContent("model-1$80.00");
    expect(models[0]).toHaveTextContent("22.2%");
    expect(models[7]).toHaveTextContent("model-8$10.00");
  });

  it("toggles a filter from a row and marks selected rows", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    renderWithProviders(<Harness onToggle={onToggle} selected={{ models: ["model-2"] }} />);

    const models = screen.getByTestId("reports-breakdown-models");
    expect(within(models).getByRole("button", { name: /model-2/ })).toHaveAttribute("aria-pressed", "true");
    await user.click(within(models).getByRole("button", { name: /model-3/ }));
    expect(onToggle).toHaveBeenCalledWith("models", "model-3");

    await user.click(within(screen.getByTestId("reports-breakdown-accounts")).getByRole("button", { name: /Andy Alpha/ }));
    expect(onToggle).toHaveBeenCalledWith("accounts", "account:acc-1");
  });

  it("keeps unattributed usage visible but not filterable", () => {
    renderWithProviders(<Harness />);

    const accounts = screen.getByTestId("reports-breakdown-accounts");
    expect(within(accounts).getAllByRole("button")).toHaveLength(1);
    expect(within(accounts).getByText("Unattributed")).toBeInTheDocument();
  });

  it("draws requests without a user agent in the neutral grey", () => {
    renderWithProviders(<Harness />);

    const row = within(screen.getByTestId("reports-breakdown-useragents")).getByRole("button", { name: new RegExp(MISSING_USER_AGENT) });
    const dot = row.querySelector(".rounded-full") as HTMLElement;
    expect(dot.style.backgroundColor).toBe("rgb(203, 213, 225)");
  });

  it("ranks by requests and flags incomplete cost coverage", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness report={{ ...REPORT, summary: { ...REPORT.summary, unpricedRequests: 3 } }} />);

    expect(screen.getByTestId("reports-breakdown-coverage")).toBeInTheDocument();
    await user.click(within(screen.getByRole("group", { name: "Breakdown metric" })).getByRole("button", { name: "Requests" }));

    expect(screen.queryByTestId("reports-breakdown-coverage")).not.toBeInTheDocument();
    expect(within(screen.getByTestId("reports-breakdown-models")).getAllByRole("button")[0]).toHaveTextContent("model-8");
  });
});
