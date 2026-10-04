# Share the weekly plan line between Codex and Claude

## Why
The Claude weekly plan line was computed by a separate implementation that broke the line whenever the
recorded reset deadline changed. Claude's usage endpoint reports the same deadline with sub-second jitter
(e.g. 21:59:59.6 and 22:00:00.505), so whole-second rounding still flips between adjacent seconds. In
production one weekly cycle produced about 55 flips and the plan line rendered as 60 fragments, while the
Codex plan line stays continuous.

## What Changes
- One shared plan-line builder in `app/core/usage/pacing.py` used by both Codex and Claude: hourly buckets,
  each bucket's latest reset deadline carried forward, starting at the first known deadline.
- Claude no longer breaks the line on deadline changes or blanks it after expiry; a new cycle appears as
  the jump back toward 100%, as on Codex.

## Impact
Claude trend API weekly plan points become hourly. No persistence, routing or frontend changes.
