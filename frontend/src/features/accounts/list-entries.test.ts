import type { TFunction } from "i18next";
import { describe, expect, it } from "vitest";

import { buildAccountListEntries, type AccountListSources } from "@/features/accounts/list-entries";
import { createClaudeAccount } from "@/features/claude/test-fixtures";
import { createOpenRouterAccount } from "@/features/openrouter/test-fixtures";
import { createAccountSummary } from "@/test/mocks/factories";

const t = ((key: string) => key) as unknown as TFunction;

function sources(): AccountListSources {
  return {
    accounts: [createAccountSummary({ accountId: "acc_codex", displayName: "Andy Alpha", email: "andy@example.com" })],
    claudeAccounts: [createClaudeAccount({ id: "src_claude", name: "Team Claude" })],
    antigravityAccounts: [],
    openRouterAccounts: [createOpenRouterAccount({ id: "src_openrouter", name: "Acme Router" })],
    modelSources: [],
  };
}

const view = { search: "", statusFilter: "all", quotaDisplay: "both", t } as const;

describe("buildAccountListEntries", () => {
  it("lists Claude before Codex and OpenRouter by default", () => {
    const entries = buildAccountListEntries(sources(), { ...view, sortMode: "reset_soonest" });

    expect(entries.map((entry) => entry.id)).toEqual(["src_claude", "acc_codex", "src_openrouter"]);
  });

  it("orders every provider together when sorted by name", () => {
    const entries = buildAccountListEntries(sources(), { ...view, sortMode: "name_asc" });

    expect(entries.map((entry) => entry.id)).toEqual(["src_openrouter", "acc_codex", "src_claude"]);
  });

  it("filters every provider by the search text", () => {
    const entries = buildAccountListEntries(sources(), { ...view, search: "andy", sortMode: "reset_soonest" });

    expect(entries.map((entry) => entry.kind)).toEqual(["codex"]);
  });
});
