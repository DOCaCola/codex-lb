import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AccountActions } from "@/features/accounts/components/account-actions";
import { useAuthStore } from "@/features/auth/hooks/use-auth";
import { ADMIN_PERMISSIONS, OPERATOR_PERMISSIONS, createAccountSummary } from "@/test/mocks/factories";

describe("AccountActions", () => {
  it.each([
    ["shows", ADMIN_PERMISSIONS, true],
    ["hides", OPERATOR_PERMISSIONS, false],
  ])("%s the Export action according to accounts:export", (_label, permissions, visible) => {
    useAuthStore.setState({ permissions });

    render(
      <AccountActions
        account={createAccountSummary()}
        busy={false}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onProbe={vi.fn()}
        onDelete={vi.fn()}
        onReauth={vi.fn()}
        onExportAuth={vi.fn()}
        onResetCredit={vi.fn()}
        onSecurityWorkAuthorizedChange={vi.fn()}
        onLimitWarmupChange={vi.fn()}
        onRoutingPolicyChange={vi.fn()}
        onCreditPolicyChange={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: /Export/ }) !== null).toBe(visible);
    useAuthStore.setState({ permissions: [] });
  });

  it("shows window warm-up as a setting with its latest attempt", async () => {
    const onLimitWarmupChange = vi.fn();
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

    render(
      <AccountActions
        account={account}
        busy={false}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onProbe={vi.fn()}
        onDelete={vi.fn()}
        onReauth={vi.fn()}
        onExportAuth={vi.fn()}
        onResetCredit={vi.fn()}
        onSecurityWorkAuthorizedChange={vi.fn()}
        onLimitWarmupChange={onLimitWarmupChange}
        onRoutingPolicyChange={vi.fn()}
        onCreditPolicyChange={vi.fn()}
      />,
    );

    const toggle = screen.getByRole("switch", { name: "Window warm-up for Warm Account" });
    expect(toggle).toHaveAccessibleDescription(expect.stringContaining("Succeeded | 5h | Gpt-5.1-codex-mini"));
    expect(screen.queryByRole("button", { name: /Warmup/ })).not.toBeInTheDocument();
    await userEvent.click(toggle);
    expect(onLimitWarmupChange).toHaveBeenCalledWith(account.accountId, true);
  });

  it.each([
    [false, true],
    [true, false],
    [undefined, false],
  ])("with global warm-up %s shows the disabled-globally hint: %s", (globallyEnabled, hinted) => {
    render(
      <MemoryRouter>
        <AccountActions
          account={createAccountSummary({ limitWarmupEnabled: true })}
          busy={false}
          limitWarmupGloballyEnabled={globallyEnabled}
          onPause={vi.fn()}
          onResume={vi.fn()}
          onProbe={vi.fn()}
          onDelete={vi.fn()}
          onReauth={vi.fn()}
          onExportAuth={vi.fn()}
          onResetCredit={vi.fn()}
          onSecurityWorkAuthorizedChange={vi.fn()}
          onLimitWarmupChange={vi.fn()}
          onRoutingPolicyChange={vi.fn()}
          onCreditPolicyChange={vi.fn()}
        />
      </MemoryRouter>,
    );

    expect(screen.queryByText(/Disabled globally/) !== null).toBe(hinted);
    if (hinted) {
      expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("href", "/settings");
    }
  });

  it("reports no warm-up attempts and disables the switch for read-only users", () => {
    render(
      <AccountActions
        account={createAccountSummary({ displayName: "Cold Account", limitWarmup: null })}
        busy={false}
        readOnly
        onPause={vi.fn()}
        onResume={vi.fn()}
        onProbe={vi.fn()}
        onDelete={vi.fn()}
        onReauth={vi.fn()}
        onExportAuth={vi.fn()}
        onResetCredit={vi.fn()}
        onSecurityWorkAuthorizedChange={vi.fn()}
        onLimitWarmupChange={vi.fn()}
        onRoutingPolicyChange={vi.fn()}
        onCreditPolicyChange={vi.fn()}
      />,
    );

    const toggle = screen.getByRole("switch", { name: "Window warm-up for Cold Account" });
    expect(toggle).toHaveAccessibleDescription("No attempts");
    expect(toggle).toBeDisabled();
  });

  it("renders an explicit routing policy selector", async () => {
    const onRoutingPolicyChange = vi.fn();
    const account = createAccountSummary({ routingPolicy: "normal" });

    render(
      <AccountActions
        account={account}
        busy={false}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onProbe={vi.fn()}
        onDelete={vi.fn()}
        onReauth={vi.fn()}
        onExportAuth={vi.fn()}
        onResetCredit={vi.fn()}
        onSecurityWorkAuthorizedChange={vi.fn()}
        onLimitWarmupChange={vi.fn()}
        onRoutingPolicyChange={onRoutingPolicyChange}
        onCreditPolicyChange={vi.fn()}
      />,
    );

    expect(screen.getByText("Routing policy")).toBeInTheDocument();
    expect(
      screen.getByRole("combobox", { name: "Routing policy" }),
    ).toHaveTextContent("Normal");
  });

  it("renders re-authenticate action for re-auth required accounts", () => {
    const onReauth = vi.fn();
    const account = createAccountSummary({ status: "reauth_required" });

    render(
      <AccountActions
        account={account}
        busy={false}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onProbe={vi.fn()}
        onDelete={vi.fn()}
        onReauth={onReauth}
        onExportAuth={vi.fn()}
        onResetCredit={vi.fn()}
        onSecurityWorkAuthorizedChange={vi.fn()}
        onLimitWarmupChange={vi.fn()}
        onRoutingPolicyChange={vi.fn()}
        onCreditPolicyChange={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: "Re-authenticate" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Pause" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("combobox", { name: "Routing policy" }),
    ).not.toBeInTheDocument();
  });

  it("does not offer resume for re-auth required accounts", () => {
    // The reactivate endpoint refuses this status, so a resume control here
    // would only ever produce a conflict.
    const account = createAccountSummary({ status: "reauth_required" });

    render(
      <AccountActions
        account={account}
        busy={false}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onProbe={vi.fn()}
        onDelete={vi.fn()}
        onReauth={vi.fn()}
        onExportAuth={vi.fn()}
        onResetCredit={vi.fn()}
        onSecurityWorkAuthorizedChange={vi.fn()}
        onLimitWarmupChange={vi.fn()}
        onRoutingPolicyChange={vi.fn()}
        onCreditPolicyChange={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "Resume" })).not.toBeInTheDocument();
  });

  it("resumes a deactivated account alongside re-authentication", async () => {
    const user = userEvent.setup();
    const onResume = vi.fn();
    const account = createAccountSummary({
      accountId: "acc_deactivated",
      status: "deactivated",
    });

    render(
      <AccountActions
        account={account}
        busy={false}
        onPause={vi.fn()}
        onResume={onResume}
        onProbe={vi.fn()}
        onDelete={vi.fn()}
        onReauth={vi.fn()}
        onExportAuth={vi.fn()}
        onResetCredit={vi.fn()}
        onSecurityWorkAuthorizedChange={vi.fn()}
        onLimitWarmupChange={vi.fn()}
        onRoutingPolicyChange={vi.fn()}
        onCreditPolicyChange={vi.fn()}
      />,
    );

    // Both recoveries stay available: resume clears a stale deactivation,
    // re-authentication replaces credentials that are actually gone.
    expect(
      screen.getByRole("button", { name: "Re-authenticate" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Resume" }));
    expect(onResume).toHaveBeenCalledWith("acc_deactivated");
  });

  it("fires the per-account probe callback for active accounts", async () => {
    const user = userEvent.setup();
    const account = createAccountSummary();
    const onProbe = vi.fn();

    render(
      <AccountActions
        account={account}
        busy={false}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onProbe={onProbe}
        onDelete={vi.fn()}
        onReauth={vi.fn()}
        onExportAuth={vi.fn()}
        onResetCredit={vi.fn()}
        onSecurityWorkAuthorizedChange={vi.fn()}
        onLimitWarmupChange={vi.fn()}
        onRoutingPolicyChange={vi.fn()}
        onCreditPolicyChange={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Force probe" }));

    expect(onProbe).toHaveBeenCalledWith(account.accountId);
    expect(onProbe).toHaveBeenCalledTimes(1);
  });

  it.each(["paused", "deactivated"] as const)(
    "disables force probe for %s accounts",
    async (status) => {
      const user = userEvent.setup();
      const account = createAccountSummary({ status });
      const onProbe = vi.fn();

      render(
        <AccountActions
          account={account}
          busy={false}
          onPause={vi.fn()}
          onResume={vi.fn()}
          onProbe={onProbe}
          onDelete={vi.fn()}
          onReauth={vi.fn()}
          onExportAuth={vi.fn()}
          onResetCredit={vi.fn()}
          onSecurityWorkAuthorizedChange={vi.fn()}
          onLimitWarmupChange={vi.fn()}
          onRoutingPolicyChange={vi.fn()}
          onCreditPolicyChange={vi.fn()}
        />,
      );

      const button = screen.getByRole("button", { name: "Force probe" });
      expect(button).toBeDisabled();

      await user.click(button);

      expect(onProbe).not.toHaveBeenCalled();
    },
  );

  it("disables force probe in read-only mode", async () => {
    const user = userEvent.setup();
    const account = createAccountSummary();
    const onProbe = vi.fn();

    render(
      <AccountActions
        account={account}
        busy={false}
        readOnly
        onPause={vi.fn()}
        onResume={vi.fn()}
        onProbe={onProbe}
        onDelete={vi.fn()}
        onReauth={vi.fn()}
        onExportAuth={vi.fn()}
        onResetCredit={vi.fn()}
        onSecurityWorkAuthorizedChange={vi.fn()}
        onLimitWarmupChange={vi.fn()}
        onRoutingPolicyChange={vi.fn()}
        onCreditPolicyChange={vi.fn()}
      />,
    );

    const button = screen.getByRole("button", { name: "Force probe" });
    expect(button).toBeDisabled();

    await user.click(button);

    expect(onProbe).not.toHaveBeenCalled();
  });

  it("shows reset action when reset credits are available", async () => {
    const user = userEvent.setup();
    const onResetCredit = vi.fn();
    const account = createAccountSummary({
      availableResetCredits: 3,
      resetCreditNearestExpiresAt: "2026-01-03T12:00:00.000Z",
    });

    render(
      <AccountActions
        account={account}
        busy={false}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onProbe={vi.fn()}
        onDelete={vi.fn()}
        onReauth={vi.fn()}
        onExportAuth={vi.fn()}
        onResetCredit={onResetCredit}
        onSecurityWorkAuthorizedChange={vi.fn()}
        onLimitWarmupChange={vi.fn()}
        onRoutingPolicyChange={vi.fn()}
        onCreditPolicyChange={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Reset (3)" }));

    expect(onResetCredit).toHaveBeenCalledWith(account.accountId);
  });

  it("hides the reset action expiry label when disabled by settings", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T12:00:00.000Z"));
    try {
      const account = createAccountSummary({
        availableResetCredits: 3,
        resetCreditNearestExpiresAt: "2026-01-01T14:00:00.000Z",
      });

      render(
        <AccountActions
          account={account}
          busy={false}
          onPause={vi.fn()}
          onResume={vi.fn()}
          onProbe={vi.fn()}
          onDelete={vi.fn()}
          onReauth={vi.fn()}
          onExportAuth={vi.fn()}
          onResetCredit={vi.fn()}
          showResetCreditExpiryBadge={false}
          onSecurityWorkAuthorizedChange={vi.fn()}
          onLimitWarmupChange={vi.fn()}
          onRoutingPolicyChange={vi.fn()}
          onCreditPolicyChange={vi.fn()}
        />,
      );

      expect(screen.getByRole("button", { name: "Reset (3)" })).toBeInTheDocument();
      expect(screen.queryByText("2h")).not.toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it.each(["paused", "deactivated", "reauth_required"] as const)(
    "disables reset action for %s accounts",
    async (status) => {
      const user = userEvent.setup();
      const onResetCredit = vi.fn();
      const account = createAccountSummary({
        status,
        availableResetCredits: 2,
        resetCreditNearestExpiresAt: "2026-01-03T12:00:00.000Z",
      });

      render(
        <AccountActions
          account={account}
          busy={false}
          onPause={vi.fn()}
          onResume={vi.fn()}
          onProbe={vi.fn()}
          onDelete={vi.fn()}
          onReauth={vi.fn()}
          onExportAuth={vi.fn()}
          onResetCredit={onResetCredit}
          onSecurityWorkAuthorizedChange={vi.fn()}
          onLimitWarmupChange={vi.fn()}
          onRoutingPolicyChange={vi.fn()}
          onCreditPolicyChange={vi.fn()}
        />,
      );

      const button = screen.getByRole("button", { name: "Reset (2)" });
      expect(button).toBeDisabled();
      await user.click(button);
      expect(onResetCredit).not.toHaveBeenCalled();
    },
  );

  it("hides reset action when no reset credits are available", () => {
    const account = createAccountSummary({
      availableResetCredits: 0,
      resetCreditNearestExpiresAt: null,
    });

    render(
      <AccountActions
        account={account}
        busy={false}
        onPause={vi.fn()}
        onResume={vi.fn()}
        onProbe={vi.fn()}
        onDelete={vi.fn()}
        onReauth={vi.fn()}
        onExportAuth={vi.fn()}
        onResetCredit={vi.fn()}
        onSecurityWorkAuthorizedChange={vi.fn()}
        onLimitWarmupChange={vi.fn()}
        onRoutingPolicyChange={vi.fn()}
        onCreditPolicyChange={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: /Reset \(/ })).not.toBeInTheDocument();
  });
});
