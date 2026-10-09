## ADDED Requirements
### Requirement: Fork and upstream migration convergence
The fork SHALL preserve published upstream and fork migration identities and
join their current heads through a new no-op merge revision.
#### Scenario: Existing fork database
- **WHEN** a database at the deployed fork routing revision upgrades
- **THEN** it reaches one common head without reapplying shared ancestor migrations
