# Tasks

## 1. Translated continuation

- [x] 1.1 Preserve assistant-tail input with a wire-only continuation after tool validation; verify text, reasoning, signed history, user/result endings, and missing-result unit/public-route tests.

## 2. Structured failure delivery

- [x] 2.1 Serialize forwarding errors after shared Responses settlement; verify original failure logging, release/cleanup, HTTP error events, same-socket recovery and cancellation regression tests.
- [x] 2.2 Add bounded undeclared-tool identity diagnostics while retaining strict declaration validation; verify safe/unsafe names and absence of arguments/content in logs.

## 3. Integration verification

- [x] 3.1 Sync specs/context, run relevant Claude/source regressions, lint/type/seam checks and strict spec validation; document results without deploying production.
