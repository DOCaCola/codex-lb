import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  normalizeReportSectionIds,
  REPORT_SECTION_VISIBILITY_STORAGE_KEY,
  useReportSections,
} from "./use-report-sections";

const ALL_SECTIONS = ["trend", "breakdown", "perf", "table", "diagnostics"];

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("useReportSections", () => {
  it("shows every section when nothing is stored", () => {
    const { result } = renderHook(() => useReportSections());

    expect(result.current.visibleSectionIds).toEqual(ALL_SECTIONS);
  });

  it("restores a stored subset", () => {
    window.localStorage.setItem(REPORT_SECTION_VISIBILITY_STORAGE_KEY, JSON.stringify(["table", "trend"]));

    const { result } = renderHook(() => useReportSections());

    expect(result.current.visibleSectionIds).toEqual(["trend", "table"]);
  });

  it("keeps an empty stored selection empty", () => {
    window.localStorage.setItem(REPORT_SECTION_VISIBILITY_STORAGE_KEY, "[]");

    const { result } = renderHook(() => useReportSections());

    expect(result.current.visibleSectionIds).toEqual([]);
  });

  it.each([["not json"], [JSON.stringify({ trend: true })], [JSON.stringify(["trend", 3])]])(
    "falls back to every section for malformed storage %s",
    (stored) => {
      window.localStorage.setItem(REPORT_SECTION_VISIBILITY_STORAGE_KEY, stored);

      const { result } = renderHook(() => useReportSections());

      expect(result.current.visibleSectionIds).toEqual(ALL_SECTIONS);
    },
  );

  it("persists changes in canonical order", () => {
    const { result } = renderHook(() => useReportSections());

    act(() => result.current.setSectionVisible("perf", false));
    act(() => result.current.setSectionVisible("perf", true));
    act(() => result.current.setSectionVisible("trend", false));

    expect(result.current.visibleSectionIds).toEqual(["breakdown", "perf", "table", "diagnostics"]);
    expect(JSON.parse(window.localStorage.getItem(REPORT_SECTION_VISIBILITY_STORAGE_KEY) ?? "null")).toEqual([
      "breakdown",
      "perf",
      "table",
      "diagnostics",
    ]);
  });

  it("keeps in-memory changes when storage fails", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const { result } = renderHook(() => useReportSections());

    act(() => result.current.setSectionVisible("table", false));

    expect(result.current.visibleSectionIds).toEqual(["trend", "breakdown", "perf", "diagnostics"]);
  });
});

describe("normalizeReportSectionIds", () => {
  it("drops unknown and duplicate IDs and orders the rest canonically", () => {
    expect(normalizeReportSectionIds(["diagnostics", "charts", "trend", "diagnostics"])).toEqual(["trend", "diagnostics"]);
  });
});
