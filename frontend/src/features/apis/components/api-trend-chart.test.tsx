import { cloneElement, type ReactElement, type ReactNode } from "react";
import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ApiKeyTrendPoint } from "@/features/apis/schemas";
import { renderWithProviders } from "@/test/utils";

import { ApiTrendChart } from "./api-trend-chart";

let chartData: { t: string; cost: number; costCoverage?: ApiKeyTrendPoint }[];

vi.mock("@/components/lazy-recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AreaChart: ({ children, data }: { children: ReactNode; data: typeof chartData }) => {
    chartData = data;
    return <div>{children}</div>;
  },
  Area: () => null,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: ({ content }: { content: ReactElement<Record<string, unknown>> }) =>
    cloneElement(content, {
      active: true,
      label: chartData[0].t,
      payload: [{ dataKey: "cost", value: chartData[0].cost, payload: chartData[0] }],
    }),
}));

describe("ApiTrendChart", () => {
  it("renders a compact known subtotal without coverage counts in its tooltip", () => {
    renderWithProviders(
      <ApiTrendChart
        cost={[{
          t: "2026-09-30T08:00:00Z",
          v: 44_248.05,
          pricedRequests: 422_859,
          unpricedRequests: 99,
          unmeteredRequests: 3_985,
        }]}
        tokens={[]}
      />,
    );

    expect(screen.getByText("$44,248.05")).toBeInTheDocument();
    expect(screen.queryByText(/known · incomplete|422859|3985/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Cost chart shows a known subtotal; coverage is incomplete")).toBeInTheDocument();
  });

  it.each([
    { pricedRequests: 0, unpricedRequests: 1, expected: "Unknown" },
    { pricedRequests: 1, unpricedRequests: 0, expected: "$0.00" },
    { pricedRequests: 0, unpricedRequests: 0, expected: "No usage" },
  ])("preserves the $expected cost state", ({ expected, ...coverage }) => {
    renderWithProviders(
      <ApiTrendChart
        cost={[{ t: "2026-09-30T08:00:00Z", v: 0, ...coverage }]}
        tokens={[]}
      />,
    );

    expect(screen.getByText(expected)).toBeInTheDocument();
  });
});
