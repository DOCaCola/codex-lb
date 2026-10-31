import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/utils";

import { THREAD_IDENTITY } from "../test-fixtures";
import { RoutingDiagnosticsCard } from "./routing-diagnostics-card";

describe("RoutingDiagnosticsCard", () => {
  it("stays collapsed until opened", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    renderWithProviders(<RoutingDiagnosticsCard open={false} onOpenChange={onOpenChange} data={undefined} error={null} />);

    const toggle = screen.getByRole("button", { name: /Routing diagnostics/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByTestId("reports-diagnostics-cache-hit")).not.toBeInTheDocument();
    await user.click(toggle);
    expect(onOpenChange).toHaveBeenCalledWith(true);
  });

  it("shows the headline stats and the four tiles once loaded", () => {
    renderWithProviders(<RoutingDiagnosticsCard open onOpenChange={vi.fn()} data={THREAD_IDENTITY} error={null} />);

    expect(screen.getByTestId("reports-diagnostics-stats")).toHaveTextContent("1.25 accounts / conversation");
    expect(screen.getByTestId("reports-diagnostics-accounts-per-conversation")).toHaveTextContent("1.25");
    expect(screen.getByTestId("reports-diagnostics-single-account")).toHaveTextContent("80.0%");
    expect(screen.getByTestId("reports-diagnostics-switch-rate")).toHaveTextContent("5.0%");
    expect(screen.getByTestId("reports-diagnostics-cache-hit")).toHaveTextContent("92.0%");
    expect(screen.getByTestId("reports-diagnostics-note")).toBeInTheDocument();
  });

  it("explains an unavailable range and reports load errors", () => {
    const view = renderWithProviders(
      <RoutingDiagnosticsCard open onOpenChange={vi.fn()} data={{ ...THREAD_IDENTITY, available: false }} error={null} />,
    );
    expect(screen.getByText(/available for date ranges of 7 days or less/)).toBeInTheDocument();
    expect(screen.queryByTestId("reports-diagnostics-stats")).not.toBeInTheDocument();
    view.unmount();

    renderWithProviders(<RoutingDiagnosticsCard open onOpenChange={vi.fn()} data={undefined} error="boom" />);
    expect(screen.getByText("Failed to load routing diagnostics: boom")).toBeInTheDocument();
  });
});
