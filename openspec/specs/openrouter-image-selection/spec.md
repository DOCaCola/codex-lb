# OpenRouter image selection

## Purpose
Provide separate image model discovery while preserving existing provider selections and routing.

## Requirements

### Requirement: Scoped image selection
OpenRouter account controls SHALL offer separate Models and Image models actions with independent selected counts. Dedicated image metadata SHALL determine image membership; unavailable selections SHALL remain manageable in Models. Read-only and busy restrictions SHALL apply to both actions.

#### Scenario: Image-only discovery
- **WHEN** an operator opens Image models
- **THEN** only entries with dedicated image capabilities are offered, with image pricing and without conversational context controls

### Requirement: Preserve other selections
Saving either picker SHALL preserve selections and settings outside its scope, including entries hidden by search or capability filters. Image selections SHALL retain the existing public Images API routing contract and SHALL NOT change the Codex image model policy.

#### Scenario: Save image changes
- **WHEN** an operator enables Sunburst and saves Image models
- **THEN** previously selected conversational models and their settings remain unchanged

#### Scenario: Save conversational changes
- **WHEN** an operator changes a conversational selection
- **THEN** selected image models remain unchanged
