## ADDED Requirements
### Requirement: Provider-specific chart alignment
Shared charts SHALL align equivalent timestamps. Codex measured quota series SHALL
retain upstream interpolation and monthly labels; other provider series SHALL
retain unknown gaps, and request counts SHALL remain non-percentage values.
#### Scenario: Independent provider observations
- **WHEN** Claude or OpenRouter series lack a sample at another series' timestamp
- **THEN** the missing observation remains unknown rather than interpolated
