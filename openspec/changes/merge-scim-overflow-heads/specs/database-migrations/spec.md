## ADDED Requirements

### Requirement: Published SCIM and overflow retirement heads converge
The graph SHALL join the published SCIM and overflow-retirement revisions through a new empty merge revision without modifying either parent. Upgrade from the common parent, either branch or both branches MUST converge on one head and preserve data except for changes required by the existing parent migrations. Downgrading only the merge MUST preserve both parent schemas and stamps.

#### Scenario: Upgrade populated branch
- **WHEN** a database at either published parent upgrades to head
- **THEN** the missing branch executes and existing settings and SCIM tokens survive

#### Scenario: Rollback to pre-branch schema
- **WHEN** an operator downgrades to the common parent using the new build
- **THEN** both branch migrations are undone according to their downgrade implementations
- **AND** unrelated settings remain intact

### Requirement: Timestamp validation recognizes explicit branch repairs
Timestamp collisions among independent revisions MUST remain errors unless all colliding revisions are direct parents of an explicit merge revision. A repaired collision SHALL be a warning, preserving immutable revision IDs. Graph head, connectivity and cycle checks MUST remain enforced.

#### Scenario: Explicit full merge
- **WHEN** a merge revision directly joins every revision in a colliding timestamp group
- **THEN** the checker reports a repaired-collision warning instead of requiring renaming

#### Scenario: Partial merge
- **WHEN** a merge joins only some members of a colliding group
- **THEN** the collision remains an error
