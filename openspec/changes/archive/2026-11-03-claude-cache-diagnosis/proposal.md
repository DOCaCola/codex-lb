# Claude cache diagnosis

Our miss logger compares a request with the previous one we saw, but it cannot
explain misses with identical content, such as the recurring Claude misses
shortly after 00:00 UTC. Anthropic explains a miss itself when the request names
the previous message of the conversation. Claude Code sends that reference, and
CLIProxyAPI adds it to the requests it translates. Our translated requests don't.

## Scope

Translated Codex-to-Claude Messages requests carry `diagnostics` with the
previous completed message of the same conversation on the same account, plus
the `cache-diagnosis-2026-04-07` beta. Anthropic's reported miss reason is
logged for translated and native traffic. Native requests are forwarded as the
client sends them.
