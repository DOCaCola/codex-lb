# Tasks

## 1. Endpoint

- [x] 1.1 Serve the capability document under `/backend-api/codex` and `/v1`, behind proxy API-key authentication.
- [x] 1.2 List each capability with its models; limit `composer_predictions` to the key's native subscription models.

## 2. Prediction attribution

- [x] 2.1 Label Responses turns whose Codex turn metadata declares `thread_source` `composer_predictions` as
  `composer_prediction` over HTTP and WebSocket; compaction takes precedence.
- [x] 2.2 Show the operation as "Prediction" in the dashboard request log.

## 3. Verification

- [x] 3.1 Integration tests: both paths return the document; API-key authentication is enforced when enabled;
  routed source models are excluded; the key's model allowlist applies.
- [x] 3.2 Prediction labelling over HTTP and WebSocket, per turn, with compaction precedence.
- [x] 3.3 Full test suite, ruff, ty and `openspec validate --strict`.
