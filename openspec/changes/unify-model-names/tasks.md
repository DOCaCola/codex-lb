## 1. Implementation

- [x] 1.1 Add the `model_display_names` table, repository, cross-replica cached snapshot and migration of existing names
- [x] 1.2 Apply names in the Codex, `/v1` and Anthropic model lists, the dashboard model list and the settings pickers
- [x] 1.3 Add the display-name settings endpoints and list image models in the catalogue
- [x] 1.4 Remove display names from OpenRouter and OpenAI API selections and from model-source models
- [x] 1.5 Rework the catalogue card: search, provider filter and inline name and window editor

## 2. Verification

- [x] 2.1 Integration tests for names, migration, image entries and endpoint errors
- [x] 2.2 Catalogue, picker and model-source editor tests; frontend typecheck, lint and build
- [x] 2.3 Backend suite, ruff, ty, migration topology and strict OpenSpec validation
- [ ] 2.4 Archive after deployment
