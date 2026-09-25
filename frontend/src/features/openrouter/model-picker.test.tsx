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
      },
    ],
  },
};

describe("OpenRouter model selection", () => {
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
