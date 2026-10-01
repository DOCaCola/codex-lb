# Design

## Context

See proposal.md for the observed 23 ms production window. OpenRouter already uses an estimated inclusive-output metric and a one-second floor, while Claude still uses native non-reasoning semantics and no floor. Reports and conversation analytics duplicate these calculations.

## Goals / Non-Goals

Use one backend expression and a matching frontend contract for provider-specific throughput. Preserve raw usage, monotonic attempt timing, routing and client bytes. Do not add a replacement end-to-end rate, fabricated reasoning counts, timing clamps, a schema migration or a configurable threshold.

## Decisions

- Claude and OpenRouter TPS uses total reported output divided by the observed window after first content. Display it as an estimate; require success, nonnegative TTFT, positive output and at least 1000 ms. Inclusive Claude output can include unreported reasoning, so subtracting an unknown or partial reasoning count would imply precision we do not have.
- Extract the repeated backend expression into core usage logic. Reports retains existing native sample eligibility; conversation analytics retains its successful-generation filter. Native output-minus-reasoning semantics stay unchanged.
- Observe nonempty redacted_thinking data and thinking signature output at the native SSE timing seam. They prove opaque output arrived, not its token count or the provider's actual generation start. Never count pings, lifecycle events, empty containers or terminal events as output.
- Extend existing request TPS explanations to Claude; aggregates explain their estimated gateway samples in existing descriptive/tooltip surfaces rather than expanding API schemas or charts.
- Correct historical rows at read time; do not reinterpret or rewrite stored timings.

## Risks / Trade-offs

- Buffered output can distort even longer windows: the one-second floor removes the most unstable values, not all network effects. Gateway rates always remain estimates.
- Opaque output can arrive only after hidden reasoning finishes: detecting it cannot reconstruct missing upstream timings.
- Short genuine answers lose a TPS value; TTFT, elapsed time, tokens and costs remain available.

## References

Inspected October 1, 2026: OpenCodex ef0297f86c4540c7d757c8595170d66f9c584aec, src/server/management/shared.ts (one-second minimum and estimated decode rate); OmniRoute dbe703a0000b303cd7b1cf5879cb8740e5bfce71 (no short-window floor); CLIProxyAPI fd48ea6840f5572deb53aeb5657740937ac9daaa (signature event detection); Agent LB c7f83276e4c8af0d7735adb6524fc68d34a97732 (no comparable native Claude TPS). No third-party code is copied.

## Migration Plan

Normal application deployment is sufficient after verification. No database or production changes are part of implementation. Rollback restores previous derived displays; recorded usage and timing remain intact.
