import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AccountModelPicker } from "./account-model-picker";

const catalog = [
  {
    model: "test",
    name: "Test model",
    description: "Test",
    available: true,
    reasoningLevels: ["none", "medium", "high"],
  },
];

describe("Account model policy drafts", () => {
  it("saves explicit none in All mode without replacing curated selections", async () => {
    const user = userEvent.setup();
    const save = vi.fn().mockResolvedValue(undefined);
    render(
      <AccountModelPicker
        name="Account"
        provider="Codex"
        catalog={catalog}
        selectedModels={["test"]}
        allModels={true}
        reasoningRestrictions={{}}
        disabled={false}
        onClose={vi.fn()}
        onSave={save}
      />,
    );
    expect(screen.getByRole("checkbox", { name: "Test model" })).toBeDisabled();
    await user.click(
      screen.getByRole("button", { name: "Allowed reasoning for test" }),
    );
    expect(
      screen.getByRole("menuitemcheckbox", { name: "All supported" }),
    ).toBeChecked();
    await user.click(screen.getByRole("menuitemcheckbox", { name: "high" }));
    await user.click(screen.getByRole("menuitemcheckbox", { name: "medium" }));
    expect(
      screen.getByRole("menuitemcheckbox", { name: "None (no reasoning)" }),
    ).toHaveAttribute("aria-disabled", "true");
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Save 1 model" }));
    expect(save).toHaveBeenCalledWith(["test"], true, { test: ["none"] });
  });

  it("does not persist cancelled mode and reasoning changes", async () => {
    const user = userEvent.setup();
    const save = vi.fn();
    const close = vi.fn();
    render(
      <AccountModelPicker
        name="Account"
        provider="Claude"
        catalog={catalog}
        selectedModels={[]}
        allModels={false}
        reasoningRestrictions={{}}
        disabled={false}
        onClose={close}
        onSave={save}
      />,
    );
    await user.click(screen.getByRole("switch", { name: /All models/ }));
    await user.click(
      screen.getByRole("button", { name: "Allowed reasoning for test" }),
    );
    await user.click(screen.getByRole("menuitemcheckbox", { name: "high" }));
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(close).toHaveBeenCalledOnce();
    expect(save).not.toHaveBeenCalled();
  });

  it("keeps missing models and saved efforts editable after unselecting", async () => {
    const user = userEvent.setup();
    const save = vi.fn().mockResolvedValue(undefined);
    render(
      <AccountModelPicker
        name="Account"
        provider="Codex"
        catalog={[]}
        selectedModels={["retired"]}
        allModels={false}
        reasoningRestrictions={{ retired: ["high"] }}
        disabled={false}
        onClose={vi.fn()}
        onSave={save}
      />,
    );
    const model = screen.getByRole("checkbox", {
      name: "retired — Unavailable",
    });
    expect(model).toBeEnabled();
    await user.click(model);
    await user.click(model);
    await user.click(
      screen.getByRole("button", { name: "Allowed reasoning for retired" }),
    );
    expect(
      screen.getByRole("menuitemcheckbox", {
        name: "high — Currently unavailable",
      }),
    ).toBeChecked();
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Save 1 model" }));
    expect(save).toHaveBeenCalledWith(["retired"], false, {
      retired: ["high"],
    });
  });
});
