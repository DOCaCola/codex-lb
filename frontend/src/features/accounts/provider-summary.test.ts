import { describe, expect, it } from "vitest";

import {
  buildProviderGroups,
  filterGroups,
  linearPacePercent,
  summarizeEntry,
  summarizeSources,
  type ProviderSummary,
} from "@/features/accounts/provider-summary";
import { providerSources, summaryContext } from "@/features/accounts/test-utils";
import { createAntigravityAccount } from "@/features/antigravity/test-fixtures";
import { createClaudeAccount } from "@/features/claude/test-fixtures";
import { createOpenRouterAccount } from "@/features/openrouter/test-fixtures";
import { createAccountSummary, createModelSource } from "@/test/mocks/factories";

const NOW = Date.parse("2026-01-01T12:00:00Z");
const inHours = (hours: number) => new Date(NOW + hours * 3_600_000).toISOString();

function codex(overrides: Parameters<typeof createAccountSummary>[0] = {}, quotaDisplay: "both" | "weekly" | "5h" = "both"): ProviderSummary {
  return summarizeEntry({ kind: "codex", account: createAccountSummary(overrides) }, summaryContext({ now: NOW, quotaDisplay }));
}

describe("provider summaries", () => {
  it("groups accounts by provider in display order and leaves out empty providers", () => {
    const groups = buildProviderGroups(
      providerSources({
        modelSources: [createModelSource()],
        openRouterAccounts: [createOpenRouterAccount()],
        claudeAccounts: [createClaudeAccount()],
        accounts: [createAccountSummary()],
      }),
      "name_asc",
      summaryContext({ now: NOW }),
    );
    expect(groups.map((group) => group.kind)).toEqual(["codex", "claude", "openrouter", "openai_compatible"]);
  });

  it("sorts each group by the selected mode", () => {
    const groups = buildProviderGroups(
      providerSources({
        claudeAccounts: [createClaudeAccount({ id: "a", name: "Alpha" }), createClaudeAccount({ id: "z", name: "Zulu" })],
      }),
      "name_desc",
      summaryContext({ now: NOW }),
    );
    expect(groups[0].summaries.map((summary) => summary.name)).toEqual(["Zulu", "Alpha"]);
  });

  it("keeps each provider's source order when summarising without a sort", () => {
    const summaries = summarizeSources(
      providerSources({
        claudeAccounts: [createClaudeAccount({ id: "z", name: "Zulu" }), createClaudeAccount({ id: "a", name: "Alpha" })],
        accounts: [
          createAccountSummary({ accountId: "pro", displayName: "Pro", availableResetCredits: 0 }),
          createAccountSummary({ accountId: "plus", displayName: "Plus", availableResetCredits: 3 }),
        ],
      }),
      summaryContext({ now: NOW }),
    );
    expect(summaries.map((summary) => summary.id)).toEqual(["pro", "plus", "z", "a"]);
  });

  it("shows the weekly and 5-hour Codex windows by the quota preference", () => {
    expect(codex().limits.map((limit) => limit.key)).toEqual(["weekly", "5h"]);
    expect(codex({}, "weekly").limits.map((limit) => limit.key)).toEqual(["weekly"]);
    expect(codex({}, "5h").limits.map((limit) => limit.key)).toEqual(["5h"]);
  });

  it("shows only the windows a Codex plan has", () => {
    const weeklyOnly = codex({ windowMinutesPrimary: null, resetAtPrimary: null, usage: { primaryRemainingPercent: null, secondaryRemainingPercent: 40, monthlyRemainingPercent: null } });
    expect(weeklyOnly.limits.map((limit) => limit.key)).toEqual(["weekly"]);
    const monthlyOnly = codex({
      windowMinutesPrimary: null,
      windowMinutesSecondary: null,
      resetAtPrimary: null,
      resetAtSecondary: null,
      windowMinutesMonthly: 43_200,
      resetAtMonthly: inHours(240),
      usage: { primaryRemainingPercent: null, secondaryRemainingPercent: null, monthlyRemainingPercent: 30 },
    });
    expect(monthlyOnly.limits.map((limit) => [limit.key, limit.value])).toEqual([["monthly", "30%"]]);
  });

  it("marks the even pace of the weekly window", () => {
    expect(linearPacePercent(inHours(84), 10_080, NOW)).toBe(50);
    expect(linearPacePercent(null, 10_080, NOW)).toBeNull();
    const weekly = codex({ resetAtSecondary: inHours(84) }).limits.find((limit) => limit.key === "weekly");
    expect(weekly?.pacePercent).toBe(50);
  });

  it("explains why an account needs attention", () => {
    expect(codex({ status: "paused" }).notice).toEqual({ tone: "off", text: "Paused", label: "Paused" });
    expect(codex({ status: "reauth_required" }).notice).toEqual({ tone: "bad", text: "Sign in again", label: "Sign in again" });
    const drained = codex({
      status: "quota_exceeded",
      resetAtSecondary: inHours(30),
      usage: { primaryRemainingPercent: 50, secondaryRemainingPercent: 0, monthlyRemainingPercent: null },
    });
    expect(drained.tone).toBe("bad");
    expect(drained.notice?.text).toMatch(/^Weekly limit · back in /);
    expect(drained.notice?.label).toBe("Weekly limit");
    expect(drained.routingPolicy).toBe("normal");
    expect(codex({ status: "deactivated" }).routingPolicy).toBeNull();
  });

  it("warns about an upcoming subscription end", () => {
    const summary = summarizeEntry(
      { kind: "codex", account: createAccountSummary() },
      summaryContext({ now: NOW, subscriptionEnds: [{ accountId: "acc_primary", modelSourceId: null, endsAt: inHours(48) }] }),
    );
    expect(summary.notice).toEqual({ tone: "warn", text: expect.stringMatching(/^Subscription ends /), label: expect.stringMatching(/^Subscription ends /) });
  });

  it("filters by attention and pause state and searches across providers", () => {
    const groups = buildProviderGroups(
      providerSources({
        accounts: [createAccountSummary({ status: "rate_limited" })],
        claudeAccounts: [createClaudeAccount({ isEnabled: false })],
        antigravityAccounts: [createAntigravityAccount({ email: "gemini@example.com" })],
        modelSources: [createModelSource()],
      }),
      "name_asc",
      summaryContext({ now: NOW }),
    );
    const kinds = (filtered: typeof groups) => filtered.map((group) => group.kind);
    expect(kinds(filterGroups(groups, "attention", ""))).toEqual(["codex"]);
    expect(kinds(filterGroups(groups, "paused", ""))).toEqual(["claude"]);
    expect(kinds(filterGroups(groups, "all", "gemini@"))).toEqual(["antigravity"]);
    expect(kinds(filterGroups(groups, "all", "localhost:8000"))).toEqual(["openai_compatible"]);
    expect(filterGroups(groups, "all", "nothing matches")).toEqual([]);
  });
});
