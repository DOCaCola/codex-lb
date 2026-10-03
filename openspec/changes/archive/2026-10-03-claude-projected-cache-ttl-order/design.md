## Policy
Inspect protocol cache controls in tools, system, messages, then automatic
top-level order. Do not recurse into tool arguments/results or embedded data.
If original marker order is valid, promote short ephemeral TTLs before the final
projected 1h marker to 1h. Omitted TTL means 5m. Preserve cache-control fields,
all later short markers, and the caller's original request object.

Native traffic bypasses normalization. Cache-control values are not changed to
repair already-invalid caller ordering. Record an explicit projection transformation and a
content-free diagnostic when TTLs change.

Extending an earlier breakpoint does not introduce a longer-lived prefix than
the later 1h breakpoint already requests. The projection never downgrades 1h.
No new markers, marker trimming, or tool schema/history rewriting is needed.

## Reference
Sub2API PR #7844 (open on 2026-10-03), revision
`da4419e626110c854d356eedfb060b8306f619a8`, reports Anthropic's TTL ordering
refusal and proposes promotion before the last 1h marker. Our triggering cause
is instruction relocation, not its injected cache markers; normalization is
restricted accordingly.
