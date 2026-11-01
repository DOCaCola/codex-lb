import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderDashboardAccounts } from "@/features/dashboard/test-utils";
import { noticeHeadline, type ProviderNotice } from "@/features/accounts/provider-summary";
import { createOpenRouterAccount } from "@/features/openrouter/test-fixtures";
import { money } from "@/features/openrouter/display-values";
import { createAccountSummary } from "@/test/mocks/factories";

describe("dashboard account card layout", () => {
  it("gives Codex cards with and without a notice the same bottom slots", () => {
    renderDashboardAccounts({
      accounts: [
        createAccountSummary({ accountId: "acc_ok" }),
        createAccountSummary({ accountId: "acc_paused", status: "paused" }),
        createAccountSummary({ accountId: "acc_empty", creditsBalance: 0, remainingCreditsPrimary: null, remainingCreditsSecondary: null }),
      ],
    });
    for (const card of screen.getAllByTestId("dashboard-account-card")) {
      const bottom = within(card).getByTestId("account-card-bottom");
      expect(card.lastElementChild).toBe(bottom);
      expect([...bottom.children].map((child) => child.getAttribute("data-testid"))).toEqual([
        "account-card-footer",
        "account-card-strip-slot",
      ]);
    }
    const [ok, paused, empty] = screen.getAllByTestId("dashboard-account-card");
    expect(within(ok).queryByTestId("account-card-strip")).not.toBeInTheDocument();
    expect(within(paused).getByTestId("account-card-strip")).toBeInTheDocument();
    expect(within(empty).getByTestId("account-card-footer")).toHaveTextContent("0 + 0 credits");
  });

  it("reserves the status-strip slot on cards of every provider", () => {
    renderDashboardAccounts({ openRouterAccounts: [createOpenRouterAccount()] });
    const card = screen.getByTestId("dashboard-account-card");
    expect(within(card).getByTestId("account-card-strip-slot")).toBeEmptyDOMElement();
    expect(within(card).queryByTestId("account-card-footer")).not.toBeInTheDocument();
  });

  it("shows the time left until a notice ends", () => {
    const now = Date.parse("2026-11-01T10:00:00Z");
    const limit: ProviderNotice = { tone: "bad", text: "", label: "Weekly limit · back", until: "2026-11-04T09:00:00Z" };
    const subscription: ProviderNotice = { tone: "warn", text: "", label: "Subscription ends", until: "2026-11-01T17:00:00Z" };
    expect(noticeHeadline(limit, now)).toBe("Weekly limit · back in 2d 23h");
    expect(noticeHeadline(subscription, now)).toBe("Subscription ends in 7h 0m");
    expect(noticeHeadline({ ...limit, label: "Paused", until: null }, now)).toBe("Paused");
  });

  it("keeps the reset-credit button on the credits line when the account is limited", () => {
    const limited = createAccountSummary({
      status: "quota_exceeded",
      availableResetCredits: 2,
      usage: { primaryRemainingPercent: 50, secondaryRemainingPercent: 0, monthlyRemainingPercent: null },
    });
    const cards = renderDashboardAccounts({ accounts: [limited] });
    const card = screen.getByTestId("dashboard-account-card");
    expect(within(within(card).getByTestId("account-card-footer")).getByRole("button", { name: /2 resets/ })).toBeInTheDocument();
    expect(within(within(card).getByTestId("account-card-strip")).queryByRole("button")).not.toBeInTheDocument();
    cards.unmount();

    renderDashboardAccounts({ accounts: [limited] }, { view: "list" });
    expect(within(screen.getByTestId("dashboard-account-row")).getByRole("button", { name: /2 resets/ })).toBeInTheDocument();
  });

  it("gives grid rows the height of the tallest card from two columns on", () => {
    renderDashboardAccounts({ accounts: [createAccountSummary()] });
    const grid = screen.getByTestId("dashboard-account-cards");
    expect(grid).toHaveClass("@min-[38.25rem]/cards:auto-rows-fr");
    expect(grid).not.toHaveClass("auto-rows-fr");
    expect(grid.parentElement).toHaveClass("@container/cards");
  });

  it("formats OpenRouter amounts like every other dashboard amount", () => {
    renderDashboardAccounts({ openRouterAccounts: [createOpenRouterAccount()] });
    expect(within(screen.getByTestId("dashboard-account-card")).getByText("$1.25")).toBeInTheDocument();
    expect(money(5.7394)).toBe("$5.7394");
    expect(money(0)).toBe("$0.00");
  });
});
