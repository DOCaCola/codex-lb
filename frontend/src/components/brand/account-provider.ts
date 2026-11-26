export const ACCOUNT_PROVIDERS = ["codex", "claude", "antigravity", "openai_apikey", "openrouter", "openai_compatible"] as const;

export type AccountProvider = (typeof ACCOUNT_PROVIDERS)[number];

/** Provider of a model-source kind; every kind is a provider account. */
export function sourceKindProvider(kind: string | null | undefined): AccountProvider | null {
  return kind === "claude" ||
    kind === "antigravity" ||
    kind === "openai_apikey" ||
    kind === "openrouter" ||
    kind === "openai_compatible"
    ? kind
    : null;
}
