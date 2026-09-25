import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AccountCards } from "@/features/dashboard/components/account-cards";
import { AccountList as DashboardList } from "@/features/dashboard/components/account-list";
import { AccountList } from "@/features/accounts/components/account-list";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { ClaudeQuota } from "./account-display";
import { claudeStatus } from "./display-values";
import type { ClaudeAccount } from "./api";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { ClaudeAccountControls } from "./account-controls";

const account: ClaudeAccount = {
  id: "claude-test",
  name: "Private Claude",
  isEnabled: true,
  credentialStatus: "ready",
  expiresAt: "2026-09-25T20:00:00Z",
  state: {
    selections: [],
    catalog: [],
    catalog_updated_at: null,
    catalog_error: null,
    usage_updated_at: null,
    usage_error: null,
  },
  quota: {
    observedAt: null,
    models: [],
    windows: [
      {
        name: "five_hour",
        utilization: null,
        resetsAt: null,
        freshness: "unknown",
        exhausted: false,
      },
      {
        name: "seven_day",
        utilization: 40,
        resetsAt: null,
        freshness: "stale",
        exhausted: false,
      },
    ],
  },
};
afterEach(() => usePrivacyStore.setState({ blurred: false }));
describe("Claude shared account surfaces", () => {
  it("requires explicit refresh ownership consent before enrollment", async () => {
    const client = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={client}>
        <ClaudeAccountControls
          account={null}
          readOnly={false}
          onCreated={vi.fn()}
        >
          {({ onAdd }) => <button onClick={onAdd}>Add Claude</button>}
        </ClaudeAccountControls>
      </QueryClientProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Add Claude" }));
    await userEvent.type(screen.getByLabelText("Account name"), "Research");
    expect(
      screen.getByRole("button", { name: "Sign in with Claude" }),
    ).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox"));
    expect(
      screen.getByRole("button", { name: "Sign in with Claude" }),
    ).toBeEnabled();
  });
  it("pauses through the account API and blocks mutations for read-only users", async () => {
    const changes: unknown[] = [];
    server.use(
      http.get("/api/claude-accounts/version", () =>
        HttpResponse.json({
          effectiveVersion: "2.1.282",
          discoveredVersion: "2.1.282",
          pinnedVersion: null,
          lastCheckedAt: null,
          lastChangedAt: null,
          error: null,
        }),
      ),
      http.patch("/api/claude-accounts/claude-test", async ({ request }) => {
        changes.push(await request.json());
        return HttpResponse.json({ ...account, isEnabled: false });
      }),
    );
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const view = render(
      <QueryClientProvider client={client}>
        <ClaudeAccountControls
          account={account}
          readOnly={false}
          onCreated={vi.fn()}
        >
          {({ detail }) => detail}
        </ClaudeAccountControls>
      </QueryClientProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Pause" }));
    expect(changes).toEqual([{ isEnabled: false }]);
    view.rerender(
      <QueryClientProvider client={client}>
        <ClaudeAccountControls account={account} readOnly onCreated={vi.fn()}>
          {({ detail }) => detail}
        </ClaudeAccountControls>
      </QueryClientProvider>,
    );
    for (const name of [
      "Pause",
      "Reconnect",
      "Refresh",
      "Save models",
      "Delete Claude account",
    ])
      expect(screen.getByRole("button", { name })).toBeDisabled();
  });
  it("distinguishes unknown and stale observations", () => {
    render(<ClaudeQuota account={account} />);
    expect(screen.getByText("Unknown")).toBeInTheDocument();
    expect(screen.getByText("40% used · stale")).toBeInTheDocument();
    expect(
      screen.queryByTestId("claude-quota-five_hour"),
    ).not.toBeInTheDocument();
  });
  it.each([AccountCards, DashboardList])(
    "includes provider-only accounts in dashboard layouts",
    (Component) => {
      render(
        <MemoryRouter>
          <Component accounts={[]} claudeAccounts={[account]} />
        </MemoryRouter>,
      );
      expect(screen.getByText(account.name)).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Details" })).toHaveAttribute(
        "href",
        "/accounts?selected=claude-test",
      );
    },
  );
  it("uses shared privacy and read-only controls", () => {
    usePrivacyStore.setState({ blurred: true });
    render(
      <AccountList
        accounts={[]}
        claudeAccounts={[account]}
        selectedAccountId={account.id}
        onSelect={vi.fn()}
        onOpenImport={vi.fn()}
        onOpenOauth={vi.fn()}
        onClaude={vi.fn()}
        readOnly
      />,
    );
    expect(screen.getByText(account.name)).toHaveClass("privacy-blur");
    expect(screen.getByRole("button", { name: /Add account/i })).toBeDisabled();
  });
  it("does not label exhausted or uncertain credentials active", () => {
    expect(claudeStatus({ ...account, credentialStatus: "uncertain" })).toBe(
      "reauth_required",
    );
    expect(claudeStatus({ ...account, isEnabled: false })).toBe("paused");
    expect(
      claudeStatus({
        ...account,
        quota: {
          ...account.quota,
          models: [{ model: "test", blocked: true, retryAt: null }],
        },
      }),
    ).toBe("quota_exceeded");
  });
});
