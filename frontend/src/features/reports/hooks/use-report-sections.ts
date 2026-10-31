import { useEffect, useState } from "react";

export const REPORT_SECTION_DEFINITIONS = [
  { id: "trend", labelKey: "reports.sections.trend" },
  { id: "breakdown", labelKey: "reports.sections.breakdown" },
  { id: "perf", labelKey: "reports.sections.perf" },
  { id: "table", labelKey: "reports.sections.table" },
  { id: "diagnostics", labelKey: "reports.sections.diagnostics" },
] as const;

export type ReportSectionId = (typeof REPORT_SECTION_DEFINITIONS)[number]["id"];

export const REPORT_SECTION_VISIBILITY_STORAGE_KEY = "codex-lb-reports-visible-sections";

const REPORT_SECTION_IDS: ReportSectionId[] = REPORT_SECTION_DEFINITIONS.map(({ id }) => id);

/** Known IDs only, each once, in canonical order. */
export function normalizeReportSectionIds(ids: readonly string[]): ReportSectionId[] {
  const requested = new Set(ids);
  return REPORT_SECTION_IDS.filter((id) => requested.has(id));
}

function readInitialReportSectionIds(): ReportSectionId[] {
  try {
    const stored = localStorage.getItem(REPORT_SECTION_VISIBILITY_STORAGE_KEY);
    if (stored === null) {
      return [...REPORT_SECTION_IDS];
    }
    const parsed: unknown = JSON.parse(stored);
    if (!Array.isArray(parsed) || !parsed.every((id): id is string => typeof id === "string")) {
      return [...REPORT_SECTION_IDS];
    }
    return normalizeReportSectionIds(parsed);
  } catch {
    return [...REPORT_SECTION_IDS];
  }
}

export function useReportSections(): {
  visibleSectionIds: ReportSectionId[];
  setSectionVisible: (id: ReportSectionId, visible: boolean) => void;
} {
  const [visibleSectionIds, setVisibleSectionIds] = useState<ReportSectionId[]>(readInitialReportSectionIds);

  useEffect(() => {
    try {
      localStorage.setItem(REPORT_SECTION_VISIBILITY_STORAGE_KEY, JSON.stringify(visibleSectionIds));
    } catch {
      // Storage failures must not prevent the in-memory preference from updating.
    }
  }, [visibleSectionIds]);

  const setSectionVisible = (id: ReportSectionId, visible: boolean) => {
    setVisibleSectionIds((current) =>
      normalizeReportSectionIds(visible ? [...current, id] : current.filter((entry) => entry !== id)),
    );
  };

  return { visibleSectionIds, setSectionVisible };
}
