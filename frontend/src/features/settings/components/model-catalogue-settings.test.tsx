import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ModelCatalogueSettings } from "@/features/settings/components/model-catalogue-settings";
import { createModelContextWindowOverrides } from "@/test/mocks/factories";

const useModelContextWindowOverridesMock = vi.fn();

vi.mock("@/features/settings/hooks/use-settings", () => ({
  useModelContextWindowOverrides: () => useModelContextWindowOverridesMock(),
}));

function mockHook(overrides = createModelContextWindowOverrides()) {
  const upsert = vi.fn().mockResolvedValue(overrides);
  const remove = vi.fn().mockResolvedValue(overrides);
  useModelContextWindowOverridesMock.mockReturnValue({
    overridesQuery: { data: overrides, error: null, isLoading: false },
    upsertMutation: { mutateAsync: upsert, isPending: false, error: null },
    deleteMutation: { mutateAsync: remove, isPending: false, error: null },
  });
  return { upsert, remove };
}

function row(slug: string): HTMLElement {
  const element = screen.getByText(slug).closest("tr");
  expect(element).not.toBeNull();
  return element as HTMLElement;
}

describe("ModelCatalogueSettings", () => {
  beforeEach(() => {
    useModelContextWindowOverridesMock.mockReset();
  });

  it("lists enabled models with default, maximum and reported window", () => {
    mockHook();
    render(<ModelCatalogueSettings />);

    expect(screen.getByText("Model catalogue")).toBeInTheDocument();
    expect(screen.getByText(/clients compact at 90% of it/)).toBeInTheDocument();

    const dashboardRow = row("gpt-5.4");
    expect(within(dashboardRow).getByText("GPT-5.4")).toBeInTheDocument();
    expect(within(dashboardRow).getByText("272,000")).toBeInTheDocument();
    expect(within(dashboardRow).getByText("1,000,000")).toBeInTheDocument();
    expect(within(dashboardRow).getByText("515,000")).toBeInTheDocument();
    expect(within(dashboardRow).getByText("Dashboard")).toBeInTheDocument();
    expect(within(dashboardRow).getByText("Environment: 300,000")).toBeInTheDocument();
    // A dashboard override that shadows an environment entry resets to it instead of vanishing.
    expect(within(dashboardRow).getByRole("button", { name: "Reset to inherited" })).toBeInTheDocument();

    const envRow = row("gpt-5.5");
    expect(within(envRow).getByText("—")).toBeInTheDocument();
    expect(within(envRow).getByText("Inherited from environment (400,000)")).toBeInTheDocument();
    expect(within(envRow).queryByRole("button", { name: "Reset to inherited" })).not.toBeInTheDocument();
    expect(within(envRow).getByRole("button", { name: "Override" })).toBeInTheDocument();

    const defaultRow = row("anthropic/claude-opus-5-5");
    expect(within(defaultRow).getByText("Default")).toBeInTheDocument();
    expect(within(defaultRow).queryByRole("button", { name: "Remove" })).not.toBeInTheDocument();
  });

  it("overrides a model within its maximum", async () => {
    const user = userEvent.setup();
    const { upsert } = mockHook();
    render(<ModelCatalogueSettings />);

    await user.click(within(row("anthropic/claude-opus-5-5")).getByRole("button", { name: "Override" }));
    const input = screen.getByLabelText("Context window for anthropic/claude-opus-5-5");
    expect(input).toHaveValue("1000000");

    await user.clear(input);
    await user.type(input, "1000001");
    expect(screen.getByText("Above the model maximum of 1,000,000")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();

    await user.clear(input);
    await user.type(input, "350000");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(upsert).toHaveBeenCalledWith({ slug: "anthropic/claude-opus-5-5", contextWindow: 350000 });
  });

  it("overrides an environment-inherited value starting from it", async () => {
    const user = userEvent.setup();
    const { upsert } = mockHook();
    render(<ModelCatalogueSettings />);

    await user.click(within(row("gpt-5.5")).getByRole("button", { name: "Override" }));
    const input = screen.getByLabelText("Context window for gpt-5.5");
    expect(input).toHaveValue("400000");
    await user.clear(input);
    await user.type(input, "0");
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    await user.clear(input);
    await user.type(input, "600000");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(upsert).toHaveBeenCalledWith({ slug: "gpt-5.5", contextWindow: 600000 });
  });

  it("removes a dashboard override after confirmation", async () => {
    const user = userEvent.setup();
    const { remove } = mockHook(
      createModelContextWindowOverrides({
        overrides: [{ slug: "anthropic/claude-opus-5-5", contextWindow: 350000, source: "dashboard", envValue: null }],
      }),
    );
    render(<ModelCatalogueSettings />);

    await user.click(within(row("anthropic/claude-opus-5-5")).getByRole("button", { name: "Remove" }));
    const dialog = screen.getByRole("alertdialog");
    expect(within(dialog).getByText(/anthropic\/claude-opus-5-5/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Remove" }));

    expect(remove).toHaveBeenCalledWith("anthropic/claude-opus-5-5");
  });

  it("shows the empty state when no model is enabled", () => {
    mockHook(createModelContextWindowOverrides({ models: [], overrides: [] }));
    render(<ModelCatalogueSettings />);
    expect(screen.getByText("No enabled models")).toBeInTheDocument();
  });

  it("disables actions when the page is read-only", () => {
    mockHook();
    render(<ModelCatalogueSettings disabled />);
    for (const button of screen.getAllByRole("button", { name: "Override" })) {
      expect(button).toBeDisabled();
    }
  });
});
