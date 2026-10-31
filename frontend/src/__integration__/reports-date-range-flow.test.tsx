import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import App from "@/App";
import { daysAgoLocalISO } from "@/features/reports/date";
import type { ReportsResponse } from "@/features/reports/schemas";
import { EMPTY_REPORT, NO_COVERAGE_GAPS } from "@/features/reports/test-fixtures";
import { server } from "@/test/mocks/server";
import { renderWithProviders } from "@/test/utils";

const REPORT_WITH_MODEL: ReportsResponse = {
  ...EMPTY_REPORT,
  byModel: [{ ...NO_COVERAGE_GAPS, model: "gpt-5.1", costUsd: 0, requests: 0 }],
};

const OPTIONS = { models: ["gpt-5.1"], useragents: [], accounts: [] };

const CORRECTIONS = [
  { name: "start date", label: "Start date", correctedDaysAgo: 9, expectedStartDaysAgo: 9, expectedEndDaysAgo: 8 },
  { name: "end date", label: "End date", correctedDaysAgo: 6, expectedStartDaysAgo: 7, expectedEndDaysAgo: 6 },
] as const;

function isInverted(params: URLSearchParams): boolean {
  const startDate = params.get("start_date");
  const endDate = params.get("end_date");
  return startDate !== null && endDate !== null && startDate > endDate;
}

function inWindow(requests: URLSearchParams[], startDate: string, endDate: string): URLSearchParams[] {
  return requests.filter((params) => params.get("start_date") === startDate && params.get("end_date") === endDate);
}

async function openReportsWithModelFilter(reportsRequests: URLSearchParams[]) {
  const user = userEvent.setup({ delay: null });
  window.history.pushState({}, "", "/reports");
  renderWithProviders(<App />);
  expect(window.location.pathname).toBe("/reports");

  await user.click(await screen.findByRole("button", { name: "Models", expanded: false }));
  await user.click(await screen.findByRole("menuitemcheckbox", { name: "gpt-5.1" }));
  await user.keyboard("{Escape}");
  await waitFor(() => {
    expect(reportsRequests.some((params) => params.get("model") === "gpt-5.1")).toBe(true);
  });
  await user.click(within(screen.getByRole("group", { name: "Date range" })).getByRole("button", { name: "Custom" }));
  return user;
}

describe("reports date-range flow integration", () => {
  it.each(CORRECTIONS)(
    "suppresses inverted requests on the reports route and recovers through the $name",
    async ({ label, correctedDaysAgo, expectedStartDaysAgo, expectedEndDaysAgo }) => {
      const referenceDate = new Date();
      const expectedStart = daysAgoLocalISO(expectedStartDaysAgo, referenceDate);
      const expectedEnd = daysAgoLocalISO(expectedEndDaysAgo, referenceDate);
      const reportsRequests: URLSearchParams[] = [];
      const optionsRequests: URLSearchParams[] = [];

      server.use(
        http.get("/api/reports", ({ request }) => {
          reportsRequests.push(new URL(request.url).searchParams);
          return HttpResponse.json(REPORT_WITH_MODEL);
        }),
        http.get("/api/reports/options", ({ request }) => {
          optionsRequests.push(new URL(request.url).searchParams);
          return HttpResponse.json(OPTIONS);
        }),
      );

      await openReportsWithModelFilter(reportsRequests);

      const startInput = screen.getByLabelText("Start date");
      const endInput = screen.getByLabelText("End date");
      fireEvent.change(endInput, { target: { value: daysAgoLocalISO(8, referenceDate) } });
      fireEvent.change(startInput, { target: { value: daysAgoLocalISO(7, referenceDate) } });

      await waitFor(() => {
        expect(startInput).toHaveAttribute("aria-invalid", "true");
        expect(endInput).toHaveAttribute("aria-invalid", "true");
      });
      expect(screen.getByText("Start date must be on or before end date.")).toBeInTheDocument();
      expect([...reportsRequests, ...optionsRequests].filter(isInverted)).toHaveLength(0);

      fireEvent.change(screen.getByLabelText(label), {
        target: { value: daysAgoLocalISO(correctedDaysAgo, referenceDate) },
      });

      await waitFor(() => {
        expect(inWindow(reportsRequests, expectedStart, expectedEnd)).toHaveLength(1);
        expect(inWindow(optionsRequests, expectedStart, expectedEnd)).toHaveLength(1);
      });
      expect(inWindow(reportsRequests, expectedStart, expectedEnd)[0].getAll("model")).toEqual(["gpt-5.1"]);
      expect(optionsRequests.every((params) => !params.has("model"))).toBe(true);
      expect(screen.queryByText("Start date must be on or before end date.")).not.toBeInTheDocument();
      expect(startInput).not.toHaveAttribute("aria-invalid");
      expect(endInput).not.toHaveAttribute("aria-describedby");
    },
  );

  it("retries only the API key options while the range is inverted", async () => {
    const referenceDate = new Date();
    const reportsRequests: URLSearchParams[] = [];
    const optionsRequests: URLSearchParams[] = [];
    let apiKeyRequests = 0;

    server.use(
      http.get("/api/request-logs/options", () => {
        apiKeyRequests += 1;
        return HttpResponse.json(
          { error: { code: "options_unavailable", message: "Options unavailable" } },
          { status: 503 },
        );
      }),
      http.get("/api/reports", ({ request }) => {
        reportsRequests.push(new URL(request.url).searchParams);
        return HttpResponse.json(REPORT_WITH_MODEL);
      }),
      http.get("/api/reports/options", ({ request }) => {
        optionsRequests.push(new URL(request.url).searchParams);
        return HttpResponse.json(OPTIONS);
      }),
    );

    const user = await openReportsWithModelFilter(reportsRequests);

    fireEvent.change(screen.getByLabelText("End date"), { target: { value: daysAgoLocalISO(8, referenceDate) } });
    fireEvent.change(screen.getByLabelText("Start date"), { target: { value: daysAgoLocalISO(7, referenceDate) } });
    expect(await screen.findByText("Start date must be on or before end date.")).toBeInTheDocument();

    const errorText = await screen.findByText(/Failed to load API key options:/);
    const retryButton = within(errorText.parentElement!.parentElement!).getByRole("button", { name: "Retry" });
    const apiKeyRequestsBefore = apiKeyRequests;
    const reportsRequestsBefore = reportsRequests.length;
    const optionsRequestsBefore = optionsRequests.length;

    await user.click(retryButton);

    await waitFor(() => expect(apiKeyRequests).toBe(apiKeyRequestsBefore + 1));
    expect(reportsRequests).toHaveLength(reportsRequestsBefore);
    expect(optionsRequests).toHaveLength(optionsRequestsBefore);
    expect([...reportsRequests, ...optionsRequests].filter(isInverted)).toHaveLength(0);
  });
});
