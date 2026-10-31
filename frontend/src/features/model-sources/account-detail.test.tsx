import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderProvidersList } from "@/features/accounts/test-utils";
import { createModelSource } from "@/test/mocks/factories";
import { renderWithProviders } from "@/test/utils";
import { ModelSourceAccountDetail } from "./account-detail";

describe("OpenAI-compatible provider accounts", () => {
  it("lists sources with the other accounts and filters them by status and search", async () => {
    const user = userEvent.setup();
    renderProvidersList({
      modelSources: [
        createModelSource(),
        createModelSource({
          id: "src_litellm",
          name: "LiteLLM",
          baseUrl: "http://litellm:4000/v1",
          isEnabled: false,
          models: [],
        }),
      ],
    });

    const group = screen.getByRole("rowgroup", { name: "OpenAI-compatible" });
    expect(within(group).getAllByTestId("provider-account-row")).toHaveLength(2);
    expect(screen.getByText("http://localhost:8000/v1")).toBeInTheDocument();
    expect(screen.getByText("1 model")).toBeInTheDocument();
    expect(screen.getByText("0 models")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "LiteLLM" })).toHaveAttribute("href", "/providers/src_litellm");

    await user.click(screen.getByRole("button", { name: /^Paused/ }));
    expect(screen.queryByText("vLLM")).not.toBeInTheDocument();
    expect(screen.getByText("LiteLLM")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^All/ }));

    await user.type(screen.getByPlaceholderText("Search accounts..."), "localhost:8000");
    expect(screen.getByText("vLLM")).toBeInTheDocument();
    expect(screen.queryByText("LiteLLM")).not.toBeInTheDocument();
  });

  it("shows the connection and models and routes actions", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    renderWithProviders(
      <ModelSourceAccountDetail
        source={createModelSource({ timeoutSeconds: 30 })}
        readOnly={false}
        busy={false}
        onRename={vi.fn()}
        onToggle={onToggle}
        onEdit={onEdit}
        onDelete={onDelete}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Settings" }));
    expect(screen.getByText("http://localhost:8000/v1")).toBeInTheDocument();
    expect(screen.getByText("Chat Completions")).toBeInTheDocument();
    expect(screen.getByText("30 s")).toBeInTheDocument();
    expect(screen.getByText("local-coder")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Pause" }));
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "Delete account" }));
    expect(onToggle).toHaveBeenCalledWith(false);
    expect(onEdit).toHaveBeenCalledOnce();
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it("disables every action for read-only sessions", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <ModelSourceAccountDetail
        source={createModelSource()}
        readOnly
        busy={false}
        onRename={vi.fn()}
        onToggle={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Settings" }));
    for (const name of ["Pause", "Edit"]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
    }
    await user.click(screen.getByRole("button", { name: "More actions" }));
    for (const name of ["Edit", "Delete account"])
      expect(await screen.findByRole("menuitem", { name })).toHaveAttribute("aria-disabled", "true");
  });
});
