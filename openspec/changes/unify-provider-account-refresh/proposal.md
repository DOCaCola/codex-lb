# One Refresh action for every provider account

## Why

Each provider's account page offered a differently named refresh: "Check limits"
on Claude and Antigravity, "Refresh balance" on OpenRouter, and "Force probe" on
Codex. The first three fetch the account's metadata without a model request; the
labels described only part of what they fetch (the Claude one also refreshes the
model catalog). Codex had no request-free refresh: Force probe spends quota on a
real request to wake a stuck upstream limiter, then refreshes usage.

## What Changes

- New `POST /api/accounts/{account_id}/refresh` forces the existing usage refresh
  for one Codex account (usage windows, credits and plan) without a model request.
  Paused accounts can refresh; re-auth-required and deactivated accounts cannot.
- Every provider account page shows the same "Refresh" header action with the
  same icon and placement.
- Codex Force probe moves to the account's "More actions" menu, with its existing
  availability rules.

## Impact

Accounts API and service, provider account pages, locales. Force probe behavior
is unchanged.
