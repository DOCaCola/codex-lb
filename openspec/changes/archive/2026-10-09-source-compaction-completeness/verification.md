# Verification — 2026-09-30

## Implemented
- Source materialization and summary construction no longer use native compact
  wire reduction. Terminal construction is structural; native dispatch still
  performs its previous early native validation.
- Source compaction retains supported images and tool-result/text contents,
  removes only compact/control declarations, disables input truncation and
  protects its history/stateless/tool-free contract from model overrides.
- Claude complete-history attempts authenticate signed blocks and require their
  original account/model, even for completed thinking. They do not use lossy
  signature-recovery retries. Ordinary Responses/native Messages are unchanged.
- Oversize or incomplete results produce an error without a checkpoint or
  replacement of the original retained conversation. No staged summarization,
  compaction-model fallback, approximate local context gate or deployment added.

## Tests
- 501 tests passed across compaction compatibility, Claude replay, native compact
  fixtures, request policy, complete source compaction, native compact/hop-by-hop/
  trigger routes, model-source routing, Claude inference and OpenRouter accounts.
- An additional 188 OpenAI request/serialization tests passed, including native
  compact trimming and anchor behavior. Total: 689 tests across these suites.
- Focused 62-test suite covers 600k-character tool output, early/middle/latest
  facts, images, retained continuation, both dedicated endpoints, both actual
  websocket surfaces, post-checkpoint continuation, capacity/incomplete failure
  atomicity, signed owners/models/search, signature rejection without reduction,
  conflicting signed owners, pending calls, protected overrides and usage/admission
  settlement. OpenRouter dedicated compact mocks also preserve above-budget
  text/image history at the upstream wire boundary.
- Incomplete paid generations finalize their reported usage; explicit capacity
  refusals release reservations. No admission slots remain held. Original anchors
  remain byte-equivalent and usable after failed compaction.

## Static/spec checks
- Ruff lint/format checks passed for all 11 affected code/test files.
- Scoped ty passed for all seven affected app files and the three focused
  compaction/replay test files. A wider test-file check also found an unchanged
  optional-ModelSource assignment diagnostic in `test_openrouter_accounts.py:82`;
  it is outside this change. No whole-repository type-clean claim is made.
- Strict change validation and all 73 main specs passed. Main spec, rationale
  and Claude operator documentation are synced. `git diff --check` passed.

## Limits of qualification
Mocks prove supported input coverage and protocol/resource lifecycle, not live
OAuth acceptance of every signed/search history or semantic completeness of an
LLM summary. Sending every supported item cannot guarantee every fact survives.
Truly oversized input deliberately fails; old checkpoints cannot restore facts
already omitted by older versions. Native protocol limits and ingress body limits
are unchanged. Production was not contacted or modified for this implementation.
