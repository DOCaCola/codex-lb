import type { ReactNode } from "react";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/utils";

import { useReportSeriesStyles } from "../report-series-styles";
import type { ReportsResponse } from "../schemas";
import { dailyRow, EMPTY_REPORT, NO_COVERAGE_GAPS } from "../test-fixtures";
import { DailyTrendCard } from "./daily-trend-card";

let chartRows: Record<string, number | string>[] = [];
const bars: { dataKey: string; name: string }[] = [];
vi.mock("@/components/lazy-recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  BarChart: ({ children, data }: { children: ReactNode; data: Record<string, number | string>[] }) => {
    chartRows = data;
    bars.length = 0;
    return <div>{children}</div>;
  },
  Bar: ({ dataKey, name }: { dataKey: string; name: string }) => {
    bars.push({ dataKey, name });
    return null;
  },
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
}));

const DAY = "2026-10-30";

function accountSplit(index: number, costUsd: number) {
  return {
    ...NO_COVERAGE_GAPS,
    date: DAY,
    requests: 1,
    inputTokens: 100,
    cachedInputTokens: 40,
    outputTokens: 10,
    reasoningTokens: 2,
    costUsd,
    accountId: `acc-${index}`,
    modelSourceId: null,
    provider: "codex" as const,
    name: `Account ${index}`,
  };
}

const REPORT: ReportsResponse = {
  ...EMPTY_REPORT,
  daily: [dailyRow(DAY, { requests: 7, inputTokens: 700, cachedInputTokens: 280, outputTokens: 70, reasoningTokens: 14, costUsd: 280 })],
  dailyByAccount: [70, 60, 50, 40, 30, 20, 10].map((cost, index) => accountSplit(index + 1, cost)),
};

function Harness({ report }: { report: ReportsResponse }) {
  const styles = useReportSeriesStyles(report);
  return <DailyTrendCard report={report} startDate="2026-10-29" endDate={DAY} styles={styles} />;
}

describe("DailyTrendCard", () => {
  it("stacks the five largest accounts and sums the rest into Other", () => {
    renderWithProviders(<Harness report={REPORT} />);

    const legend = screen.getByTestId("reports-trend-legend");
    expect(within(legend).getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "Account 1",
      "Account 2",
      "Account 3",
      "Account 4",
      "Account 5",
      "Other",
    ]);
    expect(chartRows.map((row) => row.date)).toEqual(["2026-10-29", DAY]);
    expect(chartRows[1]).toMatchObject({ s0: 70, s4: 30, other: 30 });
    expect(chartRows[0]).toMatchObject({ s0: 0, other: 0 });
  });

  it("splits the total into cached and uncached input", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness report={REPORT} />);

    await user.click(within(screen.getByRole("group", { name: "Trend metric" })).getByRole("button", { name: "Input tokens" }));
    await user.click(within(screen.getByRole("group", { name: "Split by" })).getByRole("button", { name: "Total" }));

    expect(bars.map((bar) => bar.name)).toEqual(["Uncached input", "Cached input"]);
    expect(chartRows[1]).toMatchObject({ uncachedInput: 420, cachedInput: 280 });
  });

  it("shows the empty state without daily data", () => {
    renderWithProviders(<Harness report={EMPTY_REPORT} />);

    expect(screen.getByTestId("reports-empty")).toHaveTextContent("No data");
  });
});
