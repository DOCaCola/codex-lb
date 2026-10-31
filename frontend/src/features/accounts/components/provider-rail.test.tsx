import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useParams } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { NO_ACCOUNT_COLORS } from "@/features/accounts/account-colors";
import { ProviderRail } from "@/features/accounts/components/provider-rail";
import { useRailCollapsed } from "@/features/accounts/hooks/use-rail-collapsed";
import { buildProviderGroups } from "@/features/accounts/provider-summary";
import { providerSources, summaryContext } from "@/features/accounts/test-utils";
import { createClaudeAccount } from "@/features/claude/test-fixtures";
import { createAccountSummary } from "@/test/mocks/factories";

const groups = buildProviderGroups(
  providerSources({
    accounts: [createAccountSummary()],
    claudeAccounts: [createClaudeAccount({ id: "claude-a", name: "Claude A" }), createClaudeAccount({ id: "claude-b", name: "Claude B" })],
  }),
  "name_asc",
  summaryContext(),
);

function Rail() {
  const { accountId = "" } = useParams();
  const [collapsed, toggle] = useRailCollapsed();
  return <ProviderRail groups={groups} selectedId={accountId} colors={NO_ACCOUNT_COLORS} collapsed={collapsed} onToggleCollapsed={toggle} />;
}

function renderRail(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/providers/:accountId" element={<Rail />} />
        <Route path="/providers/:accountId/settings" element={<Rail />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => localStorage.removeItem("codex-lb.providers.rail-collapsed"));

describe("ProviderRail", () => {
  it("marks the open account and summarises each provider", () => {
    renderRail("/providers/claude-a");
    const rail = screen.getByRole("navigation", { name: "Accounts" });
    expect(within(rail).getByRole("link", { name: /Claude A/ })).toHaveAttribute("aria-current", "page");
    expect(within(rail).getByRole("link", { name: /Claude B/ })).not.toHaveAttribute("aria-current");
    expect(within(rail).getByText("2/2 ready")).toBeInTheDocument();
  });

  it("moves between accounts with the arrow keys", async () => {
    renderRail("/providers/acc_primary");
    within(screen.getByRole("navigation", { name: "Accounts" })).getByRole("link", { name: /primary@example.com/ }).focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("link", { name: /Claude A/ })).toHaveAttribute("aria-current", "page");
    await userEvent.keyboard("{ArrowUp}");
    expect(screen.getByRole("link", { name: /primary@example.com/ })).toHaveAttribute("aria-current", "page");
  });

  it("keeps the open tab when switching accounts", async () => {
    renderRail("/providers/claude-a/settings");
    const rail = screen.getByRole("navigation", { name: "Accounts" });
    expect(within(rail).getByRole("link", { name: /Claude A/ })).toHaveAttribute("aria-current", "page");
    expect(within(rail).getByRole("link", { name: /Claude B/ })).toHaveAttribute("href", "/providers/claude-b/settings");
    within(rail).getByRole("link", { name: /Claude A/ }).focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("link", { name: /Claude B/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /Claude A/ })).toHaveAttribute("href", "/providers/claude-a/settings");
  });

  it("links to the overview from an account overview", () => {
    renderRail("/providers/claude-a");
    expect(screen.getByRole("link", { name: /Claude B/ })).toHaveAttribute("href", "/providers/claude-b");
  });

  it("finds accounts by name", async () => {
    renderRail("/providers/acc_primary");
    await userEvent.type(screen.getByPlaceholderText("Find account"), "claude b");
    expect(screen.getByRole("link", { name: /Claude B/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Claude A/ })).not.toBeInTheDocument();
  });

  it("keeps the collapsed state across visits", async () => {
    const view = renderRail("/providers/acc_primary");
    await userEvent.click(screen.getByRole("button", { name: "Collapse account list" }));
    expect(screen.queryByPlaceholderText("Find account")).not.toBeInTheDocument();
    view.unmount();
    renderRail("/providers/acc_primary");
    expect(screen.getByRole("button", { name: "Expand account list" })).toHaveAttribute("aria-expanded", "false");
  });
});

