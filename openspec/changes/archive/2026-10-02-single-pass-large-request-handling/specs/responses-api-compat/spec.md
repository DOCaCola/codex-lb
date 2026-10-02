# responses-api-compat Delta

## ADDED Requirements

### Requirement: Request bodies are inspected once per body

The proxy MUST decide a request body's account neutrality from the payload while it serializes that body, not by re-parsing the serialized text. A body rewritten only by the account installation stamp MUST take the body verdict of its source and a metadata verdict computed from the stamped `client_metadata`. A body without a recorded verdict MAY be parsed once, and its verdict MUST then be reused for that body. Recorded verdicts MUST NOT keep alive a body the request no longer holds.

The proxy MUST compute a turn's stored-prefix and full input fingerprints from a single canonical encoding pass over the client's input. Both MUST be byte-identical to the fingerprint of the corresponding canonical JSON list.

Installing a retained fresh-replay body MUST NOT change the request's input continuity record, which describes the client's raw input.

#### Scenario: The installation stamp repairs client metadata

- **GIVEN** a built body whose only account-bound field is a blank installation ID in `client_metadata`
- **WHEN** the dispatch stamp writes the account's installation ID
- **THEN** the stamped body is account neutral without being parsed again

#### Scenario: An anchored turn encodes its history once

- **GIVEN** a session anchor whose stored prefix matches the client's input
- **WHEN** the turn is prepared
- **THEN** the prefix check and the request's full fingerprint share one encoding pass
- **AND** both equal the fingerprints the separate computations would produce
