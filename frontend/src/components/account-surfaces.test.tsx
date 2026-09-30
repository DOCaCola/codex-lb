import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  AccountCardAction,
  AccountCardNotice,
  AccountCardSurface,
} from "./account-surfaces";

describe("AccountCardSurface", () => {
  it("owns the shared identity, content and action anatomy", async () => {
    const onClick = vi.fn();
    const view = render(
      <AccountCardSurface
        data-testid="card"
        title="Identity"
        subtitle="Provider"
        description="identity@example.com"
        descriptionTitle="Account ID"
        status={<span>Active</span>}
        actions={
          <AccountCardAction onClick={onClick}>Details</AccountCardAction>
        }
      >
        <p>Provider metrics</p>
        <AccountCardNotice>Provider notice</AccountCardNotice>
      </AccountCardSurface>,
    );
    const card = screen.getByTestId("card");
    expect(card).toHaveClass("flex", "flex-col", "h-full", "min-w-0");
    const [header, body, footer] = Array.from(card.children);
    expect(header).toHaveAttribute("data-slot", "account-card-header");
    expect(header).toHaveTextContent(
      "IdentityProvideridentity@example.comActive",
    );
    expect(screen.getByTitle("Account ID")).toHaveTextContent(
      "identity@example.com",
    );
    expect(body).toHaveAttribute("data-slot", "account-card-body");
    expect(body).toHaveClass("flex-1", "space-y-3");
    expect(body).toHaveTextContent("Provider metricsProvider notice");
    expect(footer).toHaveAttribute("data-slot", "account-card-actions");
    await userEvent.click(screen.getByRole("button", { name: "Details" }));
    expect(onClick).toHaveBeenCalledOnce();
    view.rerender(
      <AccountCardSurface
        title="Identity"
        subtitle="Provider"
        status="Active"
        actions={
          <AccountCardAction disabled onClick={onClick}>
            Details
          </AccountCardAction>
        }
      >
        Provider metrics
      </AccountCardSurface>,
    );
    expect(screen.queryByText("identity@example.com")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Details" })).toBeDisabled();
  });
});
