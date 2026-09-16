import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/utils";
import { ModelSourceCreateDialog } from "./model-source-create-dialog";

describe("ModelSourceCreateDialog", () => {
  it("creates models with independent names and prices", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderWithProviders(
      <ModelSourceCreateDialog
        open
        busy={false}
        onOpenChange={vi.fn()}
        onSubmit={onSubmit}
      />,
    );
    await user.type(screen.getByLabelText("Name"), "Provider");
    await user.type(
      screen.getByLabelText("Base URL"),
      "https://example.com/v1",
    );
    await user.type(screen.getByLabelText("Model ID"), "one");
    await user.type(screen.getByLabelText("Display name"), "First model");
    await user.type(screen.getByLabelText("Input"), "0");
    await user.click(screen.getByRole("button", { name: "Add model" }));
    await user.type(screen.getByLabelText("Model ID"), "two");
    await user.type(screen.getByLabelText("Output"), "3.25");
    await user.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce());
    expect(onSubmit.mock.calls[0][0].models).toEqual([
      expect.objectContaining({
        model: "one",
        displayName: "First model",
        inputPer1M: 0,
        outputPer1M: null,
      }),
      expect.objectContaining({
        model: "two",
        displayName: null,
        inputPer1M: null,
        outputPer1M: 3.25,
      }),
    ]);
  });

  it("clears a cancelled draft on reopen", async () => {
    const user = userEvent.setup();
    const props = { busy: false, onOpenChange: vi.fn(), onSubmit: vi.fn() };
    const { rerender } = renderWithProviders(
      <ModelSourceCreateDialog open {...props} />,
    );
    await user.type(screen.getByLabelText("Model ID"), "discard-me");
    rerender(<ModelSourceCreateDialog open={false} {...props} />);
    rerender(<ModelSourceCreateDialog open {...props} />);
    expect(screen.getByLabelText("Model ID")).toHaveValue("");
  });
});
