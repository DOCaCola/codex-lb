## Boundary
ResponsesCompactRequest validation is structural. Native to_payload serialization
remains the native OpenAI compact contract and retains its existing reduction.
Source summarization uses the validated model dump, materializes private
continuation first and constructs a tool-free stateless Responses request.
Terminal request construction must not invoke native serialization; native
dispatch retains its early native validation explicitly at that boundary.

## Complete input, bounded execution
Remove the unconditional image replacement. Keep source history item order and
content, apart from control-only additional_tools/compaction_trigger items and
explicit lowering of readable proxy checkpoints. Namespace and signed-resource
handling use the existing provider translator/ownership path. Compaction marks
all authenticated Claude signed blocks as hard owners (even completed thinking)
and disables lossy historical-signature recovery. Conflicting owners, unavailable
owners or a model mismatch fail rather than discarding signed blocks. Ordinary
Responses and native Messages recovery are unchanged. Unsupported
or incomplete active tool state fails explicitly rather than being fabricated.

The summarization contract's history/instructions, disabled truncation, tool-free
format and stateless continuation fields are protected against per-model source
request overrides. Compatible generation overrides remain available.

Set truncation=disabled on the summarization request. The provider enforces its
actual capacity: do not introduce a JSON-character preflight that incorrectly
counts inline image bytes as text tokens or confuse the conservative client
working context with provider capacity. Context/size errors flow through the
existing logged dispatch, cleanup and reservation settlement. No smaller-history
retry, alternate compaction model or staged calls are added. Summary validation
and checkpoint creation remain after complete successful generation.

## Reference evidence
OpenCodex at 5ab6d52b2a4da722d398e4ab50a6c621ac3ce087 sends parsed history to
the routed summarizer and exempts compaction from ordinary context admission.
Its merged #6175 older-image omission is explicitly heuristic; we retain images
instead. OmniRoute's destructive compression is unsuitable, CLIProxyAPI Claude
Responses compact is unsupported, and no complete staged Claude adapter was
verified in Sub2API. This implementation is original, not a source-code copy.

Sending complete input does not guarantee semantic retention of every detail by
the model. A short summary is not an error by itself. Old checkpoints cannot
reconstruct items already omitted by older versions.

## Verification
Exercise large-history earliest/middle/latest facts, large tool results, images,
resolved previous IDs, dedicated compact endpoints and actual WS terminal
triggers followed by continuation. Prove capacity/incomplete failures emit no
checkpoint, do not mutate retained history and settle/release dispatch state.
Run native compact regressions to preserve upstream behavior.
