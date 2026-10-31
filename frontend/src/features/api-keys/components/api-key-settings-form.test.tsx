import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import type { ApiKey, LimitRuleCreate } from "@/features/api-keys/schemas";
import { createAccountSummary, createApiKey } from "@/test/mocks/factories";
import { server } from "@/test/mocks/server";
import { renderWithProviders } from "@/test/utils";

import { ApiKeySettingsForm } from "./api-key-settings-form";
import { hasLimitRuleChanges } from "./limit-rules-utils";

function renderForm(apiKey: ApiKey = createApiKey(), onSave = vi.fn().mockResolvedValue(undefined)) {
  const handlers = {
    onSave,
    onResetUsage: vi.fn().mockResolvedValue(undefined),
    onRegenerate: vi.fn(),
    onToggleActive: vi.fn(),
    onDelete: vi.fn(),
  };
  renderWithProviders(<ApiKeySettingsForm apiKey={apiKey} busy={false} {...handlers} />);
  return handlers;
}

async function rename(user: ReturnType<typeof userEvent.setup>, name = "Renamed key") {
  const nameInput = screen.getByLabelText("Name");
  await user.clear(nameInput);
  await user.type(nameInput, name);
}

async function saveAndGetPayload(user: ReturnType<typeof userEvent.setup>, onSave: ReturnType<typeof vi.fn>) {
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
  return onSave.mock.calls[0][0];
}

function withTwoAccounts() {
  server.use(
    http.get("/api/accounts", () =>
      HttpResponse.json({
        accounts: [
          createAccountSummary(),
          createAccountSummary({
            accountId: "acc_secondary",
            email: "secondary@example.com",
            displayName: "secondary@example.com",
          }),
        ],
      }),
    ),
  );
}

