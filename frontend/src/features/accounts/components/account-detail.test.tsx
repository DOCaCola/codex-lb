import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AccountDetail, type AccountDetailProps } from "@/features/accounts/components/account-detail";
import { useAuthStore } from "@/features/auth/hooks/use-auth";
import type { AccountSummary } from "@/features/accounts/schemas";
import { ADMIN_PERMISSIONS, OPERATOR_PERMISSIONS, createAccountSummary, createUpstreamProxyAdmin } from "@/test/mocks/factories";
import { renderWithProviders } from "@/test/utils";

function renderDetail(account: AccountSummary, props: Partial<AccountDetailProps> = {}) {
  const handlers = {
    onPause: vi.fn(),
    onResume: vi.fn(),
    onProbe: vi.fn(),
    onResetUsage: vi.fn(),
    onSetAlias: vi.fn().mockResolvedValue(undefined),
    onDelete: vi.fn(),
    onReauth: vi.fn(),
    onExportAuth: vi.fn(),
    onResetCredit: vi.fn(),
    onLimitWarmupChange: vi.fn(),
    onRoutingPolicyChange: vi.fn(),
    onCreditPolicyChange: vi.fn(),
    onSecurityWorkAuthorizedChange: vi.fn(),
    ...props,
  };
  renderWithProviders(<AccountDetail account={account} busy={false} {...handlers} />);
  return handlers;
}

async function openSettings() {
  await userEvent.click(screen.getByRole("button", { name: "Settings" }));
}

afterEach(() => useAuthStore.setState({ permissions: ADMIN_PERMISSIONS }));

