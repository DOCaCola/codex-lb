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
  const save = vi.fn().mockResolvedValue(overrides);
  const setVisibility = vi.fn();
  useModelContextWindowOverridesMock.mockReturnValue({
    overridesQuery: { data: overrides, error: null, isLoading: false },
    saveMutation: { mutateAsync: save, isPending: false, error: null },
    visibilityMutation: { mutate: setVisibility, isPending: false, error: null },
  });
  return { save, setVisibility };
}

function withExtraModels() {
  const base = createModelContextWindowOverrides();
  return createModelContextWindowOverrides({
    models: [
      ...base.models,
      {
        slug: "openrouter/z-ai/glm-5.3-flash",
        displayName: "GLM 5.3 Flash",
        providerDisplayName: "Z.ai: GLM 5.3 Flash",
        renamed: true,
        image: false,
        provider: "openrouter",
        defaultContextWindow: 256000,
        maxContextWindow: 256000,
        listed: true,
        redirectTargetModel: null,
        redirectTargetOverrideTokens: null,
        retired: false,
      },
      {
        slug: "openai-apikey/gpt-image-2.6-sunburst",
        displayName: "gpt-image-2.6-sunburst",
        providerDisplayName: "gpt-image-2.6-sunburst",
        renamed: false,
        image: true,
        provider: "openai_apikey",
        defaultContextWindow: null,
        maxContextWindow: null,
        listed: true,
        redirectTargetModel: null,
        redirectTargetOverrideTokens: null,
        retired: false,
      },
    ],
  });
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

  it("lists each model's reported window with its source, default and maximum", () => {
    mockHook();
    render(<ModelCatalogueSettings />);

    expect(screen.getByText("Model catalogue")).toBeInTheDocument();
    expect(screen.getByText(/Clients compact at 90% of the context window/)).toBeInTheDocument();

    const dashboardRow = row("gpt-5.4");
    expect(within(dashboardRow).getByText("GPT-5.4")).toBeInTheDocument();
    expect(within(dashboardRow).getByText("515,000")).toBeInTheDocument();
    expect(within(dashboardRow).getByText("Dashboard")).toBeInTheDocument();
    expect(within(dashboardRow).getByText("default 272,000 · max 1,000,000")).toBeInTheDocument();

    const envRow = row("gpt-5.5");
    expect(within(envRow).getByText("400,000")).toBeInTheDocument();
    expect(within(envRow).getByText("Environment")).toBeInTheDocument();
    expect(within(envRow).getByText("default 272,000")).toBeInTheDocument();

    const defaultRow = row("anthropic/claude-opus-5-5");
    expect(within(defaultRow).getByText("1,000,000")).toBeInTheDocument();
    expect(within(defaultRow).getByText("max 1,000,000")).toBeInTheDocument();
    expect(within(defaultRow).queryByText("Renamed")).not.toBeInTheDocument();
  });

  it("renames a model and overrides its window in one save", async () => {
    const user = userEvent.setup();
    const { save } = mockHook();
    render(<ModelCatalogueSettings />);

    await user.click(screen.getByRole("button", { name: "Edit anthropic/claude-opus-5-5" }));
    const name = screen.getByLabelText("Name for anthropic/claude-opus-5-5");
    expect(name).toHaveValue("");
    expect(name).toHaveAttribute("placeholder", "Claude Opus 5.5");
    const window = screen.getByLabelText("Context window for anthropic/claude-opus-5-5");
    expect(window).toHaveValue("");

    await user.type(window, "1000001");
    expect(screen.getByText("Above the model maximum of 1,000,000")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();

    await user.clear(window);
    await user.type(window, "350000");
    await user.type(name, "Opus");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(save).toHaveBeenCalledWith({
      slug: "anthropic/claude-opus-5-5",
      displayName: "Opus",
      contextWindow: 350000,
    });
  });

  it("returns a dashboard window to the environment value", async () => {
    const user = userEvent.setup();
    const { save } = mockHook();
    render(<ModelCatalogueSettings />);

    await user.click(screen.getByRole("button", { name: "Edit gpt-5.4" }));
    const window = screen.getByLabelText("Context window for gpt-5.4");
    expect(window).toHaveValue("515000");
    expect(screen.getByText("Default 272,000 · maximum 1,000,000 · environment sets 300,000")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Use environment value" }));
    expect(window).toHaveValue("");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(save).toHaveBeenCalledWith({ slug: "gpt-5.4", contextWindow: null });
  });

  it("rejects a window that is not a whole number", async () => {
    const user = userEvent.setup();
    mockHook();
    render(<ModelCatalogueSettings />);

    await user.click(screen.getByRole("button", { name: "Edit gpt-5.5" }));
    await user.type(screen.getByLabelText("Context window for gpt-5.5"), "0");
    expect(screen.getByText("Enter a whole number of tokens")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("shows a renamed model with its provider name and restores it", async () => {
    const user = userEvent.setup();
    const { save } = mockHook(withExtraModels());
    render(<ModelCatalogueSettings />);

    const renamed = row("openrouter/z-ai/glm-5.3-flash");
    expect(within(renamed).getByText("GLM 5.3 Flash")).toBeInTheDocument();
    expect(within(renamed).getByText("Renamed")).toBeInTheDocument();
    expect(within(renamed).getByText("Provider name: Z.ai: GLM 5.3 Flash")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Edit openrouter/z-ai/glm-5.3-flash" }));
    expect(screen.getByLabelText("Name for openrouter/z-ai/glm-5.3-flash")).toHaveValue("GLM 5.3 Flash");
    await user.click(screen.getByRole("button", { name: "Use provider name" }));
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(save).toHaveBeenCalledWith({ slug: "openrouter/z-ai/glm-5.3-flash", displayName: null });
  });

  it("names image models without a context window", async () => {
    const user = userEvent.setup();
    const { save } = mockHook(withExtraModels());
    render(<ModelCatalogueSettings />);

    const image = row("openai-apikey/gpt-image-2.6-sunburst");
    expect(within(image).getByText("Image")).toBeInTheDocument();
    expect(within(image).getByText("—")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Edit openai-apikey/gpt-image-2.6-sunburst" }));
    expect(screen.getByText("Not applicable to image models.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Context window for openai-apikey/gpt-image-2.6-sunburst")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Name for openai-apikey/gpt-image-2.6-sunburst"), "GPT Image 2.6 Sunburst{Enter}");

    expect(save).toHaveBeenCalledWith({
      slug: "openai-apikey/gpt-image-2.6-sunburst",
      displayName: "GPT Image 2.6 Sunburst",
    });
  });

  it("saves nothing when the name equals the provider name", async () => {
    const user = userEvent.setup();
    const { save } = mockHook();
    render(<ModelCatalogueSettings />);

    await user.click(screen.getByRole("button", { name: "Edit gpt-5.5" }));
    await user.type(screen.getByLabelText("Name for gpt-5.5"), "GPT-5.5");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(save).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("Name for gpt-5.5")).not.toBeInTheDocument();
  });

  it("shows the empty state when no model is enabled", () => {
    mockHook(createModelContextWindowOverrides({ models: [], overrides: [] }));
    render(<ModelCatalogueSettings />);
    expect(screen.getByText("No enabled models")).toBeInTheDocument();
  });

  it("disables actions when the page is read-only", () => {
    mockHook();
    render(<ModelCatalogueSettings disabled />);
    for (const button of screen.getAllByRole("button", { name: /^Edit / })) {
      expect(button).toBeDisabled();
    }
    for (const toggle of screen.getAllByRole("switch")) {
      expect(toggle).toBeDisabled();
    }
  });

  it("groups models by provider and shows whether clients list them", () => {
    mockHook();
    render(<ModelCatalogueSettings />);

    const groupHeaders = screen.getAllByRole("row").map((element) => element.textContent);
    expect(groupHeaders).toContain("OpenAI1 hidden");
    expect(groupHeaders).toContain("Claude");
    expect(within(row("gpt-5.4")).getByRole("switch", { name: "Show gpt-5.4 in client model lists" })).toBeChecked();
    expect(within(row("gpt-5.4")).getByText("Listed")).toBeInTheDocument();
    expect(within(row("gpt-5.5")).getByRole("switch")).not.toBeChecked();
    expect(within(row("gpt-5.5")).getByText("Hidden")).toBeInTheDocument();
    expect(screen.getByText(/Changing a name or which models are listed/)).toBeInTheDocument();
  });

  it("hides and lists models with the switch", async () => {
    const user = userEvent.setup();
    const { setVisibility } = mockHook();
    render(<ModelCatalogueSettings />);

    await user.click(within(row("gpt-5.4")).getByRole("switch"));
    expect(setVisibility).toHaveBeenCalledWith({ slug: "gpt-5.4", listed: false });
    await user.click(within(row("gpt-5.5")).getByRole("switch"));
    expect(setVisibility).toHaveBeenCalledWith({ slug: "gpt-5.5", listed: true });
  });

  it("filters by client list visibility", async () => {
    const user = userEvent.setup();
    mockHook();
    render(<ModelCatalogueSettings />);

    expect(screen.getByRole("radio", { name: "All 3" })).toBeChecked();
    await user.click(screen.getByRole("radio", { name: "Hidden 1" }));
    expect(screen.getByText("gpt-5.5")).toBeInTheDocument();
    expect(screen.queryByText("gpt-5.4")).not.toBeInTheDocument();
    expect(screen.queryByText("anthropic/claude-opus-5-5")).not.toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "Listed 2" }));
    expect(screen.queryByText("gpt-5.5")).not.toBeInTheDocument();
    expect(screen.getByText("gpt-5.4")).toBeInTheDocument();
  });

  it("filters by provider and searches names and model IDs", async () => {
    const user = userEvent.setup();
    mockHook(withExtraModels());
    render(<ModelCatalogueSettings />);

    expect(screen.getByRole("radio", { name: "All providers 5" })).toBeChecked();
    await user.click(screen.getByRole("radio", { name: "OpenRouter 1" }));
    expect(screen.getByText("openrouter/z-ai/glm-5.3-flash")).toBeInTheDocument();
    expect(screen.queryByText("gpt-5.4")).not.toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "All providers 5" }));
    await user.type(screen.getByLabelText("Search models"), "z.ai");
    expect(screen.getByText("openrouter/z-ai/glm-5.3-flash")).toBeInTheDocument();
    expect(screen.queryByText("gpt-5.4")).not.toBeInTheDocument();

    await user.clear(screen.getByLabelText("Search models"));
    await user.type(screen.getByLabelText("Search models"), "sunburst");
    expect(screen.getByText("openai-apikey/gpt-image-2.6-sunburst")).toBeInTheDocument();
    expect(screen.queryByText("openrouter/z-ai/glm-5.3-flash")).not.toBeInTheDocument();
  });

  it("explains an empty filter", async () => {
    const user = userEvent.setup();
    mockHook(
      createModelContextWindowOverrides({
        models: createModelContextWindowOverrides().models.map((model) => ({ ...model, listed: true })),
      }),
    );
    render(<ModelCatalogueSettings />);

    await user.click(screen.getByRole("radio", { name: "Hidden 0" }));
    expect(screen.getByText("No models match.")).toBeInTheDocument();
  });
});
