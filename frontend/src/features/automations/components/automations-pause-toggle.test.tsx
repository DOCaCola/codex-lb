import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AutomationsPauseToggle } from "@/features/automations/components/automations-pause-toggle";
import type { SettingsSectionContext } from "@/features/settings/use-settings-section";
import { buildSettingsUpdateRequest } from "@/features/settings/payload";
import type { DashboardSettings } from "@/features/settings/schemas";
import { createDashboardSettings } from "@/test/mocks/factories";

const onSave = vi.fn();

/** The toggle inside a settings section, with the layout's context. */
function renderToggle(settings: DashboardSettings, { controlsDisabled = false } = {}) {
  const context: SettingsSectionContext = {
    settings,
    saving: false,
    controlsDisabled,
    onSave,
    refetchSettings: vi.fn(),
  };
  return render(
    <MemoryRouter>
      <Routes>
        <Route element={<Outlet context={context} />}>
          <Route index element={<AutomationsPauseToggle />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("AutomationsPauseToggle", () => {
  beforeEach(() => {
    onSave.mockReset();
    onSave.mockResolvedValue(undefined);
  });

  it("shows the running state and pauses through the shared dashboard setting", async () => {
    const user = userEvent.setup();
    const settings = createDashboardSettings({
      automationsSchedulerEnabled: true,
      provenance: { automations_scheduler_enabled: { source: "default", envValue: true, default: true } },
    });
    renderToggle(settings);

    const toggle = screen.getByRole("switch", { name: "Pause all automations" });
    expect(toggle).not.toBeChecked();
    expect(screen.queryByText("Paused")).not.toBeInTheDocument();
    expect(screen.getByText("Default (on)")).toBeInTheDocument();

    await user.click(toggle);

    expect(onSave).toHaveBeenCalledWith(buildSettingsUpdateRequest(settings, { automationsSchedulerEnabled: false }));
  });

  it("shows the paused state and resets to inherited with an explicit null", async () => {
    const user = userEvent.setup();
    const settings = createDashboardSettings({
      automationsSchedulerEnabled: false,
      provenance: { automations_scheduler_enabled: { source: "dashboard", envValue: true, default: true } },
    });
    renderToggle(settings);

    expect(screen.getByRole("switch", { name: "Pause all automations" })).toBeChecked();
    expect(screen.getByText("Paused")).toBeInTheDocument();
    expect(screen.getByText(/Run now is refused/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Reset to inherited" }));

    const payload = buildSettingsUpdateRequest(settings, { automationsSchedulerEnabled: null });
    expect(payload.automationsSchedulerEnabled).toBeNull();
    expect(onSave).toHaveBeenCalledWith(payload);
  });

  it("disables the switch and the reset action for a read-only viewer", () => {
    const settings = createDashboardSettings({
      automationsSchedulerEnabled: false,
      provenance: { automations_scheduler_enabled: { source: "dashboard", envValue: true, default: true } },
    });
    renderToggle(settings, { controlsDisabled: true });

    // The state stays readable (the badge and the paused copy), but writing the
    // shared setting needs write access, so neither control can start a PUT.
    expect(screen.getByRole("switch", { name: "Pause all automations" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reset to inherited" })).toBeDisabled();
    expect(screen.getByText("Paused")).toBeInTheDocument();
  });
});
