# Output-token replay compatibility investigation

Observed 2026-10-28 against deployment 81f114696d675939d08f42a8cc4e0629e07cb8ff.
The affected Windows client advanced from 0.164.0-alpha.11.1 to 0.165.0-alpha.1.2,
and its diagnostics changed feature.output_token_replay from false to true. Its
latest recorded error at 07:45:57.071 UTC was 400 invalid_request_error, param include.
The exact outgoing include array was not retained on that computer.

Independent reproduction submitted a minimal request containing
[reasoning.encrypted_content, output.encrypted_content]. Production returned the
same error over both HTTP and WebSocket. HTTP request 7beba543-9bc4-495e-b1c8-1bb6af561e29
was rejected locally: the ResponsesRequest validator reports
"Unsupported include value: output.encrypted_content". The new value is absent
from the shared ingress allowlist, so this rejection precedes upstream dispatch.

Codex source 26ad281fd1ca712e4f0c7920a6273cf18c961b8a (2026-10-28),
codex-rs/core/src/client.rs, conditionally requests that include when replay is
enabled for OpenAI. Its core/tests/suite/output_token_replay.rs verifies ciphertext
on assistant messages and function calls, including subsequent replay. This source
was inspected directly; it is not a proven source match for the Windows alpha.

## Reference comparison

Fetched and inspected on 2026-10-28. These are source findings, not live
qualification of the other gateways. Absence of the exact literal does not imply
rejection: generic forwarding can preserve new include values without naming them.
No reference code was copied.

| Reference revision | Relevant behavior |
| --- | --- |
| OpenAI Codex 26ad281fd1ca712e4f0c7920a6273cf18c961b8a (Oct 28) | client.rs:1115-1118 appends output.encrypted_content when the feature is enabled for OpenAI; output_token_replay.rs tests message/tool-call ciphertext and subsequent replay. |
| Soju06 codex-lb 72630bbfeee9e3b0d9acfb95e2b1e706b8b0188e (Oct 17) | app/core/openai/requests.py:47 has the same stale include allowlist and rejects unknown values. |
| Frozen811 codex-lb 9d22321892602f2a762e166894bc63a7a74aa41b (Oct 15) | app/core/openai/requests.py:48 has the same omission and validator. |
| Agent LB 77ba1fd9b26bf69e736b507cbd949aef842f498c (Oct 28) | app/core/openai/requests.py:17 has the same omission and validator. |
| Sub2API 0a2a29b32e6724714c69822296ccd05a6b86bfdd (Oct 28) | backend/internal/service/openai_codex_transform.go:1439 ensureCodexReasoningInclude preserves existing array entries, appending reasoning.encrypted_content only if missing. |
| OmniRoute 8a8c64ee33b83803df74628a83f8372f7a1432c7 (Oct 28) | open-sse/executors/codex.ts:332 preserves existing include entries while adding reasoning.encrypted_content; request/openai-responses/toResponses.ts:551 also copies caller include arrays. |
| OpenCodex 88aaa754566d119b6b8fc898f8fb47602387d82e (Oct 27) | src/server/responses/codex-ws-request.ts prepares response.create by spreading the body and removing stream, preserving include generically. This narrow transport finding does not establish every adapter/ciphertext path. |
| CLIProxyAPI ad8bdd3f20bef44f0684b8a6096a216b2c76040d (Oct 27) | internal/translator/codex/openai/responses/codex_openai-responses_request.go:120 setCodexRequiredInclude rebuilds the list with reasoning and optional web-search sources, discarding the new value on that translation path. Same-format registry fallback preserves the body; do not generalize the translation finding to every native path. |

## Why this appeared now

The Windows diagnostics show output_token_replay=false on the last successful
client and true after the upgrade. Official client source connects that feature
to the new include value. The allowlist omission already exists in the parent of
81f1146; the unavailable-model fix did not edit requests.py. The new client
therefore exposed an existing validation gap. The exact Windows outgoing array
remains inferred, while the same local rejection was independently reproduced.
The include error occurs before dispatch; neither the reported context limit nor
the chat's existing compaction explains this minimal reproduction.

The protocol correction accepts the native include value. Existing generic
response forwarding and native input normalization retain the corresponding
ciphertext. It does not disable the client's feature or silently discard data.
The regression tests cover both ingress paths, HTTP streaming and non-streaming,
WebSocket, response events, subsequent replay, and invalid include types/values.

## Live upstream qualification

After SSH recovered, a standalone process in the production container used the
existing account and configured egress route, bypassing only the stale ingress
enum. The wire payload retained both include values. HTTP generation completed:
resp_0a11332bf0b6e04e016ae1b75626a08191801ca2c18693f542. WebSocket generation
resp_0158fed173b711ff016ae1b79076fc8191b1530750f4ef6aff and a second request
replaying that output, resp_04fd483387fbaa26016ae1b792fbb08191b3360b1f72f74be6,
both completed with no upstream error on gpt-6-astra.

Neither transport returned message encrypted_content. The original probe's
ciphertext assertion consequently failed after a successful HTTP response. The
WebSocket probe recorded presence rather than assuming ciphertext was mandatory.
This establishes upstream acceptance and ordinary output replay, not live
encrypted-output replay. Why this account/model did not emit ciphertext is not
established. Local transport regressions verify ciphertext preservation when it
is supplied. No credentials or ciphertext were printed or persisted. The running
service and affected chat were not modified; only isolated synthetic requests
were made. Keep live encrypted-replay qualification explicitly outstanding.

Validation: 20 focused request/include/encrypted-content regressions passed,
including 14 new transport cases. make lint passed. All 77 main specs and the
strict change validation passed. ty check has675 existing diagnostics, identical
to the prior committed baseline; this change adds none. Live encrypted-output
replay qualification and deployment remain pending; SSH is available again.
