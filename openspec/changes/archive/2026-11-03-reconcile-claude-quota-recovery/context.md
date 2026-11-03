# Evidence and design

2026-11-03: inference rejected five-hour quota at 10:24:52 UTC. After a confirmed
Pro-to-Max upgrade, a manual usage read at 10:25:59 reported five-hour 0% and weekly
34%. The older cooldown continued blocking until 11:40 UTC.

Reference: OpenCodex issue #6989 and merged PR #7009; inspected 2026-11-03 at
684ad75d. Its recovery captures a refusal before fresh dispatch and preserves
newer refusals and changed credentials. We use existing per-restriction evidence
and account transaction locking rather than introducing another generation store.

https://github.com/lidge-jun/opencodex/issues/6989
https://github.com/lidge-jun/opencodex/pull/7009

Only explicit readings accepted as current can recover a restriction. Each
restriction is independent: clearing five-hour evidence leaves weekly exhaustion
and model entitlement restrictions intact. A successful usage read does not
constitute a reset grant and does not update manual reset barriers.
