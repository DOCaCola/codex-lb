import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "@/test/utils";

import { AccountNotePanel } from "./account-note-panel";

describe("AccountNotePanel", () => {
  it("saves a multi-line note and clears it when saved blank", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AccountNotePanel target={{ accountId: "acc_primary" }} readOnly={false} />);

    expect(await screen.findByText("No note.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Edit note" }));
    await user.type(screen.getByRole("textbox", { name: "Account note" }), "Reserved for CI{Enter}Renew in May");
    await user.click(screen.getByRole("button", { name: "Save" }));

    const note = await screen.findByText(/Reserved for CI/);
    expect(note).toHaveTextContent("Reserved for CI Renew in May");
    expect(note.textContent).toBe("Reserved for CI\nRenew in May");

    await user.click(screen.getByRole("button", { name: "Edit note" }));
    await user.clear(screen.getByRole("textbox", { name: "Account note" }));
    await user.type(screen.getByRole("textbox", { name: "Account note" }), "   ");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(screen.getByText("No note.")).toBeInTheDocument());
  });

  it("cancels an edit without saving", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AccountNotePanel target={{ modelSourceId: "src_claude" }} readOnly={false} />);

    await user.click(await screen.findByRole("button", { name: "Edit note" }));
    await user.type(screen.getByRole("textbox", { name: "Account note" }), "Draft");
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.getByText("No note.")).toBeInTheDocument();
  });

  it("shows the note without an edit control to read-only users", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AccountNotePanel target={{ accountId: "acc_primary" }} readOnly={false} />);
    await user.click(await screen.findByRole("button", { name: "Edit note" }));
    await user.type(screen.getByRole("textbox", { name: "Account note" }), "Shared with ops");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText("Shared with ops");

    renderWithProviders(<AccountNotePanel target={{ accountId: "acc_primary" }} readOnly />);

    await waitFor(() => expect(screen.getAllByText("Shared with ops")).toHaveLength(2));
    expect(screen.getAllByRole("button", { name: "Edit note" })).toHaveLength(1);
  });
});
