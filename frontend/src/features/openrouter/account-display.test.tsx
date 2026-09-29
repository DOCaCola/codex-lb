import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OpenRouterAccountCard, OpenRouterMetrics } from "./account-display";
import { createOpenRouterAccount } from "./test-fixtures";
import { AccountCards } from "@/features/dashboard/components/account-cards";
import { AccountList as DashboardAccountList } from "@/features/dashboard/components/account-list";
import { AccountList } from "@/features/accounts/components/account-list";
import { AccountSummaryLine } from "@/features/dashboard/components/account-summary-line";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { OpenRouterAccountDetail } from "./account-detail";

vi.mock("@/features/accounts/components/provider-account-trends", () => ({
  ProviderAccountTrends: () => <div>Account trends</div>,
}));

afterEach(() => usePrivacyStore.setState({ blurred: false }));

describe("Unified provider accounts", () => {
  it.each([
    [true, "Free"],
    [false, "Paid"],
    [null, "Unknown"],
  ] as const)("displays key tier %s in account cards and lists", (free, label) => {
    const account = createOpenRouterAccount();
    if (free === null) account.state.key = null;
    else account.state.key!.is_free_tier = free;
    render(
      <MemoryRouter>
        <OpenRouterAccountCard account={account} />
        <DashboardAccountList accounts={[]} openRouterAccounts={[account]} />
        <AccountList accounts={[]} openRouterAccounts={[account]} selectedAccountId={null}
          onSelect={vi.fn()} onOpenImport={vi.fn()} onOpenOauth={vi.fn()} />
      </MemoryRouter>,
    );
    expect(screen.getAllByTitle(/API key tier reported/)).toHaveLength(3);
    for (const tier of screen.getAllByTitle(/API key tier reported/)) {
      expect(tier).toHaveTextContent(label);
    }
  });

  it("marks retained tier metadata stale", () => {
    const account = createOpenRouterAccount();
    account.state.key_error = "Refresh failed";
    render(<MemoryRouter><OpenRouterAccountCard account={account} /></MemoryRouter>);
    expect(screen.getByTitle(/API key tier reported/)).toHaveTextContent("Paid· stale");
  });

  it("uses Pause and Resume instead of an enabled switch", async () => {
    const account = createOpenRouterAccount();
    const onToggle = vi.fn();
    const props = {
      readOnly: false,
      busy: false,
      onEdit: vi.fn(),
      onModels: vi.fn(),
      onImageModels: vi.fn(),
      onRefresh: vi.fn(),
      onDelete: vi.fn(),
      onRename: vi.fn(),
      onToggle,
    };
    const view = render(
      <OpenRouterAccountDetail account={account} {...props} />,
    );
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
    expect(screen.getByTitle(/API key tier reported/)).toHaveTextContent("Paid");
    await userEvent.click(
      screen.getByRole("button", { name: "Image models (0)" }),
    );
    expect(props.onImageModels).toHaveBeenCalledOnce();
    await userEvent.click(screen.getByRole("button", { name: "Pause" }));
    expect(onToggle).toHaveBeenLastCalledWith(false);
    view.rerender(
      <OpenRouterAccountDetail
        account={{ ...account, isEnabled: false }}
        {...props}
      />,
    );
    expect(
      screen.queryByRole("button", { name: "Pause" }),
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Resume" }));
    expect(onToggle).toHaveBeenLastCalledWith(true);
    view.rerender(
      <OpenRouterAccountDetail account={account} {...props} busy />,
    );
    expect(screen.getByRole("button", { name: "Pause" })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Image models (0)" }),
    ).toBeDisabled();
    view.rerender(
      <OpenRouterAccountDetail account={account} {...props} readOnly />,
    );
    expect(
      screen.getByRole("button", { name: "Image models (0)" }),
    ).toBeDisabled();
  });
  it("renames inline from the detail heading like Codex accounts", async () => {
    const onRename = vi.fn().mockResolvedValue(undefined);
    render(
      <OpenRouterAccountDetail
        account={createOpenRouterAccount({ name: "Research" })}
        readOnly={false}
        busy={false}
        onEdit={vi.fn()}
        onRename={onRename}
        onModels={vi.fn()}
        onImageModels={vi.fn()}
        onRefresh={vi.fn()}
        onToggle={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Rename account" }));
    const input = screen.getByRole("textbox", { name: "Account name" });
    await userEvent.clear(input);
    expect(screen.getByRole("button", { name: "Save name" })).toBeDisabled();
    await userEvent.type(input, "Team key{Enter}");
    expect(onRename).toHaveBeenCalledWith("Team key");
    expect(screen.queryByRole("textbox", { name: "Account name" })).not.toBeInTheDocument();
  });

  it("sorts provider balances numerically in dashboard list view", async () => {
    const low = createOpenRouterAccount({ id: "low", name: "Zulu" });
    const high = createOpenRouterAccount({ id: "high", name: "Alpha" });
    low.state.credits = { total_credits: 5, total_usage: 1 };
    render(
      <MemoryRouter>
        <DashboardAccountList accounts={[]} openRouterAccounts={[high, low]} />
      </MemoryRouter>,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Credits / USD" }),
    );
    expect(screen.getAllByTestId("account-list-row")[0]).toHaveTextContent(
      "Zulu",
    );
  });

  it("includes OpenRouter in common status filtering", async () => {
    render(
      <AccountList
        accounts={[]}
        openRouterAccounts={[
          createOpenRouterAccount(),
          createOpenRouterAccount({
            id: "paused",
            name: "Paused provider",
            isEnabled: false,
          }),
        ]}
        selectedAccountId={null}
        onSelect={vi.fn()}
        onOpenImport={vi.fn()}
        onOpenOauth={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("combobox", { name: /status/i }));
    await userEvent.click(screen.getByRole("option", { name: "Paused" }));
    expect(screen.queryByText("Research")).not.toBeInTheDocument();
    expect(screen.getByText("Paused provider")).toBeVisible();
  });

  it("renders an OpenRouter-only dashboard in both views with detail links", () => {
    const account = createOpenRouterAccount();
    render(
      <MemoryRouter>
        <AccountCards accounts={[]} openRouterAccounts={[account]} />
        <DashboardAccountList accounts={[]} openRouterAccounts={[account]} />
        <AccountSummaryLine accounts={[]} openRouterAccounts={[account]} />
      </MemoryRouter>,
    );
    expect(
      within(screen.getByTestId("dashboard-account-cards")).getByText(
        "Research",
      ),
    ).toBeVisible();
    expect(
      within(screen.getByTestId("dashboard-account-list")).getByText(
        "Research",
      ),
    ).toBeVisible();
    expect(
      screen
        .getAllByRole("link")
        .every(
          (link) =>
            link.getAttribute("href") === "/accounts?selected=src_research",
        ),
    ).toBe(true);
    expect(
      screen.getByTestId("dashboard-account-summary-line"),
    ).toHaveTextContent("1");
  });

  it("honors privacy mode", () => {
    usePrivacyStore.setState({ blurred: true });
    render(
      <MemoryRouter>
        <OpenRouterAccountCard account={createOpenRouterAccount()} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Research")).toHaveClass("privacy-blur");
  });

  it("keeps unavailable monitoring distinct from zero and uncapped", () => {
    const account = createOpenRouterAccount();
    account.state.key = null;
    account.state.credits = null;
    render(<OpenRouterMetrics account={account} detailed />);
    expect(screen.getAllByText("Unknown")).toHaveLength(4);
    expect(screen.queryByText("No key cap")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("openrouter-key-allowance"),
    ).not.toBeInTheDocument();
  });

  it("marks all retained key metrics as stale", () => {
    const account = createOpenRouterAccount();
    account.state.key_error = "Refresh failed";
    account.state.credits_error = "Refresh failed";
    render(<OpenRouterMetrics account={account} detailed />);
    expect(screen.getAllByText("· stale")).toHaveLength(4);
    expect(screen.getByText("$75.50")).toBeVisible();
  });

  it("uses common search and name ordering across providers", async () => {
    const select = vi.fn();
    render(
      <AccountList
        accounts={[
          {
            accountId: "codex",
            email: "z@example.com",
            displayName: "Zulu",
            status: "active",
            planType: "pro",
            additionalQuotas: [],
            limitWarmupEnabled: false,
          },
        ]}
        openRouterAccounts={[createOpenRouterAccount({ name: "Alpha" })]}
        sortMode="name_asc"
        selectedAccountId="src_research"
        onSelect={select}
        onOpenImport={vi.fn()}
        onOpenOauth={vi.fn()}
      />,
    );
    const list = screen.getByTestId("account-list-scroll-region");
    expect(within(list).getAllByRole("button")[0]).toHaveTextContent("Alpha");
    await userEvent.type(screen.getByRole("textbox"), "openrouter");
    expect(within(list).queryByText("Zulu")).not.toBeInTheDocument();
    await userEvent.click(within(list).getByRole("button"));
    expect(select).toHaveBeenCalledWith("src_research");
  });
});