describe("ApiKeySettingsForm", () => {
  it("shows no save bar until something changes", async () => {
    const user = userEvent.setup();
    renderForm();

    expect(screen.queryByRole("region", { name: "Unsaved changes" })).not.toBeInTheDocument();
    await rename(user);
    expect(within(screen.getByRole("region", { name: "Unsaved changes" })).getByText("1 unsaved change")).toBeInTheDocument();
  });

  it("sends only the changed field", async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm();

    await rename(user);
    expect(await saveAndGetPayload(user, onSave)).toEqual({ name: "Renamed key" });
  });

  it("discards edits and hides the save bar", async () => {
    const user = userEvent.setup();
    const apiKey = createApiKey({ name: "Original" });
    const { onSave } = renderForm(apiKey);

    await rename(user);
    await user.click(screen.getByRole("button", { name: "Discard" }));

    expect(screen.getByLabelText("Name")).toHaveValue("Original");
    expect(screen.queryByRole("region", { name: "Unsaved changes" })).not.toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("keeps the edits when saving fails", async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm(createApiKey(), vi.fn().mockRejectedValue(new Error("boom update")));

    await rename(user);
    await saveAndGetPayload(user, onSave);

    expect(screen.getByLabelText("Name")).toHaveValue("Renamed key");
    expect(screen.getByRole("region", { name: "Unsaved changes" })).toBeInTheDocument();
  });

  it("blocks saving an empty name", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.clear(screen.getByLabelText("Name"));
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
  });

  it("labels the reasoning effort trigger with its field and state", () => {
    renderForm(createApiKey({ allowedReasoningEfforts: ["low"] }));

    expect(screen.getByRole("button", { name: "Allowed efforts: 1 effort selected" })).toBeInTheDocument();
  });

  it("preserves a malformed fail-closed reasoning policy on unrelated edits", async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm(createApiKey({ allowedReasoningEfforts: [] }));

    await rename(user);
    const payload = await saveAndGetPayload(user, onSave);
    expect("allowedReasoningEfforts" in payload).toBe(false);
  });

  it("renders and clears the transport policy override", async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm(createApiKey({ transportPolicyOverride: "always_http" }));

    const trigger = screen.getByRole("combobox", { name: "HTTP client routing" });
    expect(trigger).toHaveTextContent("Prefer request/response");
    await user.click(trigger);
    await user.click(await screen.findByRole("option", { name: "Follow global default" }));

    expect(await saveAndGetPayload(user, onSave)).toEqual({ transportPolicyOverride: null });
  });

  it("sends limits only when a limit value changes", async () => {
    const user = userEvent.setup();
    const apiKey = createApiKey();
    const { onSave } = renderForm(apiKey);

    const tokenLimitInput = screen.getByDisplayValue(String(apiKey.limits[0].maxValue));
    await user.clear(tokenLimitInput);
    await user.type(tokenLimitInput, "999999");

    expect(await saveAndGetPayload(user, onSave)).toEqual({
      limits: [{ limitType: "total_tokens", limitWindow: "weekly", maxValue: 999999, modelFilter: null }],
    });
  });

  it("confirms before resetting limit usage", async () => {
    const user = userEvent.setup();
    const { onResetUsage } = renderForm();

    await user.click(screen.getByRole("button", { name: "Reset usage" }));
    expect(onResetUsage).not.toHaveBeenCalled();
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Reset usage" }));

    await waitFor(() => expect(onResetUsage).toHaveBeenCalledTimes(1));
  });

  it("submits selected assigned accounts", async () => {
    const user = userEvent.setup();
    withTwoAccounts();
    const { onSave } = renderForm();

    await user.click(await screen.findByRole("button", { name: "All accounts" }));
    await user.click(screen.getByRole("menuitemcheckbox", { name: /primary@example\.com/i }));
    await user.click(screen.getByRole("menuitemcheckbox", { name: /secondary@example\.com/i }));
    await user.keyboard("{Escape}");

    const payload = await saveAndGetPayload(user, onSave);
    expect(payload.assignedAccountIds).toEqual(["acc_primary", "acc_secondary"]);
  });

  it("submits an empty account list when clearing assigned accounts", async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm(
      createApiKey({ accountAssignmentScopeEnabled: true, assignedAccountIds: ["acc_primary"] }),
    );

    await user.click(await screen.findByRole("button", { name: "1 account selected" }));
    await user.click(screen.getByRole("menuitemcheckbox", { name: "All accounts" }));
    await user.keyboard("{Escape}");

    expect(await saveAndGetPayload(user, onSave)).toEqual({ assignedAccountIds: [] });
  });

  it("keeps a deny-all account scope when editing an unrelated field", async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm(createApiKey({ accountAssignmentScopeEnabled: true, assignedAccountIds: [] }));

    await rename(user);
    expect(await saveAndGetPayload(user, onSave)).toEqual({ name: "Renamed key" });
  });

  it("submits an empty account list when explicitly removing a deny-all account scope", async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm(createApiKey({ accountAssignmentScopeEnabled: true, assignedAccountIds: [] }));

    await user.click(screen.getByRole("checkbox", { name: "Remove account restriction (allow all accounts)" }));
    expect(await saveAndGetPayload(user, onSave)).toEqual({ assignedAccountIds: [] });
  });

  it("keeps a deny-all source scope when editing an unrelated field", async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm(createApiKey({ sourceAssignmentScopeEnabled: true, assignedSourceIds: [] }));

    await rename(user);
    expect(await saveAndGetPayload(user, onSave)).toEqual({ name: "Renamed key" });
  });

  it("submits an empty source list when explicitly removing a deny-all source scope", async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm(createApiKey({ sourceAssignmentScopeEnabled: true, assignedSourceIds: [] }));

    await user.click(screen.getByRole("checkbox", { name: "Remove source restriction (allow all sources)" }));
    expect(await saveAndGetPayload(user, onSave)).toEqual({ assignedSourceIds: [] });
  });

  it("shows and submits the codex /model setting", async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm(createApiKey({ applyToCodexModel: false }));

    const toggle = screen.getByRole("switch", { name: "Apply to codex /model" });
    expect(toggle).not.toBeChecked();
    await user.click(toggle);

    expect(await saveAndGetPayload(user, onSave)).toEqual({ applyToCodexModel: true });
  });

  it("shows and submits the traffic class", async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm(createApiKey({ trafficClass: "foreground" }));

    const group = screen.getByRole("group", { name: "Traffic class" });
    expect(within(group).getByRole("button", { name: /foreground/i })).toHaveAttribute("aria-pressed", "true");
    await user.click(within(group).getByRole("button", { name: /opportunistic/i }));

    expect(await saveAndGetPayload(user, onSave)).toEqual({ trafficClass: "opportunistic" });
  });

  it("shows the stored Ultrafast service tier", () => {
    renderForm(createApiKey({ enforcedServiceTier: "ultrafast" }));

    expect(screen.getByRole("combobox", { name: "Enforced service tier" })).toHaveTextContent("Ultrafast");
  });

  it("runs the key actions", async () => {
    const user = userEvent.setup();
    const handlers = renderForm(createApiKey({ isActive: true }));

    await user.click(screen.getByRole("button", { name: "Regenerate" }));
    await user.click(screen.getByRole("button", { name: "Disable" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(handlers.onRegenerate).toHaveBeenCalledTimes(1);
    expect(handlers.onToggleActive).toHaveBeenCalledTimes(1);
    expect(handlers.onDelete).toHaveBeenCalledTimes(1);
  });
});

describe("hasLimitRuleChanges", () => {
  it("treats reordered identical rule sets as unchanged", () => {
    const initial: LimitRuleCreate[] = [
      { limitType: "total_tokens", limitWindow: "weekly", maxValue: 1000, modelFilter: null },
      { limitType: "cost_usd", limitWindow: "monthly", maxValue: 1_500_000, modelFilter: "gpt-5.1" },
    ];
    const reordered: LimitRuleCreate[] = [initial[1], initial[0]];

    expect(hasLimitRuleChanges(initial, reordered)).toBe(false);
  });
});
