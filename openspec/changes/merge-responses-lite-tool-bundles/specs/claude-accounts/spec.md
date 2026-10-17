## ADDED Requirements

### Requirement: Responses Lite tool bundles
Translated Claude Responses SHALL declare the tools of `additional_tools` input items after the top-level tools, in history order. A tool already declared by the top-level tools or an earlier bundle MUST NOT be declared again; same-named namespaces SHALL merge their members, and nameless hosted tools SHALL be identified by type. The items SHALL NOT become conversation content. Tools declared or called under the reserved `functions` namespace SHALL be the tools of the same name without a namespace. An item without a tools array MUST fail explicitly.

#### Scenario: Switch from a Responses Lite model
- **WHEN** a request to a Claude model carries top-level tools and `additional_tools` items recorded by a Responses Lite model
- **THEN** Claude receives the top-level declarations followed by the bundled tools they did not declare, and no message for the items

#### Scenario: Lite-era call
- **WHEN** history contains a call recorded under the `functions` namespace
- **THEN** it is projected as a call of the tool of that name without a namespace

#### Scenario: Request without bundles
- **WHEN** a request carries no `additional_tools` item
- **THEN** its tool declarations are unchanged
