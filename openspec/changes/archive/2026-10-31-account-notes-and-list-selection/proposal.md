# Account notes and first-entry selection

## Why

Operators want to keep a free-text note on each account, such as who owns it,
what it is reserved for, or when a subscription renews. The dashboard has no
place for that today.

Opening the Accounts page without a selection also picks the wrong account.
The page falls back to the first Codex account in sort order, but the list
mixes all providers in its own order (Claude, Antigravity, Codex, OpenRouter,
OpenAI-compatible, or by name). The highlighted account is therefore often not
the first row.

## What Changes

- Codex accounts and model sources (Claude, Antigravity, OpenRouter and
  OpenAI-compatible accounts) gain an optional plain-text note of up to 2,000
  characters. A dashboard API lists and sets notes, following the chart-colour API.
- Every account detail shows a Note panel under its header. Writers can edit it;
  read-only users see it.
- The account list's row order lives in one function. Without an explicit
  selection, the Accounts page selects the first row that order produces.

## Impact

- Migration adding a nullable `note` column to `accounts` and `model_sources`.
- New `/api/account-notes` endpoints.
- Accounts page selection and all five account detail views.
