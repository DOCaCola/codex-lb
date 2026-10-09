import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AccountList } from "@/features/accounts/components/account-list";
import { createModelSource } from "@/test/mocks/factories";
import { renderWithProviders } from "@/test/utils";
import { ModelSourceAccountDetail } from "./account-detail";

const listProps = {
  accounts: [],
  selectedAccountId: null,
  onOpenImport: () => {},
  onOpenOauth: () => {},
};

describe("OpenAI-compatible provider accounts", () => {
  it("lists sources with the other accounts and filters them by status and search", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <AccountList
        {...listProps}
        onSelect={onSelect}
        modelSources={[
          createModelSource(),
          createModelSource({
            id: "src_litellm",
            name: "LiteLLM",
            baseUrl: "http://litellm:4000/v1",
            isEnabled: false,
            models: [],
          }),
        ]}
      />,
    );

    expect(screen.getByText("vLLM")).toBeInTheDocument();
    expect(screen.getByText("OpenAI-compatible | 1 model")).toBeInTheDocument();
    expect(screen.getByText("OpenAI-compatible | 0 models")).toBeInTheDocument();
    expect(document.querySelectorAll('[data-provider="openai_compatible"]')).toHaveLength(2);

    await user.click(screen.getByText("LiteLLM"));
    expect(onSelect).toHaveBeenCalledWith("src_litellm");

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

    expect(screen.getByText("http://localhost:8000/v1")).toBeInTheDocument();
    expect(screen.getByText("Chat Completions")).toBeInTheDocument();
    expect(screen.getByText("30 s")).toBeInTheDocument();
    expect(screen.getByText("local-coder")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Pause" }));
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(onToggle).toHaveBeenCalledWith(false);
    expect(onEdit).toHaveBeenCalledOnce();
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it("disables every action for read-only sessions", () => {
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

    for (const name of ["Pause", "Edit", "Delete"]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
    }
  });
});
