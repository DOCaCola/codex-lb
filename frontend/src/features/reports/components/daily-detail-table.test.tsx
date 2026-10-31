import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { renderWithProviders } from "@/test/utils";

import { dailyRow, EMPTY_REPORT } from "../test-fixtures";
import { DailyDetailTable } from "./daily-detail-table";

const DATA = [
  dailyRow("2026-10-02", {
    requests: 40,
    conversations: 4,
    inputTokens: 2000,
    cachedInputTokens: 1500,
    outputTokens: 300,
    reasoningTokens: null,
    costUsd: 4,
    pricedRequests: 40,
    errorCount: 2,
    activeAccounts: 2,
    medianTtftMs: 850,
    medianTps: 42.4,
  }),
  dailyRow("2026-10-03", { requests: 10, inputTokens: 500, outputTokens: 50, costUsd: 1, pricedRequests: 10, activeAccounts: 1 }),
];

const SUMMARY = {
  ...EMPTY_REPORT.summary,
  totalRequests: 50,
  totalConversations: 4,
  totalInputTokens: 2500,
  totalCachedTokens: 1500,
  totalOutputTokens: 350,
  totalCostUsd: 5,
  pricedRequests: 50,
  totalErrors: 2,
  activeAccounts: 2,
};

function renderTable() {
  return renderWithProviders(
    <DailyDetailTable startDate="2026-10-01" endDate="2026-10-03" data={DATA} summary={SUMMARY} />,
  );
}

const rowDates = () =>
  screen.getAllByTestId(/^daily-breakdown-row-/).map((row) => row.dataset.testid?.replace("daily-breakdown-row-", ""));

beforeEach(() => {
  useDateDisplayFormatStore.setState({ dateDisplayFormat: "default" });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("DailyDetailTable", () => {
  it("lists every day of the window, newest first", () => {
    renderTable();

    expect(rowDates()).toEqual(["2026-10-03", "2026-10-02", "2026-10-01"]);
    expect(screen.getByTestId("daily-breakdown-row-2026-10-01")).toHaveTextContent("Thu, Oct 1");
    expect(screen.getByRole("columnheader", { name: /Day/ })).toHaveAttribute("aria-sort", "descending");
  });

  it("formats cached input, missing reasoning, errors and medians", () => {
    renderTable();

    const cells = within(screen.getByTestId("daily-breakdown-row-2026-10-02")).getAllByRole("cell");
    expect(cells[3]).toHaveTextContent("2K75% cached");
    expect(cells[5]).toHaveTextContent("—");
    expect(cells[7]).toHaveTextContent("25.0%");
    expect(cells[10]).toHaveTextContent("850 ms");
    expect(cells[11]).toHaveTextContent("42");
    const empty = within(screen.getByTestId("daily-breakdown-row-2026-10-01")).getAllByRole("cell");
    expect(empty[3]).toHaveTextContent(/^0$/);
    expect(empty[11]).toHaveTextContent("—");
  });

  it("totals the window from the report summary", () => {
    renderTable();

    const total = within(screen.getByTestId("daily-breakdown-total")).getAllByRole("cell");
    expect(total[0]).toHaveTextContent("Total");
    expect(total[1]).toHaveTextContent("50");
    expect(total[3]).toHaveTextContent("2.5K60% cached");
    expect(total[6]).toHaveTextContent("$5.00");
  });

  it("sorts a new column descending first, then toggles", async () => {
    const user = userEvent.setup();
    renderTable();

    await user.click(screen.getByRole("button", { name: "Requests" }));
    expect(rowDates()).toEqual(["2026-10-02", "2026-10-03", "2026-10-01"]);
    expect(screen.getByTestId("sort-icon-desc")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Requests" }));
    expect(rowDates()).toEqual(["2026-10-01", "2026-10-03", "2026-10-02"]);
    expect(screen.getByTestId("sort-icon-asc")).toBeInTheDocument();
  });

  it("follows the date display format", () => {
    useDateDisplayFormatStore.setState({ dateDisplayFormat: "iso8601" });
    renderTable();

    expect(screen.getByTestId("daily-breakdown-row-2026-10-01")).toHaveTextContent("2026-10-01");
  });

  it("exports the window chronologically regardless of the sort", async () => {
    const user = userEvent.setup();
    let exported: Blob | undefined;
    vi.spyOn(URL, "createObjectURL").mockImplementation((blob) => {
      exported = blob as Blob;
      return "blob:report";
    });
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    renderTable();

    await user.click(screen.getByRole("button", { name: "CSV" }));

    const lines = (await exported!.text()).split("\n");
    expect(lines[0]).toMatch(/^Date,Requests,Conversations,/);
    expect(lines.slice(1).map((line) => line.split(",")[0])).toEqual(["2026-10-01", "2026-10-02", "2026-10-03"]);
    expect(lines[2].split(",")[6]).toBe("");
  });
});
