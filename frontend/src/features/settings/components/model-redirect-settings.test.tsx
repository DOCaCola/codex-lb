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
    expect(within(target).getByRole("group", { name: "OpenAI" })).toBeInTheDocument();
    expect(within(target).getByRole("option", { name: /GPT-5.5.*hidden/ })).toBeInTheDocument();
    await user.type(source, "retired/model");
    await user.selectOptions(target, "gpt-5.5");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Active")).toBeInTheDocument();
    const sourceRow = (await screen.findByText("Redirects to GPT-5.5")).closest("tr")!;
    expect(within(sourceRow).getByText("Not in registry")).toBeInTheDocument();
    expect(within(sourceRow).getByText("400,000 · Served model")).toBeInTheDocument();
    expect(within(sourceRow).getByRole("button", { name: "Override" })).toBeDisabled();
    const listed = within(sourceRow).getByRole("switch", { name: "Show retired/model in client model lists" });
    expect(listed).not.toBeChecked();
    await user.click(listed);
    await waitFor(() => expect(listed).toBeChecked());

    await user.click(screen.getByRole("button", { name: "Change" }));
    expect(screen.queryByRole("combobox", { name: "Requested model" })).not.toBeInTheDocument();
    await user.selectOptions(screen.getByRole("combobox", { name: "Served model" }), "gpt-5.4");
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
    await user.type(source, "gpt-6-luna");
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
    })));
    renderWithProviders(<ModelRedirectSettings disabled />);
    expect(await screen.findByText("Inactive")).toBeInTheDocument();
    expect(screen.getByText("Served model not in catalogue")).toBeInTheDocument();
    for (const name of ["Add redirect", "Change", "Remove"]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
    }
  });
});
