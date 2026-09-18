## Why
Upstream published two independent migration heads at the same timestamp. Startup cannot resolve head; published IDs must remain stable.

## What Changes
- Add an empty merge revision joining SCIM and retired-overflow removal.
- Recognize directly merged historical timestamp collisions as warnings, without relaxing unresolved-fork checks.
- Verify upgrade from the common parent and either/both branches, merge-only downgrades and schema rollback.

## Impact
Migration graph and author-time validation only. Existing parent DDL remains unchanged. Image-only rollback across overflow removal is unsafe.
