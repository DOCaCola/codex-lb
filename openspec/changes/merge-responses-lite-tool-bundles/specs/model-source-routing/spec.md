## ADDED Requirements

### Requirement: Responses Lite tool bundles
Model-source Responses forwarding SHALL merge the tools of `additional_tools` input items into `tools` by the rules of the Claude Responses Lite tool bundles requirement, remove the items from the input and remove the reserved `functions` namespace from recorded calls, because source models are advertised without Responses Lite. A request without bundles or calls under that namespace SHALL be forwarded unchanged. Cache-preserving source compaction SHALL keep the items with the other tool declarations; source compaction without tool declarations SHALL omit them.

#### Scenario: OpenRouter after a Responses Lite model
- **WHEN** a Responses request to a source model carries `additional_tools` items
- **THEN** the source receives their tools in `tools` and no `additional_tools` item
