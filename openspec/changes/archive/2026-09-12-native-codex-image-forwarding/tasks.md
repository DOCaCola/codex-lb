## Implementation
- [x] Separate Codex image routes from public Images adapters.
- [x] Add native transport and account lifecycle with no post-dispatch replay.
- [x] Preserve API-key admission, settlement and response metadata.
## Verification
- [x] Test native success, errors, auth/scoping, cancellation and transport behavior; retain public adapter regressions.
- [x] Run lint, typing and strict specification validation; synchronize main specifications.

## Evidence
- Images, native transport, routed upstream paths, and Daybreak routes: 317 passed.
- Existing control utilities: 6 passed; settlement, image middleware, extended API and realtime: 185 passed.
- Final native/policy/settings-reference subset: 44 passed.
- make lint, ty check, git diff --check: clean; all 65 specifications passed strict validation.
- No live image generation, deployment, commit, or push performed.
