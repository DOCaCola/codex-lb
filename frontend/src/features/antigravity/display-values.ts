import type { AntigravityAccount, AntigravityWindow, QuotaFamily } from "./api";

export const FAMILY_LABELS: Record<QuotaFamily, string> = {
  gemini: "Gemini",
  argon: "Gemini 4 Argon",
  claude: "Claude & GPT",
};

/** Labels for narrow quota columns. */
export const SHORT_FAMILY_LABELS: Record<QuotaFamily, string> = {
  gemini: "Gemini",
  argon: "Argon",
  claude: "Claude",
};

export const WINDOW_LABELS: Record<AntigravityWindow["window"], string> = {
  five_hour: "5h",
  weekly: "Weekly",
};

export function modelSummary(account: AntigravityAccount): string {
  if (account.state.all_models) return "All models";
  const count = account.state.selections.length;
  return count + " " + (count === 1 ? "model" : "models") + " selected";
}

function activeScopes(account: AntigravityAccount, now: number): Set<string> {
  return new Set(
    account.cooldowns.filter((cooldown) => Date.parse(cooldown.until) > now).map((cooldown) => cooldown.scope),
  );
}

/** Families with a quota reading, in display order. */
export function quotaFamilies(account: AntigravityAccount): QuotaFamily[] {
  const present = new Set(account.windows.map((window) => window.family));
  return (["gemini", "argon", "claude"] as const).filter((family) => present.has(family));
}

/** The window with the least quota left for a family; it decides whether the family can serve. */
export function bindingWindow(account: AntigravityAccount, family: QuotaFamily): AntigravityWindow | null {
  return account.windows
    .filter((window) => window.family === family)
    .reduce<AntigravityWindow | null>(
      (binding, window) => (binding === null || window.usedPercent > binding.usedPercent ? window : binding),
      null,
    );
}

export function antigravityStatus(account: AntigravityAccount, now = Date.now()) {
  if (!account.isEnabled) return "paused";
  if (account.hold !== null) return "deactivated";
  if (account.credentialStatus !== "ready") return "reauth_required";
  const scopes = activeScopes(account, now);
  if (scopes.has("account")) return "rate_limited";
  const families = quotaFamilies(account);
  const blocked = families.filter(
    (family) =>
      scopes.has("family:" + family) ||
      account.windows.some((window) => window.family === family && window.exhausted),
  );
  if (families.length === 0 || blocked.length < families.length) return "active";
  // Like Codex accounts: only drained weekly windows are "quota exceeded"; anything shorter is "rate limited".
  const weeklyDrained = families.every((family) =>
    account.windows.some((window) => window.family === family && window.window === "weekly" && window.exhausted),
  );
  return weeklyDrained ? "quota_exceeded" : "rate_limited";
}
