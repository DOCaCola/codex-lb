import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderProvidersList } from "@/features/accounts/test-utils";
import { createClaudeAccount } from "@/features/claude/test-fixtures";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { createAccountSummary } from "@/test/mocks/factories";

afterEach(() => usePrivacyStore.setState({ blurred: false }));

const primary = createAccountSummary();
const secondary = createAccountSummary({
  accountId: "acc_secondary",
  email: "secondary@example.com",
  displayName: "secondary@example.com",
  status: "paused",
});

describe("ProvidersList", () => {
  it("links each account row to its page", () => {
    renderProvidersList({ accounts: [primary] });
    expect(screen.getByRole("link", { name: "primary@example.com" })).toHaveAttribute("href", "/providers/acc_primary");
  });

  it("filters by the segmented status control with counts", async () => {
    renderProvidersList({ accounts: [primary, secondary] });
    expect(screen.getByRole("button", { name: /^All\s*2$/ })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: /^Paused\s*1$/ }));
    expect(screen.queryByText("primary@example.com")).not.toBeInTheDocument();
    expect(screen.getByText("secondary@example.com")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^Needs attention\s*0$/ }));
    expect(screen.getByText("No matching accounts")).toBeInTheDocument();
  });

  it("searches across providers", async () => {
    renderProvidersList({ accounts: [primary], claudeAccounts: [createClaudeAccount({ name: "Team Claude" })] });
    await userEvent.type(screen.getByPlaceholderText("Search accounts..."), "team");
    expect(screen.getByText("Team Claude")).toBeInTheDocument();
    expect(screen.queryByText("primary@example.com")).not.toBeInTheDocument();
    expect(screen.getAllByRole("rowgroup").map((group) => group.getAttribute("aria-label"))).toEqual(["Claude"]);
  });

  it("changes the sort mode", async () => {
    const onSortModeChange = vi.fn();
    renderProvidersList({ accounts: [primary] }, { onSortModeChange });
    await userEvent.click(screen.getByRole("combobox", { name: "Sort accounts" }));
    await userEvent.click(await screen.findByRole("option", { name: "Name (A-Z)" }));
    expect(onSortModeChange).toHaveBeenCalledWith("name_asc");
  });

  it("caps the reset credit badge and hides it when settings disable it", () => {
    const account = createAccountSummary({ availableResetCredits: 120 });
    const view = renderProvidersList({ accounts: [account] });
    expect(screen.getByText("99+")).toHaveAttribute("title", "Reset (120)");
    view.unmount();
    renderProvidersList({ accounts: [account] }, { showResetCreditBadges: false });
    expect(screen.queryByText("99+")).not.toBeInTheDocument();
  });

  it("tells duplicate e-mail accounts apart by their ID", () => {
    renderProvidersList({ accounts: [createAccountSummary({ alias: "Work", isEmailDuplicate: true, accountId: "acc_0123456789abcdef" })] });
    expect(within(screen.getByTestId("provider-account-row")).getByText(/· ID /)).toBeInTheDocument();
  });

  it("explains active Codex eligibility and blurs names in privacy mode", () => {
    usePrivacyStore.setState({ blurred: true });
    renderProvidersList({ accounts: [primary] });
    expect(screen.getByText("primary@example.com")).toHaveClass("privacy-blur");
    expect(screen.getByText(/can still skip an Active account/)).toBeInTheDocument();
  });

  it("offers adding providers that are not connected yet", async () => {
    const onAdd = vi.fn();
    const view = renderProvidersList({ accounts: [primary] }, { onAdd });
    await userEvent.click(screen.getByRole("button", { name: /^OpenRouter$/ }));
    await userEvent.click(screen.getByRole("button", { name: "Add Codex account" }));
    expect(onAdd).toHaveBeenCalledTimes(2);
    view.unmount();
    renderProvidersList({ accounts: [primary] }, { readOnly: true });
    expect(screen.queryByText("Not connected yet:")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add Codex account" })).not.toBeInTheDocument();
  });

  it("shows an empty state without accounts", () => {
    renderProvidersList({});
    expect(screen.getByText("No accounts yet")).toBeInTheDocument();
  });
});
