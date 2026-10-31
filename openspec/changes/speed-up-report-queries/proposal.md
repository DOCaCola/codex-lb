## Why

The Reports page takes about 6 seconds to load the default 7-day range in production, and every filter change costs
the same because it requests a new report. Two causes account for nearly all of it:

- PostgreSQL JIT compiles the report and rollup queries because the planner overestimates rows for their range joins
  (about 650k estimated versus a few dozen actual). Compilation takes about 0.9 s per rollup query and 1.85 s for the
  speed medians, while execution takes tens of milliseconds.
- The speed-median statement builds separate TTFT, TPS and queue CTEs that each join the report days to
  `request_logs` using only per-day bounds. PostgreSQL cannot derive an index range from them, so it scans the whole
  table three times.

## What Changes

- Asyncpg PostgreSQL connections set `jit=off` in their session settings, next to the UTC time zone.
- Speed medians read request logs once through a single samples CTE that is bounded by the report range's first day
  start and last day end, and derive the three medians from it.

## Impact

- Affected specs: `database-backends`, `reports`
- Affected code: `app/db/session.py`, `app/modules/reports/repository.py`
- Report results are unchanged; only the query plans change.
