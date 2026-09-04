## 1. Specification

- [x] Define Astra bootstrap discovery and metadata requirements.

## 2. Implementation

- [x] Add the Astra bootstrap entry and websocket preference pattern.
- [x] Preserve Astra-specific raw catalog metadata without reusing incompatible
      GPT-5.6 defaults.
- [x] Add Astra pricing and suffixed-alias resolution using the existing cost
      model.

## 3. Verification

- [x] Add unit coverage for the registry entry and websocket fallback.
- [x] Add route-level coverage for Codex-native and OpenAI-compatible catalogs.
- [x] Add focused pricing and API-key reservation coverage for Astra.
- [x] Run focused tests, formatting/lint, architecture checks, and strict
      OpenSpec validation.
