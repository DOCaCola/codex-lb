import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "@/test/utils";

import { fromLocalDateTimeInput, toLocalDateTimeInput } from "../account-subscriptions";
import { AccountSubscriptionEndPanel } from "./account-subscription-end-panel";

const ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone;
const INPUT_LABEL = `Subscription end (${ZONE})`;

describe("AccountSubscriptionEndPanel", () => {
  it("sets an end in local time, shows it, and clears it", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AccountSubscriptionEndPanel target={{ accountId: "acc_primary" }} readOnly={false} />);

    expect(await screen.findByText("Not set; the subscription is treated as renewing.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Edit subscription end" }));
    const input = screen.getByLabelText(INPUT_LABEL);
    expect(screen.getByText(`Date and time in your browser's time zone, ${ZONE}.`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    await user.type(input, "2099-11-15T18:00");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText((text) => text.startsWith("Ends ") && text.endsWith(`(${ZONE})`))).toBeInTheDocument();
    expect(screen.getByText(/^in \d+d$/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Edit subscription end" }));
    expect(screen.getByLabelText(INPUT_LABEL)).toHaveValue("2099-11-15T18:00");
    await user.click(screen.getByRole("button", { name: "Clear" }));
    await waitFor(() =>
      expect(screen.getByText("Not set; the subscription is treated as renewing.")).toBeInTheDocument(),
    );
  });

  it("states that a passed end is ignored by projections", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AccountSubscriptionEndPanel target={{ modelSourceId: "src_claude" }} readOnly={false} />);

    await user.click(await screen.findByRole("button", { name: "Edit subscription end" }));
    await user.type(screen.getByLabelText(INPUT_LABEL), "2020-01-02T03:04");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(
      await screen.findByText((text) => text.startsWith("Passed ") && text.endsWith(`(${ZONE}) · ignored in projections`)),
    ).toBeInTheDocument();
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
