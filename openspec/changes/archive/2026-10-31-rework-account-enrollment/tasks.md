## Backend

- [x] Store profile email and organization name on Claude accounts and expose them.
- [x] Hold mismatched Claude reconnects as pending; add confirm and discard endpoints; remove `replaceIdentity`.
- [x] Migration for the new columns and table; tests for hold, confirm, discard, expiry and stale generation.

## Frontend

- [x] Shared link stage, paste field and file area; reuse them in the Codex OAuth and import dialogs.
- [x] Provider sign-in and import dialogs for Claude and Antigravity, including the identity confirmation.
- [x] Re-authenticate menu on Claude and Antigravity details.
- [x] Grouped chooser with provider logos; aligned OpenRouter and OpenAI-compatible dialog header and footer.
- [x] Tests, lint and types; validate the change.
