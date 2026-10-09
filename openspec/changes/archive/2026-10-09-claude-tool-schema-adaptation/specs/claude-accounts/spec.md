## ADDED Requirements

### Requirement: Faithful translated Claude tool schemas
Translated function tools SHALL expose an object input_schema without root oneOf, anyOf or allOf. Ordinary object schemas and nested composition SHALL retain their constraints. Root compositions SHALL use a reversible upstream-only arguments object envelope rather than lossy property merging. Local JSON-pointer references SHALL remain bound to the original schema after relocation. Schemas requiring relocation with unsupported reference scopes, malformed structure or exhausted adaptation budgets SHALL fail before dispatch with the caller-visible tool identity and tools parameter path, without omitting tools or replacing their schema with an unconstrained object.

Completed function arguments SHALL be unwrapped before public Responses output, including HTTP and WebSocket projection. Wrapped argument deltas SHALL remain private until a complete valid envelope is available, then emit original-shape arguments before done. Malformed or oversized envelopes and incomplete JSON MUST NOT be reported as successful tool calls. History SHALL be projected using the current tool declaration's codec; logical replay SHALL retain original client arguments. Tool identity, namespace, choice, call IDs and result pairing SHALL remain stable. Native Messages forwarding SHALL remain outside this translated-schema change.

#### Scenario: Mode-specific tool
- **WHEN** a namespaced function uses root oneOf with different required fields per mode
- **THEN** Claude receives both complete alternatives beneath arguments and Codex receives the unwrapped selected mode

#### Scenario: Fragmented arguments
- **WHEN** a wrapped tool input arrives in partial JSON chunks
- **THEN** no wrapper bytes reach public argument deltas and delta/done/final output agree

#### Scenario: Follow-up history
- **WHEN** the client returns a tool result with its original-shape call history
- **THEN** the adapter encodes that call once according to the current declaration without changing the client history

#### Scenario: Local references
- **WHEN** the original schema references a local definition or its root
- **THEN** relocated references target that original subschema, not the new envelope

#### Scenario: Unsupported reference scope
- **WHEN** adaptation encounters an external reference or a nested schema identifier that cannot safely be relocated
- **THEN** it fails locally naming the tool rather than weakening the contract
