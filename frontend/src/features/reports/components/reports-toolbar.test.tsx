import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/utils";

import { REPORT_SECTION_DEFINITIONS } from "../hooks/use-report-sections";
import type { ReportsFilterState } from "../hooks/use-reports";
import { ReportsToolbar, type ReportsToolbarProps } from "./reports-toolbar";

const FILTERS: ReportsFilterState = {
  startDate: "2026-10-25",
  endDate: "2026-10-31",
  accounts: [],
  apiKeyIds: [],
  models: [],
  useragents: [],
};

function renderToolbar(overrides: Partial<ReportsToolbarProps> = {}) {
  const props: ReportsToolbarProps = {
    filters: FILTERS,
    preset: "7d",
    accountOptions: [],
    apiKeyOptions: [],
    modelOptions: [{ value: "gpt-6.1-sol", label: "gpt-6.1-sol" }],
    useragentOptions: [],
    showComparison: true,
    generatedAt: undefined,
    refreshing: false,
    visibleSectionIds: REPORT_SECTION_DEFINITIONS.map(({ id }) => id),
    onPresetChange: vi.fn(),
    onFiltersChange: vi.fn(),
    onRefresh: vi.fn(),
    onSectionVisibleChange: vi.fn(),
    ...overrides,
  };
  const view = renderWithProviders(<ReportsToolbar {...props} />);
  return { ...props, view };
}

describe("ReportsToolbar", () => {
  it("labels a preset range and its comparison window", async () => {
    const user = userEvent.setup();
    const props = renderToolbar();

    // Text matchers collapse the thin spaces Intl puts around the range dash.
    expect(screen.getByTestId("reports-range-label")).toHaveTextContent("Sun, Oct 25 – Sat, Oct 31, 2026");
    expect(screen.getByText("compared with Oct 18 – 24")).toBeInTheDocument();
    expect(screen.queryByLabelText("Start date")).not.toBeInTheDocument();

    await user.click(within(screen.getByRole("group", { name: "Date range" })).getByRole("button", { name: "30d" }));
    expect(props.onPresetChange).toHaveBeenCalledWith("30d");
  });

  it("hides the comparison when the report has none", () => {
    renderToolbar({ showComparison: false });

    expect(screen.queryByText(/compared with/)).not.toBeInTheDocument();
  });

  it("marks an inverted custom range as invalid and disables refresh", () => {
    renderToolbar({ preset: "custom", filters: { ...FILTERS, startDate: "2026-10-30", endDate: "2026-10-29" } });

    const start = screen.getByLabelText("Start date");
    const error = screen.getByText("Start date must be on or before end date.");
    expect(start).toHaveAttribute("aria-invalid", "true");
    expect(start).toHaveAttribute("aria-describedby", error.id);
    expect(screen.getByLabelText("End date")).toHaveAttribute("aria-describedby", error.id);
    expect(screen.getByRole("button", { name: "Refresh" })).toBeDisabled();
  });

  it("offers Reset only while a filter is active and clears every filter", async () => {
    const user = userEvent.setup();
    const { view } = renderToolbar();
    expect(screen.queryByRole("button", { name: "Reset" })).not.toBeInTheDocument();
    view.unmount();

    const active = { ...FILTERS, models: ["gpt-6.1-sol"], apiKeyIds: ["key-1"] };
    const props = renderToolbar({ filters: active });
    await user.click(screen.getByRole("button", { name: "Reset" }));
    expect(props.onFiltersChange).toHaveBeenCalledWith({ ...FILTERS });
  });

  it("toggles section visibility from the Sections menu", async () => {
    const user = userEvent.setup();
    const props = renderToolbar({ visibleSectionIds: ["trend", "table"] });

    await user.click(screen.getByRole("button", { name: "Sections (2)" }));
    const item = await screen.findByRole("menuitemcheckbox", { name: "Latency & throughput" });
    expect(item).toHaveAttribute("aria-checked", "false");
    await user.click(item);
    expect(props.onSectionVisibleChange).toHaveBeenCalledWith("perf", true);
  });
});
