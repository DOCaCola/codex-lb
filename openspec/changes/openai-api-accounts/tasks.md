## 1. Accounts and catalog

- [x] 1.1 Add the `openai_api_accounts` table, the `source_cooldowns` rename and a single-head migration.
- [x] 1.2 Implement key validation, catalog synchronization, selection projection, scheduled refresh and the
      dashboard API.
- [x] 1.3 Price API-key usage from the API price table.

## 2. Routing

- [x] 2.1 Generalize pooled account selection, cooldowns and failure recording to both API-key providers, with
      billing exhaustion until renewal.
- [x] 2.2 Project the model id, exclude API-key models from Codex routes and retry eligible accounts before delivery.
- [x] 2.3 Serve API-key image models on Codex and `/v1` image routes, with image redirects and their validation.

## 3. Dashboard and verification

- [x] 3.1 Add the OpenAI API account controls, model picker, credit settings and estimate, and the add-account group.
- [x] 3.2 Add backend and frontend tests; run lint, types, migration topology and the affected suites.
