# Tasks

## 1. Collection trend data

- [x] 1.1 Refactor the shared rollup/raw trend reader and add typed collection contracts; verify integration tests prove individual/collection parity, partial boundaries, exclusions, deleted usage, coverage, and permission enforcement.
- [x] 1.2 Add the collection route and window metadata; verify canonical and trailing-slash URL forms return equivalent payloads with one shared timeline.

## 2. Overview chart

- [x] 2.1 Add collection query, multi-series transformations, metric/mode controls and legend in the existing overview layout; verify frontend tests cover ranking, Other aggregation, cumulative totals, unknown/free distinctions and interaction.
- [x] 2.2 Add localized labels and explicit loading/empty/error states; verify type checking and targeted lint succeed.

## 3. Integration verification and documentation

- [x] 3.1 Exercise the complete APIs page with mocked collection data on desktop/mobile and inspect screenshots, toggles, legend and page overflow.
- [x] 3.2 Sync the verified requirements/context into the main API-key spec and run strict change/spec validation; record verification evidence.
