## MODIFIED Requirements

### Requirement: Messages reasoning controls

`output_config.effort` SHALL pass through as the reasoning effort. Otherwise, an enabled thinking budget SHALL map
to an effort bucket: up to 512 tokens is minimal, up to 1024 low, up to 8192 medium, up to 24576 high, and above that
xhigh. Disabled thinking SHALL map to `none`. Adaptive thinking without an effort SHALL leave effort unset. The
resulting effort SHALL then be projected onto the levels supported by the catalog entry serving the model, taken from
the native model registry or else the enabled source catalog: an unsupported known effort SHALL become the nearest
supported level, the lower one on a tie, with `none` ranked below `minimal`. A model without declared levels and an
unknown effort SHALL keep the requested value. Each projection SHALL log the model and both efforts. Existing
per-model effort normalization and API-key effort policy SHALL apply afterwards. Reasoning summaries SHALL be requested
unless thinking is disabled or its display is omitted.

#### Scenario: Claude Code effort command
- **WHEN** Claude Code sends adaptive thinking with `output_config.effort: high`
- **THEN** the upstream request carries reasoning effort `high`

#### Scenario: Effort above the model's highest level
- **WHEN** Claude Code sends `output_config.effort: max` for a model whose levels end at `xhigh`
- **THEN** the upstream request carries reasoning effort `xhigh`

#### Scenario: Disabled thinking on a model that cannot disable reasoning
- **WHEN** Claude Code disables thinking for a model whose levels do not include `none`
- **THEN** the upstream request carries the model's lowest level without a reasoning summary

#### Scenario: Gap in a source model's levels
- **WHEN** Claude Code sends `output_config.effort: medium` for a source model supporting low, high and max
- **THEN** the upstream request carries reasoning effort `low`
