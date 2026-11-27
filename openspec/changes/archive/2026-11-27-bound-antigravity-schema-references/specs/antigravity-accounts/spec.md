## ADDED Requirements

### Requirement: Bounded Antigravity schema reference expansion
Schema material copied out of `$ref` targets while compiling tool schemas SHALL be measured by its UTF-8 size and node count; schemas without references MUST NOT be charged. A tool schema copying more than 256 KiB, or a request whose tool schemas together copy more than 2 MiB or 50,000 nodes, SHALL be rejected as `unsupported_parameter` on the tool that exceeded the limit. Schemas MUST NOT be weakened to fit.

#### Scenario: Shared definition fan-out
- **WHEN** a 30 KB tool schema references a 14 KB enum definition from 400 properties
- **THEN** the request is rejected before it is sent, naming that tool

#### Scenario: Limit spans declarations
- **WHEN** ten tools each copy about 230 KB of referenced definitions
- **THEN** the request is rejected at the tenth tool

#### Scenario: Large schema without references
- **WHEN** a tool declares a 330 KB enum inline without references
- **THEN** it compiles unchanged
