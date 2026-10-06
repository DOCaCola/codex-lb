## Implementation
- [x] Advertise `multi_agent_version: "v2"` in the Claude catalog projection; cover Claude and non-Claude sources in catalog tests.
- [x] Lower `agent_message` content without an added header; update `tests/unit/test_subagent_messages.py` and the Claude translation tests that assert the header.
- [x] Add one deterministic hosted-search text renderer for Claude call/result blocks and OpenAI `web_search_call` actions (search, open_page, find_in_page; sources when present).
- [x] In `project_native_replay`, omit authenticated redacted thinking and replace an authenticated search envelope and its matching `web_search_call` with the rendered message. Log `redacted_omitted` and `search_projected`. Update `tests/unit/test_native_provider_history.py` and `tests/integration/test_native_provider_history.py`, which currently expect `nonportable_provider_history`.
- [x] In Claude dispatch, project OpenAI `web_search_call` items that no authenticated Claude search envelope claims, in completed and active turns, keeping input positions stable. Remove the resulting "account-bound opaque state" failure for them.
- [x] Make completed Claude search non-strict in `authenticate_replay`, and project it in `ClaudeReplay.project` when the model or account differs, including compaction. Active-turn search stays strict. Cover model switch, unavailable owner, external task boundary and active tool cycle.
- [x] Record the reference survey and the text-versus-structured decision in `openspec/specs/claude-accounts/context.md`, replacing the "not portable native state" paragraph.
- [x] Run the lab case "full-history forks" from design.md, mocks only, on stock and fork 0.160.1, and record the results, including where Codex places the child's task.
- [x] Validate catalog, subagent-message and Claude translation suites, lint, typing and strict OpenSpec validation.
