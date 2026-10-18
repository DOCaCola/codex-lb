import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CompactionRouteSettings } from "@/features/settings/components/compaction-route-settings";
import { createCompactionRoutes } from "@/test/mocks/factories";

const useModelCompactionRoutesMock = vi.fn();

vi.mock("@/features/settings/hooks/use-settings", () => ({
  useModelCompactionRoutes: () => useModelCompactionRoutesMock(),
}));

function mockHook(routes = createCompactionRoutes()) {
  const upsert = vi.fn().mockResolvedValue(routes);
  const remove = vi.fn().mockResolvedValue(routes);
  useModelCompactionRoutesMock.mockReturnValue({
    routesQuery: { data: routes, error: null, isLoading: false },
    upsertMutation: { mutateAsync: upsert, isPending: false, error: null },
    deleteMutation: { mutateAsync: remove, isPending: false, error: null },
  });
  return { upsert, remove };
}

function row(slug: string): HTMLElement {
  const element = screen.getAllByText(slug)[0].closest("tr");
  expect(element).not.toBeNull();
  return element as HTMLElement;
}

describe("CompactionRouteSettings", () => {
  beforeEach(() => {
    useModelCompactionRoutesMock.mockReset();
  });

  it("lists routes with their effort and status, explaining inactive ones", () => {
    mockHook(
      createCompactionRoutes({
        routes: [
          { slug: "gpt-6-astra", compactionModel: "gpt-6-luna", reasoningEffort: "low", status: "active", reason: null },
          {
            slug: "gpt-6.1-sol",
            compactionModel: "gpt-6-luna",
            reasoningEffort: null,
            status: "inactive",
            reason: "context_window_too_small",
          },
        ],
      }),
    );
    render(<CompactionRouteSettings />);

    expect(screen.getByText("Compaction routing")).toBeInTheDocument();
    const astra = row("gpt-6-astra");
    expect(within(astra).getByText("GPT-6-Luna")).toBeInTheDocument();
    expect(within(astra).getByText("low")).toBeInTheDocument();
    expect(within(astra).getByText("Active")).toBeInTheDocument();

    const sol = row("gpt-6.1-sol");
    expect(within(sol).getByText("Client's effort")).toBeInTheDocument();
    expect(within(sol).getByText("Inactive")).toBeInTheDocument();
    expect(
      within(sol).getByText("Compaction model's context limit is below the coding model's window"),
    ).toBeInTheDocument();
  });

  it("adds a route for an unrouted model at a chosen effort", async () => {
    const user = userEvent.setup();
    const { upsert } = mockHook();
    render(<CompactionRouteSettings />);

    await user.click(screen.getByRole("button", { name: "Add route" }));
    await user.click(screen.getByRole("combobox", { name: "Coding model" }));
    // Astra already has a route, so only the others are offered.
    expect(screen.queryByRole("option", { name: "GPT-6-Astra" })).not.toBeInTheDocument();
    await user.click(await screen.findByRole("option", { name: "GPT-6.1-Sol" }));
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();

    await user.click(screen.getByRole("combobox", { name: "Compaction model" }));
    await user.click(await screen.findByRole("option", { name: "GPT-6-Luna" }));
    await user.click(screen.getByRole("combobox", { name: "Compaction effort" }));
    // Efforts follow the compaction model: Luna has no ultra.
    expect(screen.queryByRole("option", { name: "ultra" })).not.toBeInTheDocument();
    await user.click(await screen.findByRole("option", { name: "max" }));
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(upsert).toHaveBeenCalledWith({ slug: "gpt-6.1-sol", compactionModel: "gpt-6-luna", reasoningEffort: "max" });
  });

  it("edits a route back to the client's effort and removes routes after confirmation", async () => {
    const user = userEvent.setup();
    const { upsert, remove } = mockHook();
    render(<CompactionRouteSettings />);

    await user.click(within(row("gpt-6-astra")).getByRole("button", { name: "Edit" }));
    await user.click(screen.getByRole("combobox", { name: "Compaction effort" }));
    await user.click(await screen.findByRole("option", { name: "Client's effort" }));
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(upsert).toHaveBeenCalledWith({ slug: "gpt-6-astra", compactionModel: "gpt-6-luna", reasoningEffort: null });

    await user.click(within(row("gpt-6-astra")).getByRole("button", { name: "Remove" }));
    const dialog = await screen.findByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: "Remove" }));
    expect(remove).toHaveBeenCalledWith("gpt-6-astra");
  });

  it("explains that models compact on themselves without routes", () => {
    mockHook(createCompactionRoutes({ routes: [] }));
    render(<CompactionRouteSettings />);

    expect(screen.getByText("No compaction routes. Every model compacts on itself.")).toBeInTheDocument();
  });
});
