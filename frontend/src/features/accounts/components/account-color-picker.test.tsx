import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "@/test/utils";

import { AccountColorPicker } from "./account-color-picker";

describe("AccountColorPicker", () => {
  it("picks a colour from the popover and returns to automatic assignment", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AccountColorPicker target={{ accountId: "acc_primary" }} disabled={false} />);

    const trigger = await screen.findByRole("button", { name: "Chart color" });
    await user.click(trigger);
    expect(screen.getByRole("button", { name: /^Automatic · currently Blue$/ })).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "Dark amber" }));
    expect(screen.queryByRole("button", { name: "Dark amber" })).not.toBeInTheDocument();

    await user.click(trigger);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Dark amber" })).toHaveAttribute("aria-pressed", "true"),
    );

    await user.click(screen.getByRole("button", { name: /^Automatic/ }));
    await user.click(trigger);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /^Automatic · currently Blue$/ })).toHaveAttribute(
        "aria-pressed",
        "true",
      ),
    );
  });

  it("marks only colours chosen for other accounts, not automatic ones", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <>
        <AccountColorPicker target={{ accountId: "acc_primary" }} disabled={false} />
        <AccountColorPicker target={{ accountId: "acc_secondary" }} disabled={false} />
      </>,
    );
    const [primary, secondary] = await screen.findAllByRole("button", { name: "Chart color" });

    await user.click(primary);
    expect(screen.getByRole("button", { name: "Violet" })).not.toHaveAttribute("data-in-use");
    await user.keyboard("{Escape}");

    await user.click(secondary);
    await user.click(screen.getByRole("button", { name: "Dark amber" }));

    await user.click(primary);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Dark amber" })).toHaveAttribute("data-in-use", "true"),
    );
    expect(screen.getByRole("button", { name: "Violet" })).not.toHaveAttribute("data-in-use");
  });
});
