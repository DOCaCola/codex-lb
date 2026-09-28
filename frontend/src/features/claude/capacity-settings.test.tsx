import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ClaudeCapacitySettings } from "./capacity-settings";

describe("Claude capacity settings", () => {
  it("saves a limit and clears to unlimited", async () => {
    const user = userEvent.setup();
    const save = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<ClaudeCapacitySettings value={null} readOnly={false} onSave={save} />);
    const input = screen.getByRole("spinbutton", { name: "Maximum concurrent requests" });
    await user.type(input, "3");
    await user.click(screen.getByRole("button", { name: "Save concurrency limit" }));
    expect(save).toHaveBeenLastCalledWith(3);
    rerender(<ClaudeCapacitySettings value={3} readOnly={false} onSave={save} />);
    await user.clear(input);
    await user.click(screen.getByRole("button", { name: "Save concurrency limit" }));
    expect(save).toHaveBeenLastCalledWith(null);
  });

  it("rejects zero and disables read-only controls", async () => {
    const user = userEvent.setup();
    const save = vi.fn();
    const { rerender } = render(<ClaudeCapacitySettings value={null} readOnly={false} onSave={save} />);
    await user.type(screen.getByRole("spinbutton"), "0");
    expect(screen.getByRole("button")).toBeDisabled();
    rerender(<ClaudeCapacitySettings value={null} readOnly onSave={save} />);
    expect(screen.getByRole("spinbutton")).toBeDisabled();
    expect(save).not.toHaveBeenCalled();
  });
});
