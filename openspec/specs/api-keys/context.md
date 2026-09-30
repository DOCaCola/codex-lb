# API Keys Context

See `openspec/specs/api-keys/spec.md` for normative requirements.

## Seven-day comparison overview

The APIs page compares downstream API keys, independently of their upstream account/provider assignments. The full-width recent trend sits between lifetime summary statistics and lifetime share panels, so recent behavior and all-time totals remain distinct.

The collection trend reader shares the individual-key watermark partition: whole folded hours come from hourly summaries, and the exact raw complement supplies partial boundary hours and the unfurled tail. After retention prunes raw edges, the existing reader can undercount up to one partial bucket per unaligned edge. This is the same limitation as individual-key trends. Unauthenticated traffic is excluded; retained IDs that no longer exist in the key inventory are combined anonymously as Deleted keys.

Cost is recorded estimated API cost, not subscription charges. Tokens match individual-key accounting: input plus output, using reasoning only when output is absent. The chart shows the five largest series for the selected measure and sums the rest into Other. For example, seven keys with hourly costs 7, 6, 5, 4, 3, 2 and 1 produce five individual bands and an Other band worth 3. Ranking occurs before legend filtering so hiding a key does not promote another; a hidden individual key also stays excluded if a measure switch moves it into Other.

Hourly areas show usage in each hour; cumulative lines sum only the current seven-day window. Cost-coverage counts accumulate alongside dollars. Unknown-only cost points are gaps and tooltips say Unknown; a priced free request is zero. Known subtotals keep compact currency formatting, with a brief tooltip notice for incomplete coverage. Controls transform the same response locally, without additional requests. The query refreshes every five minutes and is invalidated by key mutations; errors offer an explicit retry.

## Request-aware reservation estimate

The admission budget for token and `cost_usd` limits (Requirement
"Request-aware API-key usage reservations") sizes the input side from the
forwarded request payload: `min(utf8_length(serialized_payload_minus_caps), 8192)`.
Two implementation notes keep that value exact while avoiding redundant work on
the hot path:

- **Shared dump.** `ResponsesRequest.to_payload()` is deterministic, so the
  HTTP bridge prepare path computes it once and threads the same dict through
  client-metadata derivation, the forwarded `response.create` frame and
  `estimate_api_key_request_usage(payload, upstream_payload=...)`. The budget,
  frame bytes and input fingerprints are byte-identical to computing each stage
  from its own dump. When the prepare path rewrites the request (replayed
  side-effect tool-call dedupe under `previous_response_id`) the caller's dump
  is discarded and recomputed from the rewritten request, so the forwarded
  frame never carries un-deduped input. Callers that do not hold a dump keep
  the default single-argument form.
- **Early-exit serialization.** Because the estimate is capped at 8192 bytes,
  the estimator returns the cap as soon as it is proven: an `instructions`
  string of 8192+ characters alone suffices (a JSON string literal is never
  shorter than its character count), otherwise the payload is streamed through
  the same `sort_keys`/`ensure_ascii=False` encoder and stopped once 8192 bytes
  have been produced. Sub-cap payloads still yield the exact serialized length.
  The opaque-context checks (`previous_response_id`, `conversation`, file or
  image references) run before either shortcut, so the conservative `None`
  budget is unchanged.

Edge: a lone surrogate (`"\ud800"`) anywhere in the payload used to raise
`UnicodeEncodeError` (HTTP 500) from the full dump. It now raises only when it
sits in a chunk that is actually UTF-8 encoded, i.e. within the first ~8 KiB of
serialized output and not inside a string literal that the length shortcuts
(`instructions` >= 8192 chars, or a single chunk that alone covers the
remaining budget) prove the cap without encoding. Surrogates skipped that way
yield the 8192 cap like any other large payload.
