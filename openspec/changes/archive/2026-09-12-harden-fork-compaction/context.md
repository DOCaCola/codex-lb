# History safety and dispatch ownership

Source compaction is a new summarization turn, not the native provider's private compaction API. The source cannot resolve a native previous-response ID or decrypt its checkpoint. The current replay store only proves history for scoped HTTP-fallback WebSocket turns, so it is not a general materializer for this HTTP route. Reject unresolved handles rather than claiming a context-free summary is complete.

For example, a terminal trigger with previous_response_id=resp_old and no retained input receives a 400 asking for complete materialized history. A readable clb1 checkpoint remains portable; a native opaque checkpoint can still go to its original native provider unchanged.

Overflow uses the same synthetic compaction helper and passes its existing dispatch context and admission claims through the normal source owner. Validation occurs before reservations; the overflow helper releases any unowned claims on rejection. Once transferred, the source owner remains responsible for settlement and release.

store=false controls storage of the newly generated response. It does not invalidate an explicit reference to an item persisted by a previous response.

## Verification

- 1,899 compaction, replay, transport, routing, overflow and proxy regression tests passed.
- 84 additional source-dispatch and native-compact integration tests passed.
- Full ty check and scoped Ruff lint/format checks passed.
- All 65 canonical OpenSpec specifications and both changed change specifications validated strictly.
- No commit, push or production deployment performed.
