import type { TFunction } from "i18next";

import type { AccountSummary } from "@/features/accounts/schemas";
import { sortAccountsForDisplay, type AccountSortMode } from "@/features/accounts/sorting";
import type { AntigravityAccount } from "@/features/antigravity/api";
import { antigravityStatus } from "@/features/antigravity/display-values";
import type { ClaudeAccount } from "@/features/claude/api";
import { claudeStatus } from "@/features/claude/display-values";
import type { ModelSource } from "@/features/model-sources/schemas";
import { modelSourceStatus } from "@/features/model-sources/display-values";
import type { OpenRouterAccount } from "@/features/openrouter/api";
import { openRouterStatus } from "@/features/openrouter/display-values";
import type { AccountQuotaDisplayPreference } from "@/hooks/use-account-quota-display";

export type AccountListSources = {
  accounts: AccountSummary[];
  claudeAccounts: ClaudeAccount[];
  antigravityAccounts: AntigravityAccount[];
  openRouterAccounts: OpenRouterAccount[];
  modelSources: ModelSource[];
};

export type AccountListView = {
  search: string;
  statusFilter: string;
  sortMode: AccountSortMode;
  quotaDisplay: AccountQuotaDisplayPreference;
  t: TFunction;
};

export type AccountListEntry =
  | { kind: "claude"; id: string; name: string; account: ClaudeAccount }
  | { kind: "antigravity"; id: string; name: string; account: AntigravityAccount }
  | { kind: "codex"; id: string; name: string; account: AccountSummary }
  | { kind: "openrouter"; id: string; name: string; account: OpenRouterAccount }
  | { kind: "openai_compatible"; id: string; name: string; account: ModelSource };

/**
 * Rows of the Accounts page list, in display order: Claude, Antigravity, Codex,
 * OpenRouter, then OpenAI-compatible sources, or all of them by name when the
 * list is sorted by name.
 */
export function buildAccountListEntries(sources: AccountListSources, view: AccountListView): AccountListEntry[] {
  const { search, statusFilter, sortMode, quotaDisplay, t } = view;
  const needle = search.trim().toLowerCase();
  const matches = (status: string, haystack: string) =>
    (statusFilter === "all" || status === statusFilter) && (!needle || haystack.toLowerCase().includes(needle));
  const byName = (a: { name: string }, b: { name: string }) => a.name.localeCompare(b.name);

  const result: AccountListEntry[] = [
    ...sources.claudeAccounts
      .filter((account) =>
        matches(
          claudeStatus(account),
          `${account.name} ${account.id} claude anthropic ${account.planType.replaceAll("_", " ")} ${t(`claude.subscription.${account.planType}`)}`,
        ),
      )
      .map((account) => ({ kind: "claude" as const, id: account.id, name: account.name, account })),
    ...sources.antigravityAccounts
      .filter((account) =>
        matches(
          antigravityStatus(account),
          `${account.name} ${account.id} ${account.email} antigravity google gemini ${account.planType.replaceAll("_", " ")} ${t(`antigravity.plan.${account.planType}`)}`,
        ),
      )
      .map((account) => ({ kind: "antigravity" as const, id: account.id, name: account.name, account })),
    ...sortAccountsForDisplay(sources.accounts, quotaDisplay, sortMode)
      .filter((account) =>
        matches(
          account.status,
          `${account.email} ${account.alias ?? ""} ${account.displayName} ${account.accountId} ${account.planType}`,
        ),
      )
      .map((account) => ({
        kind: "codex" as const,
        id: account.accountId,
        name: account.displayName || account.email,
        account,
      })),
    ...sources.openRouterAccounts
      .filter((account) => matches(openRouterStatus(account), `${account.name} ${account.id} openrouter`))
      .sort(byName)
      .map((account) => ({ kind: "openrouter" as const, id: account.id, name: account.name, account })),
    ...sources.modelSources
      .filter((source) =>
        matches(
          modelSourceStatus(source),
          `${source.name} ${source.id} ${source.baseUrl} openai-compatible openai compatible`,
        ),
      )
      .sort(byName)
      .map((source) => ({ kind: "openai_compatible" as const, id: source.id, name: source.name, account: source })),
  ];
  if (sortMode === "name_asc" || sortMode === "name_desc") {
    result.sort(
      (a, b) => (sortMode === "name_desc" ? -1 : 1) * a.name.localeCompare(b.name, undefined, { sensitivity: "base" }),
    );
  }
  return result;
}
