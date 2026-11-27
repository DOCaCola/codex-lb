import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { ModelCatalogueSettings } from "@/features/settings/components/model-catalogue-settings";
import { ModelRedirectSettings } from "@/features/settings/components/model-redirect-settings";
import { server } from "@/test/mocks/server";
import { renderWithProviders } from "@/test/utils";

describe("ModelRedirectSettings", () => {
  it("adds, changes, and removes a retired redirect and lets the operator list it", async () => {
    const user = userEvent.setup();
    renderWithProviders(<><ModelRedirectSettings /><ModelCatalogueSettings /></>);

    await screen.findByText("No redirects. Requests are served by the model they name.");
    await user.click(screen.getByRole("button", { name: "Add redirect" }));
    const source = screen.getByRole("combobox", { name: "Requested model" });
    const target = screen.getByRole("combobox", { name: "Served model" });
    expect(target).toBeDisabled();
    expect(target).toHaveTextContent("Choose a requested model first");
    await user.click(source);
    await user.type(screen.getByRole("searchbox", { name: "Search or enter a model name…" }), "retired/model");
    await user.click(screen.getByRole("option", { name: /Use “retired\/model”/ }));
    expect(source).toHaveTextContent("retired/model");
    await user.click(target);
    const openai = screen.getByRole("group", { name: "OpenAI" });
    await user.click(within(openai).getByRole("option", { name: "GPT-5.5, hidden" }));
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Active")).toBeInTheDocument();
    const sourceRow = (await screen.findByText("Redirects to GPT-5.5")).closest("tr")!;
    expect(within(sourceRow).getByText("Not in registry")).toBeInTheDocument();
    expect(within(sourceRow).getByText("400,000 · Served model")).toBeInTheDocument();
    // A redirected model can be renamed; its window is the served model's.
    await user.click(within(sourceRow).getByRole("button", { name: "Edit retired/model" }));
    expect(screen.getByText("Uses the served model's context window while redirected")).toBeInTheDocument();
    expect(screen.queryByLabelText("Context window for retired/model")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    const listed = within(sourceRow).getByRole("switch", { name: "Show retired/model in client model lists" });
    expect(listed).not.toBeChecked();
    await user.click(listed);
    await waitFor(() => expect(listed).toBeChecked());

    await user.click(screen.getByRole("button", { name: "Change" }));
    expect(screen.queryByRole("combobox", { name: "Requested model" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("combobox", { name: "Served model" }));
    await user.click(screen.getByRole("option", { name: /^GPT-5\.4/ }));
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Redirects to GPT-5.4")).toBeInTheDocument();
    const card = screen.getByRole("heading", { name: "Model redirects" }).closest("section")!;
    await user.click(within(card).getByRole("button", { name: "Remove" }));
    expect(await screen.findByText("No redirects. Requests are served by the model they name.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Redirects to GPT-5.4")).not.toBeInTheDocument());
  });

  it("shows both inline errors for the approved compaction conflict state", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ModelRedirectSettings />);
    await screen.findByText("No redirects. Requests are served by the model they name.");
    await user.click(screen.getByRole("button", { name: "Add redirect" }));
    const source = screen.getByRole("combobox", { name: "Requested model" });
    expect(source).toHaveFocus();
    await user.click(source);
    await user.type(screen.getByRole("searchbox", { name: "Search or enter a model name…" }), "gpt-6-luna{Enter}");
    expect(source).toHaveTextContent(/luna/i);
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("gpt-6-luna is part of a compaction route. Change that route first.")).toBeVisible();
    expect(screen.getByText("Choose a served model.")).toBeVisible();
    expect(source).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("combobox", { name: "Served model" })).toHaveAttribute("aria-invalid", "true");
  });

  it("shows an inactive reason and disables actions for read-only viewers", async () => {
    server.use(http.get("/api/settings/model-redirects", () => HttpResponse.json({
      redirects: [{
        sourceModel: "retired/model",
        targetModel: "missing",
        status: "inactive",
        reason: "model_redirect_target_unavailable",
      }],
      targets: [],
      imageSources: [],
      disabledModels: [],
    })));
    renderWithProviders(<ModelRedirectSettings disabled />);
    expect(await screen.findByText("Inactive")).toBeInTheDocument();
    expect(screen.getByText("Served model not in catalogue")).toBeInTheDocument();
    for (const name of ["Add redirect", "Change", "Remove"]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
    }
  });

  it("keeps client requests apart, offers disabled models on request and matches image targets", async () => {
    server.use(http.get("/api/settings/model-redirects", () => HttpResponse.json({
      redirects: [],
      targets: [
        { provider: "subscription", models: [{ slug: "gpt-6.1-sol", displayName: "GPT-6.1 Sol", hidden: false, image: false }] },
        {
          provider: "openai_apikey",
          models: [{
            slug: "openai-apikey/gpt-image-2.6-sunburst",
            displayName: "GPT Image 2.6 Sunburst",
            hidden: false,
            image: true,
          }],
        },
      ],
      imageSources: ["gpt-image-2"],
      disabledModels: [{
        provider: "openrouter",
        models: [{ slug: "openrouter/deepseek/deepseek-v4", displayName: "DeepSeek V4", hidden: false, image: false }],
      }],
    })));
    const user = userEvent.setup();
    renderWithProviders(<ModelRedirectSettings />);
    await screen.findByText("No redirects. Requests are served by the model they name.");
    await user.click(screen.getByRole("button", { name: "Add redirect" }));
    const source = screen.getByRole("combobox", { name: "Requested model" });
    const target = screen.getByRole("combobox", { name: "Served model" });

    await user.click(source);
    const client = screen.getByRole("group", { name: "Client requests" });
    expect(within(client).getByRole("option", { name: /gpt-image-2/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Sunburst/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /DeepSeek/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole("switch", { name: "Show disabled models" }));
    const openrouter = screen.getByRole("group", { name: "OpenRouter" });
    expect(within(openrouter).getByRole("option", { name: /DeepSeek V4.*Not enabled/ })).toBeInTheDocument();
    await user.type(screen.getByRole("searchbox", { name: "Search or enter a model name…" }), "deep");
    expect(screen.queryByRole("group", { name: "Client requests" })).not.toBeInTheDocument();
    await user.clear(screen.getByRole("searchbox", { name: "Search or enter a model name…" }));
    await user.click(within(screen.getByRole("group", { name: "Client requests" })).getByRole("option", { name: /gpt-image-2/ }));

    await user.click(target);
    expect(screen.queryByRole("option", { name: /GPT-6\.1 Sol/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole("option", { name: /GPT Image 2\.6 Sunburst/ }));
    expect(target).toHaveTextContent("GPT Image 2.6 Sunburst");

    // Switching to a text model drops the image target.
    await user.click(source);
    await user.click(screen.getByRole("option", { name: /GPT-6\.1 Sol/ }));
    expect(target).toHaveTextContent("Choose a model…");
  });
});
