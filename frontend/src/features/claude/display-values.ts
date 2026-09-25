import type { ClaudeAccount } from "./api";

export function claudeStatus(account: ClaudeAccount) {
  if (!account.isEnabled) return "paused";
  if (account.credentialStatus !== "ready") return "reauth_required";
  if (
    account.quota.models.length &&
    account.quota.models.every((model) => model.blocked)
  )
    return "quota_exceeded";
  return "active";
}
