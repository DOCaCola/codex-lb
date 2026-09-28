import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AddAccountDialog } from "./add-account-dialog";

const props = () => ({
  open: true, onOpenChange: vi.fn(), onAddAccount: vi.fn(),
  onImport: vi.fn(), onClaude: vi.fn(), onOpenRouter: vi.fn(),
});

describe("AddAccountDialog", () => {
  it("groups providers with Codex first and consistent icons", () => {
    render(<AddAccountDialog {...props()} />);
    const groups = screen.getAllByRole("group");
    expect(groups.map((group) => group.querySelector("legend")?.textContent))
      .toEqual(["Codex", "Claude", "OpenRouter"]);
    expect(within(groups[0]!).getAllByRole("button")).toHaveLength(2);
    for (const group of groups) {
      for (const button of within(group).getAllByRole("button")) {
        expect(button.querySelector("svg")).toHaveClass("h-4", "w-4", "shrink-0");
        expect(button.querySelector("svg")?.parentElement).toHaveClass("h-9", "w-9", "shrink-0");
      }
    }
  });
  it("omits unavailable providers", () => {
    render(<AddAccountDialog {...props()} onClaude={undefined} onOpenRouter={undefined} />);
    expect(screen.getAllByRole("group")).toHaveLength(1);
    expect(screen.getByRole("group", { name: "Codex" })).toBeVisible();
  });
  it.each([
    ["Codex", 0, "onAddAccount"], ["Codex", 1, "onImport"],
    ["Claude", 0, "onClaude"], ["OpenRouter", 0, "onOpenRouter"],
  ] as const)("hands off %s option %s after closing", async (provider, index, action) => {
    const callbacks = props();
    render(<AddAccountDialog {...callbacks} />);
    await userEvent.click(within(screen.getByRole("group", { name: provider })).getAllByRole("button")[index]!);
    await vi.waitFor(() => expect(callbacks[action]).toHaveBeenCalledOnce());
    expect(callbacks.onOpenChange).toHaveBeenCalledWith(false);
    expect(callbacks.onOpenChange.mock.invocationCallOrder[0])
      .toBeLessThan(callbacks[action].mock.invocationCallOrder[0]!);
  });
});
