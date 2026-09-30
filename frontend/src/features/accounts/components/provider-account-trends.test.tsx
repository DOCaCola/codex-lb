import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/utils";
import { server } from "@/test/mocks/server";
import { ProviderAccountTrends } from "./provider-account-trends";

vi.mock("./account-trend-chart", () => ({
  AccountSeriesChart: ({ percentage, series }: { percentage: boolean; series: unknown[] }) =>
    <div data-testid="chart" data-series={JSON.stringify(series)}>{percentage ? "percentage" : "count"}:{series.length}</div>,
}));

describe("ProviderAccountTrends", () => {
  it.each(["openrouter", "claude"] as const)("uses provider-appropriate units for %s", async (provider) => {
    server.use(http.get(`/api/${provider}-accounts/account-a/trends`, () => HttpResponse.json({ series: [] })));
    renderWithProviders(<ProviderAccountTrends provider={provider} accountId="account-a" />);
    expect(await screen.findByTestId("chart")).toHaveTextContent(provider === "claude" ? "percentage:0" : "count:0");
    expect(screen.getByRole("region")).toHaveTextContent(provider === "claude" ? "Quota remaining" : "Request activity");
  });

  it("shows an error rather than an empty chart on failure", async () => {
    server.use(http.get("/api/openrouter-accounts/account-a/trends", () => HttpResponse.json({}, { status: 500 })));
    renderWithProviders(<ProviderAccountTrends provider="openrouter" accountId="account-a" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load history");
    expect(screen.queryByTestId("chart")).not.toBeInTheDocument();
  });

  it("preserves the weekly-plan style and color through the API and legend", async () => {
    const series = [
      { key: "seven_day", label: "Weekly", dashed: false, colorIndex: 1, points: [{ t: "2026-09-30T00:00:00Z", v: 80 }] },
      { key: "weekly_plan", label: "Weekly plan", dashed: true, colorIndex: 1, points: [{ t: "2026-09-30T00:00:00Z", v: 60 }] },
    ];
    server.use(http.get("/api/claude-accounts/account-a/trends", () => HttpResponse.json({ series })));
    renderWithProviders(<ProviderAccountTrends provider="claude" accountId="account-a" />);
    const chart = await screen.findByTestId("chart");
    expect(JSON.parse(chart.getAttribute("data-series")!)).toEqual(series);
    const weekly = screen.getByText("Weekly").querySelector("span")!;
    const plan = screen.getByText("Weekly plan").querySelector("span")!;
    expect(plan).toHaveClass("border-dashed");
    expect(plan.style.borderColor).toBe(weekly.style.backgroundColor);
    expect(screen.getByText(/even-consumption guideline/)).toBeInTheDocument();
  });
});
