import { describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";

import { AccountSeriesChart, AccountTrendChart } from "@/features/accounts/components/account-trend-chart";

vi.mock("@/components/lazy-recharts", () => ({
  Area: () => null,
  AreaChart: ({ children, data }: { children: ReactNode; data: unknown }) => <div data-testid="chart-data" data-points={JSON.stringify(data)}>{children}</div>,
  CartesianGrid: () => null,
  Line: () => null,
  ResponsiveContainer: ({ children }: { children: ReactNode }) => (
    <div data-testid="responsive-container" style={{ width: 400, height: 200 }}>
      {children}
    </div>
  ),
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: ({ tickFormatter }: { tickFormatter: (v: number) => string }) => <span data-testid="axis-unit">{tickFormatter(25)}</span>,
}));

const BASE = new Date("2026-01-15T00:00:00Z");

function makePoints(count: number, baseValue: number) {
  return Array.from({ length: count }, (_, i) => ({
    t: new Date(BASE.getTime() + i * 3600_000).toISOString(),
    v: baseValue + i * 0.5,
  }));
}

describe("AccountTrendChart", () => {
  it("keeps unknown quota gaps and the union of series timestamps", () => {
    render(<AccountSeriesChart series={[
      { key: "a", label: "5h", points: [{ t: "2026-01-15T00:00:00Z", v: 70 }] },
      { key: "b", label: "Weekly", points: [{ t: "2026-01-15T01:00:00Z", v: 40 }] },
    ]} />);
    expect(JSON.parse(screen.getByTestId("chart-data").getAttribute("data-points")!)).toEqual([
      { t: "2026-01-15T00:00:00Z", a: 70, b: null },
      { t: "2026-01-15T01:00:00Z", a: null, b: 40 },
    ]);
    expect(screen.getByTestId("axis-unit")).toHaveTextContent("25%");
  });

  it("does not format request counts as percentages", () => {
    render(<AccountSeriesChart percentage={false} series={[
      { key: "requests", label: "Requests", points: [{ t: BASE.toISOString(), v: 25 }] },
    ]} />);
    expect(screen.getByTestId("axis-unit").textContent).toBe("25");
  });
  it("renders empty state when no data is provided", () => {
    render(<AccountTrendChart primary={[]} secondary={[]} />);
    expect(screen.getByText("No trend data available")).toBeInTheDocument();
  });

  it("renders chart container when data is provided", () => {
    const primary = makePoints(24, 70);
    const secondary = makePoints(24, 50);

    render(<AccountTrendChart primary={primary} secondary={secondary} />);
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("renders chart with only primary data when secondary is empty", () => {
    const primary = makePoints(24, 80);

    render(<AccountTrendChart primary={primary} secondary={[]} />);
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });
});
