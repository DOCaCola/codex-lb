## Why
Claude Code's `metadata.user_id` carries the authenticated Anthropic account
UUID. codex-lb sent an empty `account_uuid` on translated Codex requests and
forwarded the client's own `account_uuid` on native Claude Code requests, even
when a different pooled account served them. Upstream therefore saw session
metadata naming an account other than the bearer token's.

References agree on binding it to the serving credential: opencodex
(`0f6026ddc`, `account-metadata.ts`) rewrites `account_uuid` to the serving
provider UUID on its native OAuth lane, and CLIProxyAPI (`4fdf59c4`) rebuilds
`user_id` from the credential's profile `account.uuid` on every request.

Anthropic usage data also reports whether pay-as-you-go extra usage is enabled.
Operators had no indication that an account could bill beyond its subscription.

## What Changes
- Persist the authenticated provider account UUID with each Claude account at
  enrollment, reconnect and identity binding. Accounts enrolled before this
  change gain it on their next credential use, after the authenticated
  identity is checked against the enrolled fingerprint.
- Session metadata on every outbound Messages request names the serving
  account's UUID; native requests without metadata stay unchanged.
- Session metadata is projected after the serving credential snapshot, so it
  always matches the bearer token actually sent.
- Claude cards and account-list rows show an "Extra usage" warning badge when
  Anthropic reports extra usage as enabled.

## Capabilities
### Modified Capabilities
- `claude-accounts`: serving-account session metadata, extra-usage presentation.

## Impact
- New nullable `claude_accounts.provider_account_uuid` column (migration).
- `app/modules/claude/{identity,service,dispatch,wire_identity,schemas}.py`.
- Claude account display in the frontend.
