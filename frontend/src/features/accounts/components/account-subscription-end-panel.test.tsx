import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "@/test/utils";

import { fromLocalDateTimeInput, toLocalDateTimeInput } from "../account-subscriptions";
import { AccountSubscriptionEndPanel } from "./account-subscription-end-panel";

describe("AccountSubscriptionEndPanel", () => {
  it("sets an end in local time, shows it, and clears it", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AccountSubscriptionEndPanel target={{ accountId: "acc_primary" }} readOnly={false} />);

    expect(await screen.findByText("Not set; the subscription is treated as renewing.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Edit subscription end" }));
    const input = screen.getByLabelText("Subscription end (local time)");
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    await user.type(input, "2099-11-15T18:00");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText(/^Ends /)).toBeInTheDocument();
    expect(screen.getByText(/^in \d+d$/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Edit subscription end" }));
    expect(screen.getByLabelText("Subscription end (local time)")).toHaveValue("2099-11-15T18:00");
    await user.click(screen.getByRole("button", { name: "Clear" }));
    await waitFor(() =>
      expect(screen.getByText("Not set; the subscription is treated as renewing.")).toBeInTheDocument(),
    );
  });

  it("states that a past end has ended", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AccountSubscriptionEndPanel target={{ modelSourceId: "src_claude" }} readOnly={false} />);

    await user.click(await screen.findByRole("button", { name: "Edit subscription end" }));
    await user.type(screen.getByLabelText("Subscription end (local time)"), "2020-01-02T03:04");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText(/^Ended /)).toBeInTheDocument();
  });

  it("hides the edit control from read-only users", async () => {
    renderWithProviders(<AccountSubscriptionEndPanel target={{ accountId: "acc_primary" }} readOnly />);

    expect(await screen.findByText("Not set; the subscription is treated as renewing.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit subscription end" })).not.toBeInTheDocument();
  });

  it("round-trips local input values through UTC", () => {
    expect(toLocalDateTimeInput(fromLocalDateTimeInput("2026-11-15T18:00"))).toBe("2026-11-15T18:00");
  });
});
