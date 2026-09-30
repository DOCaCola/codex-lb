import { cloneElement, type ReactElement, type ReactNode } from "react";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ComparisonPoint } from "@/features/apis/comparison-trends";
import type { ApiKeysTrendsResponse } from "@/features/apis/schemas";
import { renderWithProviders } from "@/test/utils";
import { ApiComparisonTrend } from "./api-comparison-trend";

let chartData: ComparisonPoint[];
vi.mock("@/components/lazy-recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AreaChart: ({ children, data }: { children: ReactNode; data: ComparisonPoint[] }) => {
    chartData = data;
    return <div data-testid="hourly-chart">{children}</div>;
  },
  LineChart: ({ children, data }: { children: ReactNode; data: ComparisonPoint[] }) => {
    chartData = data;
    return <div data-testid="cumulative-chart">{children}</div>;
  },
  Area: ({ name }: { name: string }) => <div data-testid={`series-${name}`} />,
  Line: ({ name }: { name: string }) => <div data-testid={`series-${name}`} />,
  CartesianGrid: () => null, XAxis: () => null, YAxis: () => null,
  Tooltip: ({ content }: { content: ReactElement<Record<string, unknown>> }) =>
    cloneElement(content, { active: true, label: chartData[0].t }),
}));

const fixture: ApiKeysTrendsResponse = {
  since: "2026-09-23T10:00:00Z", until: "2026-09-30T10:00:00Z",
  series: [{ keyId: "unknown", name: "Unknown-price key", isDeleted: false,
    cost: [{ t: "2026-09-30T08:00:00Z", v: 0, unpricedRequests: 1 }],
    tokens: [{ t: "2026-09-30T08:00:00Z", v: 900 }],
  }, { keyId: "free", name: "Free key", isDeleted: false,
    cost: [{ t: "2026-09-30T08:00:00Z", v: 0, pricedRequests: 1 }],
    tokens: [{ t: "2026-09-30T08:00:00Z", v: 100 }],
  }],
};

describe("ApiComparisonTrend", () => {
  it("switches measure and accumulation, and preserves legend choices across controls", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ApiComparisonTrend data={fixture} loading={false} error={false} onRetry={vi.fn()} />);
    expect(screen.getByTestId("hourly-chart")).toBeVisible();
    expect(screen.getByText("Unknown", { exact: true })).toBeVisible();
    expect(screen.getByText("$0.00", { exact: true })).toBeVisible();
    const legend = screen.getByRole("group", { name: "Visible API keys" });
    await user.click(within(legend).getByRole("button", { name: "Free key" }));
    expect(screen.queryByTestId("series-key:free")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tokens" }));
    expect(screen.getByRole("button", { name: "Tokens" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("900", { exact: true })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Cumulative" }));
    expect(screen.getByTestId("cumulative-chart")).toBeVisible();
    expect(screen.queryByTestId("series-key:free")).not.toBeInTheDocument();
    await user.click(within(legend).getByRole("button", { name: "Free key" }));
    expect(screen.getByTestId("series-key:free")).toBeVisible();
  });

  it("shows explicit loading, empty and retryable error states", async () => {
    const onRetry = vi.fn();
    const view = renderWithProviders(<ApiComparisonTrend loading error={false} onRetry={onRetry} />);
    expect(screen.getByRole("status", { name: "Loading usage trends" })).toBeVisible();
    view.rerender(<ApiComparisonTrend data={{ ...fixture, series: [] }} loading={false} error={false} onRetry={onRetry} />);
    expect(screen.getByText("No usage recorded in the last 7 days.")).toBeVisible();
    view.rerender(<ApiComparisonTrend loading={false} error onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Usage trends could not be loaded.");
    expect(screen.queryByText("No usage recorded in the last 7 days.")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
