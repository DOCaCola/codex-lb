import type { ClaudeAccount } from "./api";

export function claudeStatus(account: ClaudeAccount) {
  if (!account.isEnabled) return "paused";
  if (account.credentialStatus !== "ready") return "reauth_required";
  if (
    account.quota.models.length &&
    account.quota.models.every((model) => model.blocked)
  ) {
    // Like Codex accounts: only a drained weekly window is "quota exceeded";
    // a drained 5-hour window (or another temporary block) is "rate limited".
    const weeklyDrained = account.quota.windows.some(
      (window) => window.exhausted && window.name.startsWith("seven_day"),
    );
    return weeklyDrained ? "quota_exceeded" : "rate_limited";
  }
  return "active";
}
