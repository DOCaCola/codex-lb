import { screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/utils";
import { ConversationActivityChart } from "./conversation-activity-chart";

vi.mock("@/hooks/use-chart-colors", () => ({
  useChartColors: () => ["#3b82f6"],
}));
vi.mock("@/components/lazy-recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => children,
  AreaChart: ({ data }: { data: unknown }) => (
    <output data-testid="activity-data">{JSON.stringify(data)}</output>
  ),
  Area: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));

describe("ConversationActivityChart", () => {
  it("fills empty hours within the advertised window and includes its latest request", () => {
    renderWithProviders(
      <ConversationActivityChart
        analytics={{
          start: "2026-09-24T10:00:00.001Z",
          end: "2026-10-01T10:00:00.001Z",
          models: [],
          activity: [
            {
              at: "2026-10-01T10:00:00Z",
              requests: 3,
              errors: 1,
              cancelled: 0,
            },
          ],
        }}
      />,
    );
    const data: { at: number; requests: number }[] = JSON.parse(
      screen.getByTestId("activity-data").textContent!,
    );
    expect(data).toHaveLength(169);
    expect(data[0]).toEqual({
      at: Date.parse("2026-09-24T10:00:00Z"),
      requests: 0,
    });
    expect(data.at(-1)).toEqual({
      at: Date.parse("2026-10-01T10:00:00Z"),
      requests: 3,
    });
    expect(
      screen.getByRole("region", { name: "Hourly activity (latest 7 days)" }),
    ).toBeInTheDocument();
  });
});
