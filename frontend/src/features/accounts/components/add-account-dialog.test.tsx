import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AddAccountDialog } from "./add-account-dialog";

const props = () => ({
  open: true,
  onOpenChange: vi.fn(),
  codex: { onSignIn: vi.fn(), onImport: vi.fn() },
  claude: { onSignIn: vi.fn(), onImport: vi.fn() },
  antigravity: { onSignIn: vi.fn(), onImport: vi.fn() },
  onOpenRouter: vi.fn(),
  onOpenAICompatible: vi.fn(),
});

describe("AddAccountDialog", () => {
  it("lists subscriptions first, each with sign-in and file import, then API providers", () => {
    render(<AddAccountDialog {...props()} />);
    const groups = screen.getAllByRole("group");
    expect(groups.map((group) => group.querySelector("legend")?.textContent))
      .toEqual(["Codex", "Claude", "Antigravity", "API providers"]);
    for (const group of groups.slice(0, 3)) {
      expect(within(group).getAllByRole("button").map((button) => button.querySelector(".font-medium")?.textContent))
        .toEqual(["Sign in", "Import file"]);
      expect(group.querySelector("legend img")).toHaveAttribute("data-provider");
    }
    expect(within(groups[3]!).getAllByRole("button").map((button) => button.querySelector("img")?.dataset.provider))
      .toEqual(["openrouter", "openai_compatible"]);
  });

  it("omits unavailable providers", () => {
    render(<AddAccountDialog {...props()} claude={undefined} antigravity={undefined}
      onOpenRouter={undefined} onOpenAICompatible={undefined} />);
    expect(screen.getAllByRole("group")).toHaveLength(1);
    expect(screen.getByRole("group", { name: "Codex" })).toBeVisible();
  });

  it.each([
    ["Codex", "Sign in", (p: ReturnType<typeof props>) => p.codex.onSignIn],
    ["Codex", "Import file", (p: ReturnType<typeof props>) => p.codex.onImport],
    ["Claude", "Sign in", (p: ReturnType<typeof props>) => p.claude.onSignIn],
    ["Claude", "Import file", (p: ReturnType<typeof props>) => p.claude.onImport],
    ["Antigravity", "Sign in", (p: ReturnType<typeof props>) => p.antigravity.onSignIn],
    ["Antigravity", "Import file", (p: ReturnType<typeof props>) => p.antigravity.onImport],
    ["API providers", "OpenRouter", (p: ReturnType<typeof props>) => p.onOpenRouter],
    ["API providers", "OpenAI-compatible", (p: ReturnType<typeof props>) => p.onOpenAICompatible],
  ] as const)("hands off %s / %s after closing", async (group, option, action) => {
    const callbacks = props();
    render(<AddAccountDialog {...callbacks} />);
    await userEvent.click(within(screen.getByRole("group", { name: group })).getByRole("button", { name: new RegExp(`^${option}`) }));
    const handler = action(callbacks);
    await vi.waitFor(() => expect(handler).toHaveBeenCalledOnce());
    expect(callbacks.onOpenChange).toHaveBeenCalledWith(false);
    expect(callbacks.onOpenChange.mock.invocationCallOrder[0]).toBeLessThan(handler.mock.invocationCallOrder[0]!);
  });
});