describe("AccountDetail", () => {
  it("keeps usage on the Overview tab and account options on the Settings tab", async () => {
    renderDetail(createAccountSummary());

    expect(screen.getByRole("button", { name: "Overview" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("region", { name: "Usage" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Token Status" })).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Routing policy" })).not.toBeInTheDocument();

    await openSettings();
    expect(window.location.pathname).toMatch(/\/settings$/);
    expect(screen.getByRole("button", { name: "Settings" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("combobox", { name: "Routing policy" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Usage" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Overview" }));
    expect(window.location.pathname).not.toMatch(/\/settings$/);
    expect(screen.getByRole("region", { name: "Usage" })).toBeInTheDocument();
  });

  it("lets operators change account routing policy", async () => {
    const user = userEvent.setup();
    const account = createAccountSummary({ routingPolicy: "normal" });
    const { onRoutingPolicyChange } = renderDetail(account);
    await openSettings();

    expect(screen.getByRole("combobox", { name: "Routing policy" })).toHaveTextContent("Normal");
    await user.click(screen.getByRole("combobox", { name: "Routing policy" }));
    await user.click(await screen.findByRole("option", { name: "Preserve" }));
    expect(onRoutingPolicyChange).toHaveBeenCalledWith(account.accountId, "preserve");
  });

  it("lets operators forbid spending credits after quota exhaustion", async () => {
    const user = userEvent.setup();
    const account = createAccountSummary({ creditPolicy: "spend" });
    const { onCreditPolicyChange } = renderDetail(account);
    await openSettings();

    expect(screen.getByRole("combobox", { name: "Credits" })).toHaveTextContent("Spend credits");
    await user.click(screen.getByRole("combobox", { name: "Credits" }));
    await user.click(await screen.findByRole("option", { name: "Never spend credits" }));
    expect(onCreditPolicyChange).toHaveBeenCalledWith(account.accountId, "never");
  });

  it("shows window warm-up as a setting with its latest attempt", async () => {
    const attemptedAt = new Date("2026-06-03T12:00:00Z").toISOString();
    const account = createAccountSummary({
      displayName: "Warm Account",
      limitWarmupEnabled: false,
      limitWarmup: {
        window: "primary_idle",
        resetAt: 18_000,
        status: "succeeded",
        model: "gpt-5.1-codex-mini",
        attemptedAt,
        completedAt: attemptedAt,
        errorCode: null,
        errorMessage: null,
      },
    });
    const { onLimitWarmupChange } = renderDetail(account);
    await openSettings();

    const toggle = screen.getByRole("switch", { name: "Window warm-up for Warm Account" });
    expect(toggle).toHaveAccessibleDescription(expect.stringContaining("Succeeded | 5h | Gpt-5.1-codex-mini"));
    await userEvent.click(toggle);
    expect(onLimitWarmupChange).toHaveBeenCalledWith(account.accountId, true);
  });

  it.each([
    [false, true],
    [true, false],
    [undefined, false],
  ])("with global warm-up %s shows the disabled-globally hint: %s", async (globallyEnabled, hinted) => {
    renderDetail(createAccountSummary({ limitWarmupEnabled: true }), { limitWarmupGloballyEnabled: globallyEnabled });
    await openSettings();
    expect(screen.queryByText(/Disabled globally/) !== null).toBe(hinted);
    if (hinted) expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("href", "/settings");
  });

  it("reports no warm-up attempts and disables every control for read-only users", async () => {
    const account = createAccountSummary({ accountId: "acc_primary", alias: "Personal", displayName: "Cold Account", limitWarmup: null });
    renderDetail(account, {
      readOnly: true,
      onProxyBindingSave: vi.fn().mockResolvedValue(undefined),
      upstreamProxyAdmin: createUpstreamProxyAdmin({
        bindings: [{ accountId: "acc_primary", poolId: "pool_primary", isActive: true }],
      }),
      resetCredits: { availableCount: 1 },
    });

    for (const name of ["Edit alias", "Reset usage", "Pause", "Force probe", "Re-authenticate"])
      expect(screen.getByRole("button", { name })).toBeDisabled();
    await openSettings();
    const toggle = screen.getByRole("switch", { name: "Window warm-up for Personal" });
    expect(toggle).toHaveAccessibleDescription("No attempts");
    expect(toggle).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save binding" })).toBeDisabled();
    expect(screen.getByRole("combobox", { name: "Routing policy" })).toBeDisabled();
    expect(screen.getByRole("switch", { name: "Enable account proxy binding" })).toBeDisabled();
    expect(screen.getByRole("combobox", { name: "Account proxy pool" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "More actions" }));
    expect(await screen.findByRole("menuitem", { name: "Delete account" })).toHaveAttribute("aria-disabled", "true");
  });

  it("asks a re-auth required account to sign in again without offering resume", async () => {
    const account = createAccountSummary({ status: "reauth_required" });
    const { onReauth } = renderDetail(account);
    await openSettings();

    expect(screen.getByText("Routing skips this account until it is re-authenticated.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
    // The reactivate endpoint refuses this status, so a resume control would only produce a conflict.
    expect(screen.queryByRole("button", { name: "Resume" })).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Routing policy" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Re-authenticate" }));
    expect(onReauth).toHaveBeenCalledOnce();
  });

  it("resumes a deactivated account alongside re-authentication", async () => {
    const account = createAccountSummary({ accountId: "acc_deactivated", status: "deactivated" });
    const { onResume } = renderDetail(account);

    expect(screen.getByRole("button", { name: "Re-authenticate" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Resume" }));
    expect(onResume).toHaveBeenCalledWith("acc_deactivated");
  });

  it("probes active accounts immediately", async () => {
    const account = createAccountSummary();
    const { onProbe } = renderDetail(account);
    await userEvent.click(screen.getByRole("button", { name: "Force probe" }));
    expect(onProbe).toHaveBeenCalledExactlyOnceWith(account.accountId);
  });

  it.each(["paused", "deactivated"] as const)("disables force probe for %s accounts", (status) => {
    renderDetail(createAccountSummary({ status }));
    expect(screen.getByRole("button", { name: "Force probe" })).toBeDisabled();
  });

  it("offers a reset credit with its nearest expiry", async () => {
    const account = createAccountSummary({
      availableResetCredits: 3,
      resetCreditNearestExpiresAt: new Date(Date.now() + 2 * 3_600_000 + 60_000).toISOString(),
    });
    const { onResetCredit } = renderDetail(account);
    await userEvent.click(screen.getByRole("button", { name: "Reset (3)" }));
    expect(onResetCredit).toHaveBeenCalledWith(account.accountId);
    expect(screen.getByText("2h")).toBeInTheDocument();
  });

  it("hides the reset credit expiry when settings disable it", () => {
    renderDetail(
      createAccountSummary({
        availableResetCredits: 3,
        resetCreditNearestExpiresAt: new Date(Date.now() + 2 * 3_600_000 + 60_000).toISOString(),
      }),
      { showResetCreditExpiryBadge: false },
    );
    expect(screen.getByRole("button", { name: "Reset (3)" })).toBeInTheDocument();
    expect(screen.queryByText("2h")).not.toBeInTheDocument();
  });

  it.each(["paused", "deactivated", "reauth_required"] as const)("disables reset credits for %s accounts", (status) => {
    renderDetail(createAccountSummary({ status, availableResetCredits: 2 }));
    expect(screen.getByRole("button", { name: "Reset (2)" })).toBeDisabled();
  });

  it("hides the reset credit action when none are available", () => {
    renderDetail(createAccountSummary({ availableResetCredits: 0 }));
    expect(screen.queryByRole("button", { name: /Reset \(/ })).not.toBeInTheDocument();
  });

  it("disables usage reset for paused accounts", () => {
    renderDetail(createAccountSummary({ status: "paused" }), { resetCredits: { availableCount: 2 } });
    expect(screen.getByRole("button", { name: "Reset usage" })).toBeDisabled();
  });

  it.each([
    ["offers", ADMIN_PERMISSIONS, true],
    ["hides", OPERATOR_PERMISSIONS, false],
  ])("%s credential export according to accounts:export", async (_label, permissions, visible) => {
    useAuthStore.setState({ permissions });
    const account = createAccountSummary();
    const { onExportAuth } = renderDetail(account);
    await userEvent.click(screen.getByRole("button", { name: "More actions" }));
    await screen.findByRole("menuitem", { name: "Copy ID" });
    const item = screen.queryByRole("menuitem", { name: "Export credentials" });
    expect(item !== null).toBe(visible);
    if (item) {
      await userEvent.click(item);
      expect(onExportAuth).toHaveBeenCalledWith(account.accountId);
    }
  });

  it("always shows the account ID in the header", () => {
    const account = createAccountSummary({ accountId: "acc_0123456789abcdef" });
    renderDetail(account);
    expect(screen.getByTitle(/acc_0123456789abcdef/)).toHaveTextContent(/^ID /);
  });
});
