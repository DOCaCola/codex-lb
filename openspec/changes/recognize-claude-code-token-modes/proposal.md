# Recognize Claude Code in both token modes

## Why

A lab run of Claude Code 2.1.316 against codex-lb showed that genuine Claude Code was often
not recognized as native, so codex-lb rewrote its requests. Three gaps caused this:

- The documented setup (`ANTHROPIC_AUTH_TOKEN`) puts Claude Code in API-key mode, which never
  sends the OAuth beta that recognition required.
- `claude -p` and the Agent SDK identify as `sdk-cli`/`sdk-ts` and append `agent-sdk/`,
  `client-app/` and `workload/` fields; background sessions send `x-app: cli-bg`
  (CLIProxyAPI #7373, #7412). Recognition accepted only the bare `cli` user agent.
- When every Claude account was quota-blocked, codex-lb refused locally without Anthropic's
  unified rate-limit headers, so Claude Code reported "Server is temporarily limiting requests
  (not your usage limit)" instead of the usage limit and its reset (CLIProxyAPI #7417).

The lab also showed that with `CLAUDE_CODE_OAUTH_TOKEN` and non-essential traffic enabled, Claude
Code sends the configured token to `api.anthropic.com`. agent-lb and opencodex advise against
`ANTHROPIC_AUTH_TOKEN` because it switches Claude Code to API billing behavior.

## What Changes

- Native recognition accepts Claude Code's `cli`, `sdk-cli`, `sdk-ts` and `claude-vscode`
  entrypoints with well-formed `name/value` user-agent fields, `x-app` `cli` or `cli-bg`,
  and either the Claude Code beta or the OAuth beta.
- Local quota refusals on native Messages carry `anthropic-ratelimit-unified-*` headers naming
  the blocking window and its observed reset.
  Unlike CLIProxyAPI, the refusal omits the overage status: Claude Code 2.1.316 shows the generic
  "You've hit your limit" for a bare rejected overage status, and codex-lb doesn't know the
  account's extra-usage setup.
- Client setup recommends subscription mode (`CLAUDE_CODE_OAUTH_TOKEN` with
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`) and keeps `ANTHROPIC_AUTH_TOKEN` as the
  alternative.

## Impact

Claude native recognition, local Claude quota refusals and client documentation. Translated
Responses traffic and third-party Messages clients are unchanged.
