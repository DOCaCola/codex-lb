export const ACCOUNT_PROVIDERS = ["codex", "claude", "openrouter"] as const;

export type AccountProvider = (typeof ACCOUNT_PROVIDERS)[number];
