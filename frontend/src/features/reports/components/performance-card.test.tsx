import type { ReactElement, ReactNode } from "react";
import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/utils";

import { useReportSeriesStyles } from "../report-series-styles";
import type { ReportsResponse } from "../schemas";
import { dailyRow, EMPTY_REPORT } from "../test-fixtures";
import { PerformanceCard } from "./performance-card";

type Point = Record<string, unknown>;
let chartPoints: Point[] = [];
vi.mock("@/components/lazy-recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  LineChart: ({ children, data }: { children: ReactNode; data: Point[] }) => {
    chartPoints = data;
    return <div>{children}</div>;
  },
  Line: ({ dot }: { dot: (props: Point) => ReactElement | null }) => (
    <svg>{chartPoints.map((payload, index) => dot({ cx: 10, cy: 10, index, payload }))}</svg>
  ),
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
}));

const TPS = [50, 60, 0, 2941, 58];

const REPORT: ReportsResponse = {
  ...EMPTY_REPORT,
  speedMetricsAvailable: true,
  daily: TPS.map((medianTps, index) =>
    dailyRow(`2026-10-2${index + 5}`, { medianTps, medianTtftMs: medianTps === 0 ? 0 : 1200, medianQueueMs: 0 }),
  ),
};

function Harness({ report }: { report: ReportsResponse }) {
  const styles = useReportSeriesStyles(report);
  return <PerformanceCard report={report} styles={styles} />;
}

describe("PerformanceCard", () => {
  it("pins an outlier to the top edge with its real value", () => {
    renderWithProviders(<Harness report={REPORT} />);

    const tps = screen.getByTestId("reports-perf-tps");
    expect(within(tps).getByTestId("reports-perf-outlier")).toHaveTextContent("2,941 ↑");
    expect(within(tps).getAllByTestId("reports-perf-outlier")).toHaveLength(1);
  });

  it("treats missing speed samples as gaps but keeps a real zero queue wait", () => {
    renderWithProviders(<Harness report={REPORT} />);

    expect(screen.getByTestId("reports-perf-tps")).toHaveTextContent("59");
    expect(screen.getByTestId("reports-perf-ttft")).toHaveTextContent("1.2s");
    expect(screen.getByTestId("reports-perf-queue")).toHaveTextContent("0 ms");
  });

  it("explains when the range is too long for speed metrics", () => {
    renderWithProviders(<Harness report={{ ...REPORT, speedMetricsAvailable: false, speedMetricsMaxDays: 31 }} />);

    expect(screen.getByTestId("reports-perf")).toHaveTextContent("date ranges of 31 days or less");
    expect(screen.queryByTestId("reports-perf-tps")).not.toBeInTheDocument();
  });
});
