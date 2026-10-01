# Provider observability context

This extends the existing Reports and Conversation Details surfaces. There is no
second sessions page or new content store. Metadata aggregates read existing
request logs through bounded SQL queries; they do not load message history.

## Routing explanations

Reasons originate in eligibility checks and explicit OpenRouter refusals, after
authorization and ownership restriction. Public errors contain sorted category
counts rather than account IDs. Mixed paused/cooldown pools do not claim all
accounts are paused. Uniform native-pool and authorization errors retain their
specific wording. Upstream refusal statuses and Retry-After remain authoritative;
neither routing ranking nor failover eligibility changes.

For example, a paused account and a cooling account can return
`Routing exclusions (cooldown: 1, paused: 1; known recovery: ...)` without exposing
either account's identity. Recovery timestamps report known eligibility deadlines,
not a guarantee of successful inference after that time.

## Measurement semantics

Claude input tokens already include cache reads and writes. A request with
1,000 total input and 800 cached tokens contributes an 80% cache-read ratio, not
800 divided by an input value that adds those tokens a second time. Complete
cache observations require valid input, read and write measurements; missing or
inconsistent measurements contribute only to successful-request coverage. A real
zero cache observation is not missing. Current and previous rolling-hour windows
ignore Reports filters and exclude internal/deleted/non-generation requests.
Ratios vary by workload; no universal hit-rate target or automatic health claim.

Conversation totals retain lifetime scope. New activity, errors, cancellations,
cache writes and speeds cover the latest seven days ending at the last request.
Speed means include only successful generation requests with real measurements;
unknowns remain null and sample counts are exposed. TPS follows the existing
Reports visible-output convention, including its OpenRouter duration floor.
Cache-write coverage is displayed separately. Source and subscription IDs occupy
distinct counting namespaces. Cost coverage and cost displays are unchanged.

## Reference and qualification

Inspected aneym/agent-lb `c7f83276e4c8af0d7735adb6524fc68d34a97732`
on 2026-10-01 (MIT). Its selection diagnostics, cache observations and session
analytics informed this integration; source was not copied wholesale. Local
integration and browser tests use synthetic accounts and traffic. They do not
qualify live provider acceptance, billing or a particular cache-hit ratio.

Timed pause/resume, credential federation, watchdog probes, a status CLI and
additional transcript retention are outside this change.
