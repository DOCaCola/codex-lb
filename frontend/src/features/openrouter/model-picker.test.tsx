import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { OpenRouterAccount } from "./api";
import { ModelPicker } from "./model-picker";

const account: OpenRouterAccount = {
  id: "src_test",
  name: "Test",
  isEnabled: true,
  hasManagementKey: false,
  state: {
    selections: [],
    catalog_updated_at: null,
    catalog_error: null,
    key_updated_at: null,
    key_error: null,
    credits_updated_at: null,
    credits_error: null,
    credits: null,
    key: null,
    catalog: [
      {
        id: "vendor/test",
        name: "Test model",
        context_length: 1000000,
        pricing: {
          prompt: 0.000001,
          completion: 0.000002,
          input_cache_read: null,
        },
        supported_parameters: ["tools"],
        architecture: {
          input_modalities: ["text"],
          output_modalities: ["text"],
        },
        top_provider: { context_length: 1000000, max_completion_tokens: 32000 },
        reasoning: null,
        image: null,
      },
    ],
  },
};

describe("OpenRouter model selection", () => {
  it.each(["models", "images"] as const)(
    "preserves other selections when saving %s",
    async (kind) => {
      const user = userEvent.setup();
      const mixed = structuredClone(account);
      mixed.state.catalog.push({
        ...mixed.state.catalog[0]!,
        id: "openai/gpt-image-2.5-sunburst",
        name: "Sunburst",
        image: { supports_streaming: true, endpoint_details: [] },
      });
      mixed.state.selections = [
        "vendor/test",
        "openai/gpt-image-2.5-sunburst",
        "vendor/retired",
      ].map((model) => ({
        model,
        contextWindow: 123456,
        maxOutputTokens: 4096,
        displayName: "Custom name",
      }));
      const save = vi.fn().mockResolvedValue(undefined);
      render(
        <ModelPicker
          account={mixed}
          kind={kind}
          busy={false}
          onClose={vi.fn()}
          onSave={save}
        />,
      );
      const edited = kind === "images" ? "Sunburst" : "Test model";
      const other = kind === "images" ? "Test model" : "Sunburst";
      expect(
        screen.queryByRole("checkbox", { name: other }),
      ).not.toBeInTheDocument();
      await user.click(screen.getByRole("checkbox", { name: edited }));
      await user.click(
        screen.getByRole("button", {
          name: kind === "images" ? "Save 0 image models" : "Save 1 models",
        }),
      );
      const removedId =
        kind === "images" ? "openai/gpt-image-2.5-sunburst" : "vendor/test";
      expect(save).toHaveBeenCalledWith(
        mixed.state.selections.filter((item) => item.model !== removedId),
      );
    },
  );

  it.each([
    "Text generation",
    "Image generation",
    "Vision",
    "Tools",
    "Reasoning",
  ])("filters by %s capability", async (capability) => {
    const user = userEvent.setup();
    const filtered = structuredClone(account);
    const model = filtered.state.catalog[0]!;
    model.architecture.input_modalities = ["text", "image"];
    model.supported_parameters = ["tools", "reasoning"];
    model.image =
      capability === "Image generation"
        ? { supports_streaming: true, endpoint_details: [] }
        : null;
    filtered.state.catalog.push({
      ...model,
      id: "vendor/other",
      name: "Other model",
      image: null,
      architecture: {
        input_modalities: ["audio"],
        output_modalities: ["audio"],
      },
      supported_parameters: [],
    });
    render(
      <ModelPicker
        account={filtered}
        kind={capability === "Image generation" ? "images" : "models"}
        busy={false}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Capabilities" }));
    await user.click(
      screen.getByRole("menuitemcheckbox", { name: capability }),
    );
    await user.keyboard("{Escape}");
    expect(screen.getByText("Test model")).toBeVisible();
    expect(screen.queryByText("Other model")).not.toBeInTheDocument();
  });

  it("combines capabilities and search while preserving hidden and retired selections", async () => {
    const user = userEvent.setup();
    const save = vi.fn().mockResolvedValue(undefined);
    const filtered = structuredClone(account);
    const model = filtered.state.catalog[0]!;
    model.image = { supports_streaming: true, endpoint_details: [] };
    filtered.state.catalog.push({
      ...model,
      id: "vendor/vision",
      name: "Vision model",
      architecture: {
        input_modalities: ["text", "image"],
        output_modalities: ["image"],
      },
    });
    filtered.state.selections = ["vendor/test", "vendor/retired"].map(
      (model) => ({
        model,
        contextWindow: 262144,
        maxOutputTokens: null,
        displayName: null,
      }),
    );
    render(
      <ModelPicker
        account={filtered}
        busy={false}
        onClose={vi.fn()}
        onSave={save}
        kind="images"
      />,
    );
    await user.click(screen.getByRole("button", { name: "Capabilities" }));
    await user.click(
      screen.getByRole("menuitemcheckbox", { name: "Image generation" }),
    );
    await user.click(screen.getByRole("menuitemcheckbox", { name: "Vision" }));
    await user.keyboard("{Escape}");
    expect(screen.queryByText("Test model")).not.toBeInTheDocument();
    expect(screen.queryByText(/Unavailable/)).not.toBeInTheDocument();
    expect(screen.getByText("Vision model")).toBeVisible();
    await user.type(screen.getByLabelText("Search OpenRouter models"), "test");
    expect(screen.getByRole("status")).toHaveTextContent("No models match");
    await user.clear(screen.getByLabelText("Search OpenRouter models"));
    await user.click(screen.getByRole("button", { name: "Capabilities (2)" }));
    await user.click(
      screen.getByRole("menuitem", { name: "Clear capability filters" }),
    );
    expect(
      screen.queryByText("vendor/retired — Unavailable"),
    ).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Save 1 image models" }),
    );
    expect(save).toHaveBeenCalledWith(filtered.state.selections);
  });
  it("shows image prices without conversational context controls", async () => {
    const user = userEvent.setup();
    const images: OpenRouterAccount = structuredClone(account);
    const model = images.state.catalog[0]!;
    model.context_length = null;
    model.architecture.output_modalities = ["image"];
    model.image = {
      supports_streaming: true,
      endpoint_details: [
        {
          provider_name: "OpenAI",
          pricing: [
            {
              billable: "output_image",
              unit: "token",
              cost_usd: 0.00003,
              variant: null,
            },
          ],
        },
      ],
    };
    render(
      <ModelPicker
        account={images}
        kind="images"
        busy={false}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );
    await user.click(screen.getByRole("checkbox"));
    expect(screen.getByText(/Public Images API only/)).toBeVisible();
    expect(screen.getByText(/output_image: \$30 \/ 1M tokens/)).toBeVisible();
    expect(
      screen.queryByLabelText("Context cap for vendor/test"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("Output cap for vendor/test"),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Display name for vendor/test")).toBeVisible();
  });
  it("requires explicit selection and defaults to a bounded context", async () => {
    const user = userEvent.setup();
    const save = vi.fn().mockResolvedValue(undefined);
    render(
      <ModelPicker
        account={account}
        busy={false}
        onClose={vi.fn()}
        onSave={save}
      />,
    );
    expect(screen.getByRole("checkbox")).not.toBeChecked();
    await user.click(screen.getByRole("checkbox"));
    expect(screen.getByLabelText("Context cap for vendor/test")).toHaveValue(
      262144,
    );
    await user.click(screen.getByRole("button", { name: "Save 1 models" }));
    expect(save).toHaveBeenCalledWith([
      {
        model: "vendor/test",
        contextWindow: 262144,
        maxOutputTokens: null,
        displayName: null,
      },
    ]);
  });

  it("keeps retired selections visible so operators can remove them", () => {
    const retired = {
      ...account,
      state: {
        ...account.state,
        catalog: [],
        selections: [
          {
            model: "vendor/retired",
            contextWindow: 262144,
            maxOutputTokens: null,
            displayName: null,
          },
        ],
      },
    };
    render(
      <ModelPicker
        account={retired}
        busy={false}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );
    expect(screen.getByText("vendor/retired — Unavailable")).toBeVisible();
    expect(screen.getByRole("checkbox")).toBeChecked();
  });
});
