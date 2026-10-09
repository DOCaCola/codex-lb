## Why

Codex selects remote compaction at the provider level. Because codex-lb is
configured as the OpenAI provider, a terminal `compaction_trigger` is sent for
models served by OpenAI-compatible model sources even though those sources do
not implement the private OpenAI compaction protocol.

Today the Codex route excludes terminal compaction from model-source routing
and sends it to a subscription account. A source-owned model is then rejected
as unsupported. A later native compaction can also reject source-generated
reasoning history whose `reasoning.content` contains plaintext blocks.

## What Changes

- Select an eligible model source for terminal compaction requests instead of
  forcing every compact turn onto a subscription account.
- Run source-owned compaction as an ordinary, tool-free summarization request
  and wrap the completed summary in a codex-lb-owned compaction envelope.
- Decode codex-lb-owned compaction envelopes into explicit summary context
  before any later upstream request.
- Replace native opaque compaction history with an explicit note when the next
  destination is a model source that cannot decode it.
- Sanitize source-generated plaintext reasoning items at the native
  subscription boundary without changing ordinary model-source replay.
- Remove lookup-only top-level item IDs before stateless Responses egress so
  temporary output identities are not interpreted as persisted-item references.

## Capabilities

### Modified Capabilities

- `responses-api-compat`
- `model-source-routing`

## Impact

- No database migration, setting, dashboard surface, or new deployment step.
- Existing subscription-backed native compaction remains the default for
  subscription models.
- Existing WebSocket-to-HTTP model-source transport selection remains
  unchanged; synthetic compaction runs after the request reaches the HTTP
  model-source path.
