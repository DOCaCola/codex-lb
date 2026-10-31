import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import App from "@/App";
import { renderWithProviders } from "@/test/utils";

describe("accounts flow integration", () => {
  it("opens an account from the Providers table and pauses or resumes it", async () => {
    const user = userEvent.setup({ delay: null });

    window.history.pushState({}, "", "/providers");
    renderWithProviders(<App />);

    expect(await screen.findByRole("heading", { level: 1, name: "Providers" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "primary@example.com" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "secondary@example.com" })).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "secondary@example.com" }));
    expect(await screen.findByText("Token Status")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/providers/acc_secondary");

    const resumeButton = screen.queryByRole("button", { name: "Resume" });
    if (resumeButton) {
      await user.click(resumeButton);
      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Pause" })).toBeInTheDocument();
      });
    } else {
      await user.click(screen.getByRole("button", { name: "Pause" }));
      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Resume" })).toBeInTheDocument();
      });
    }
  });

  it("lets operators set, find, and clear an account alias", async () => {
    const user = userEvent.setup({ delay: null });

    window.history.pushState({}, "", "/providers/acc_primary");
    renderWithProviders(<App />);

    await user.click(await screen.findByRole("button", { name: "Edit alias" }));
    const aliasInput = await screen.findByLabelText("Account alias");
    await user.clear(aliasInput);
    await user.type(aliasInput, "Personal Plus");
    await user.click(screen.getByRole("button", { name: "Save alias" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Personal Plus" })).toBeInTheDocument();
    });

    const rail = screen.getByRole("navigation", { name: "Accounts" });
    await user.type(within(rail).getByPlaceholderText("Find account"), "personal");
    expect(within(rail).getByRole("link", { name: /Personal Plus/ })).toBeInTheDocument();
    expect(within(rail).queryByText("secondary@example.com")).not.toBeInTheDocument();

    await user.click(await screen.findByRole("button", { name: "Edit alias" }));
    const aliasInputToClear = await screen.findByLabelText("Account alias");
    await user.clear(aliasInputToClear);
    await user.click(screen.getByRole("button", { name: "Save alias" }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "primary@example.com" })).toBeInTheDocument();
    });
  });
});
