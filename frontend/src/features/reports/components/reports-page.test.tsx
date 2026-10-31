import type { ReactNode } from "react";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getRequestLogOptions } from "@/features/dashboard/api";
import { daysAgoLocalISO, getBrowserReportsTimeZone, localDateISO } from "@/features/reports/date";
import { REPORT_SECTION_VISIBILITY_STORAGE_KEY } from "@/features/reports/hooks/use-report-sections";
import { useReports, useReportsOptions, useThreadIdentity, type ReportsFilterState } from "@/features/reports/hooks/use-reports";
import type { ReportsResponse } from "@/features/reports/schemas";
import { accountEntry, EMPTY_REPORT, NO_COVERAGE_GAPS, THREAD_IDENTITY } from "@/features/reports/test-fixtures";
import { renderWithProviders } from "@/test/utils";

import { ReportsPage } from "./reports-page";

vi.mock("@/features/dashboard/api", () => ({ getRequestLogOptions: vi.fn() }));

vi.mock("@/features/reports/hooks/use-reports", () => ({
  useReports: vi.fn(),
  useReportsOptions: vi.fn(),
  useThreadIdentity: vi.fn(),
}));

vi.mock("@/features/reports/date", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/reports/date")>()),
  getBrowserReportsTimeZone: vi.fn(),
}));

vi.mock("@/components/lazy-recharts", () => {
  const Container = ({ children }: { children: ReactNode }) => <div>{children}</div>;
  const Empty = () => null;
  return {
    ResponsiveContainer: Container,
    BarChart: Container,
    LineChart: Container,
    Bar: Empty,
    Line: Empty,
    CartesianGrid: Empty,
    XAxis: Empty,
    YAxis: Empty,
    Tooltip: Empty,
  };
});

const REPORT: ReportsResponse = {
  ...EMPTY_REPORT,
  byModel: [{ ...NO_COVERAGE_GAPS, model: "gpt-6.1-sol", costUsd: 3, requests: 3, pricedRequests: 3 }],
  byAccount: [accountEntry("acc-1", "Andy Alpha", 3, 3)],
};

const useReportsMock = vi.mocked(useReports);
const useReportsOptionsMock = vi.mocked(useReportsOptions);
const useThreadIdentityMock = vi.mocked(useThreadIdentity);
const getRequestLogOptionsMock = vi.mocked(getRequestLogOptions);

type QueryResult = { data?: unknown; error?: unknown; isLoading?: boolean; refetch?: () => Promise<unknown> };

function queryResult({ data, error = null, isLoading = false, refetch = vi.fn().mockResolvedValue(undefined) }: QueryResult) {
  return { data, error, isLoading, isFetching: false, refetch } as never;
}

const lastFilters = (): ReportsFilterState => useReportsMock.mock.lastCall![0];

describe("ReportsPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(getBrowserReportsTimeZone).mockReturnValue("Europe/Berlin");
    useReportsMock.mockReset().mockReturnValue(queryResult({ data: REPORT }));
    useReportsOptionsMock.mockReset().mockReturnValue(
      queryResult({
        data: {
          models: ["gpt-6.1-sol"],
          useragents: [],
          accounts: [{ accountId: "acc-1", modelSourceId: null, provider: "codex", name: "Andy Alpha" }],
        },
      }),
    );
    useThreadIdentityMock.mockReset().mockReturnValue(queryResult({ data: THREAD_IDENTITY }));
    getRequestLogOptionsMock.mockReset().mockResolvedValue({ accountIds: [], apiKeys: [], modelOptions: [], statuses: [] });
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("opens on the last seven days in the browser timezone", () => {
    renderWithProviders(<ReportsPage />);

    expect(useReportsMock).toHaveBeenCalledWith(
      { startDate: daysAgoLocalISO(6), endDate: localDateISO(), accounts: [], apiKeyIds: [], models: [], useragents: [] },
      "Europe/Berlin",
    );
    expect(screen.getByRole("button", { name: "7d" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { level: 1, name: "Reports" })).toBeInTheDocument();
  });

  it("switches the window with a preset", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ReportsPage />);

    await user.click(screen.getByRole("button", { name: "30d" }));

    expect(lastFilters()).toMatchObject({ startDate: daysAgoLocalISO(29), endDate: localDateISO() });
  });

  it("starts in the custom range when given dates", () => {
    renderWithProviders(<ReportsPage initialFilters={{ startDate: "2026-10-01", endDate: "2026-10-03" }} />);

    expect(screen.getByRole("button", { name: "Custom" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("Start date")).toHaveValue("2026-10-01");
  });

  it("filters the report from a breakdown row and resets it", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ReportsPage />);

    await user.click(within(screen.getByTestId("reports-breakdown-models")).getByRole("button", { name: /gpt-6.1-sol/ }));
    await user.click(within(screen.getByTestId("reports-breakdown-accounts")).getByRole("button", { name: /Andy Alpha/ }));
    expect(lastFilters()).toMatchObject({ models: ["gpt-6.1-sol"], accounts: ["account:acc-1"] });

    await user.click(screen.getByRole("button", { name: "Reset" }));
    expect(lastFilters()).toMatchObject({ models: [], accounts: [] });
  });

  it("offers the report's accounts as filter options", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ReportsPage />);

    await user.click(within(screen.getByRole("region", { name: "Report filters" })).getByRole("button", { name: "Accounts" }));

    expect(await screen.findByRole("menuitemcheckbox", { name: "Andy Alpha" })).toBeInTheDocument();
  });

  it("loads routing diagnostics only while the card is open", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ReportsPage />);

    expect(useThreadIdentityMock.mock.lastCall?.[2]).toBe(false);
    await user.click(screen.getByRole("button", { name: /Routing diagnostics/ }));
    expect(useThreadIdentityMock.mock.lastCall?.[2]).toBe(true);
  });

  it("hides the sections the user turned off", () => {
    window.localStorage.setItem(REPORT_SECTION_VISIBILITY_STORAGE_KEY, JSON.stringify(["table"]));
    renderWithProviders(<ReportsPage />);

    expect(screen.getByTestId("reports-table")).toBeInTheDocument();
    expect(screen.queryByTestId("reports-trend")).not.toBeInTheDocument();
    expect(screen.queryByTestId("reports-diagnostics")).not.toBeInTheDocument();
    expect(useThreadIdentityMock.mock.lastCall?.[2]).toBe(false);
  });

  it("reports a failed report load and retries every query", async () => {
    const user = userEvent.setup();
    const refetchReport = vi.fn().mockResolvedValue(undefined);
    useReportsMock.mockReturnValue(queryResult({ error: new Error("down"), refetch: refetchReport }));
    getRequestLogOptionsMock.mockRejectedValue(new Error("keys down"));
    renderWithProviders(<ReportsPage />);

    expect(screen.getByText("Failed to load report data: down")).toBeInTheDocument();
    expect(await screen.findByText("Failed to load API key options: keys down")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Retry" })[0]);
    await waitFor(() => expect(refetchReport).toHaveBeenCalled());
  });
});
