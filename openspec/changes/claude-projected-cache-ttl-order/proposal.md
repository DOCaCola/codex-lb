## Why
Modern OAuth instruction relocation can turn valid caller cache order (system
1h, user 5m) into invalid wire order (user 5m, relocated system 1h).

## What Changes
Repair only TTL ordering invalidated by gateway projection, preserving longer
retention and cache metadata. Keep native traffic and invalid caller policies
unchanged. Apply the same policy to Messages and count_tokens.

## Impact
Claude OAuth request projection and its regression tests. No settings or schema
changes, and no changes to token/cost metering.
