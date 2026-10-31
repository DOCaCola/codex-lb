import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type PropsWithChildren } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { get } from "@/lib/api-client";
import { useReports, useReportsOptions, useThreadIdentity, type ReportsFilterState } from "./use-reports";

vi.mock("@/lib/api-client", () => ({ get: vi.fn().mockResolvedValue({}) }));

const getMock = vi.mocked(get);

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return function Wrapper({ children }: PropsWithChildren) {
    return createElement(QueryClientProvider, { client }, children);
  };
}

function requestedUrls(): URL[] {
  return getMock.mock.calls.map(([url]) => new URL(String(url), "http://localhost"));
}

const FILTERS: ReportsFilterState = {
  startDate: "2026-10-25",
  endDate: "2026-10-31",
  accounts: ["source:src-claude", "account:acc-b", "account:acc-a"],
  apiKeyIds: ["key-1"],
  models: ["gpt-6.1-sol", "gpt-6-astra"],
  useragents: ["Missing User-Agent", "Codex Desktop"],
};

beforeEach(() => {
  getMock.mockClear();
});

describe("useReports", () => {
  it("sends every selection as a repeated parameter and provider accounts as model sources", async () => {
    renderHook(() => useReports(FILTERS, "Europe/Berlin"), { wrapper: wrapper() });

    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(1));
    const [url] = requestedUrls();
    expect(url.pathname).toBe("/api/reports");
    expect(url.searchParams.get("start_date")).toBe("2026-10-25");
    expect(url.searchParams.get("end_date")).toBe("2026-10-31");
    expect(url.searchParams.get("timezone")).toBe("Europe/Berlin");
    expect(url.searchParams.getAll("account_id")).toEqual(["acc-a", "acc-b"]);
    expect(url.searchParams.getAll("model_source_id")).toEqual(["src-claude"]);
    expect(url.searchParams.getAll("api_key_id")).toEqual(["key-1"]);
    expect(url.searchParams.getAll("model")).toEqual(["gpt-6-astra", "gpt-6.1-sol"]);
    expect(url.searchParams.getAll("useragent_group")).toEqual(["Codex Desktop", "Missing User-Agent"]);
  });

  it("sends nothing while the range is inverted", async () => {
    renderHook(() => useReports({ ...FILTERS, startDate: "2026-11-01" }, undefined), { wrapper: wrapper() });

    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(getMock).not.toHaveBeenCalled();
  });
});

describe("useReportsOptions", () => {
  it("is scoped by dates, accounts and API keys but not by model or user agent", async () => {
    const { rerender } = renderHook((filters: ReportsFilterState) => useReportsOptions(filters, undefined), {
      wrapper: wrapper(),
      initialProps: FILTERS,
    });
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(1));

    rerender({ ...FILTERS, models: [], useragents: ["Codex Desktop"] });
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(getMock).toHaveBeenCalledTimes(1);
    const [url] = requestedUrls();
    expect(url.pathname).toBe("/api/reports/options");
    expect(url.searchParams.getAll("model_source_id")).toEqual(["src-claude"]);
    expect(url.searchParams.has("model")).toBe(false);
    expect(url.searchParams.has("useragent_group")).toBe(false);
  });
});

describe("useThreadIdentity", () => {
  it("requests only while enabled and only by date range", async () => {
    const { rerender } = renderHook((enabled: boolean) => useThreadIdentity(FILTERS, undefined, enabled), {
      wrapper: wrapper(),
      initialProps: false,
    });
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(getMock).not.toHaveBeenCalled();

    rerender(true);

    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(1));
    const [url] = requestedUrls();
    expect(url.pathname).toBe("/api/reports/thread-identity");
    expect([...url.searchParams.keys()].sort()).toEqual(["end_date", "start_date"]);
  });
});
