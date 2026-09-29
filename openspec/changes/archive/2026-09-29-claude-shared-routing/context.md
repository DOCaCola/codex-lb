# Shared policy, separate provider pools

Claude models select only enabled, authorized Claude accounts. Codex/OpenAI
models retain their existing pool and capacity estimates. Sharing a policy does
not share credentials, quotas, cooldowns, affinity or resource ownership.

Claude supplies one normalized capacity unit per account. Shared fresh five-hour
and weekly observations determine the known-data cohort for quota strategies;
fresh applicable model-family weekly pressure can raise the weekly bottleneck.
When no candidate has complete fresh shared windows, the cohort is explicitly
neutral. Stale exhaustion still blocks through the existing eligibility layer.
Unknown usage is never persisted or displayed as observed zero.

For example, relative availability with top-k one prefers an unbound Claude
account with 80% remaining and reset in two hours over an otherwise equivalent
account with 20% remaining and reset in twenty hours. Eligible retained affinity
or a hard resource owner takes precedence. A new weighted draw is not seeded;
durable admission-time affinity stabilizes subsequent native and translated turns.

Single-account mode uses independent OpenAI and Claude targets. A missing,
unauthorized or unavailable Claude target fails explicitly, rather than selecting
an OpenAI account or silently guessing another Claude account. OpenRouter is not
included in this scheduling change.

Admission timestamps persist for round-robin. They are recency hints, not an
atomic global scheduling lock: concurrent selections may choose the same account;
existing atomic per-worker concurrency admission remains the capacity authority.
No RPM/session-count limits or inferred Claude plan-capacity multipliers are added.
Checks use isolated databases and mocked upstream traffic, not live OAuth billing
qualification. No production changes are part of this implementation.
