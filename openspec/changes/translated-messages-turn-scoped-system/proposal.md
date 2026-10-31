## Why

Claude Code sends its reminders as `role: "system"` messages with `clear_at: "next_user_message"` and re-sends them
unchanged on every later request. Anthropic renders such a message only while no `role: "user"` message follows it;
afterwards it stays in the array but is no longer shown to the model. Translated Messages requests to OpenAI,
OpenRouter and Antigravity models currently forward every reminder as a permanent developer message, so expired
reminders accumulate in the prompt and the model keeps reading guidance meant for an earlier turn.

No reference drops expired turn-scoped messages on a translated path: CLIProxyAPI and opencodex read `clear_at` only
on native Anthropic passthrough. Claude Code itself stops re-sending earlier reminders when the server refuses
`clear_at`, which confirms the intended lifetime.

## What Changes

- A message-level system message with `clear_at: "next_user_message"` is omitted from the translated input once any
  later `role: "user"` message exists, including one that carries only tool results.
- A `clear_at` value other than `"next_user_message"` or `"never"` fails before dispatch with
  `invalid_request_error`, as Anthropic refuses it.

## Impact

- Affected specs: `messages-api-compat`
- Affected code: `app/core/messages/translate.py`
- The prompt prefix changes where a reminder expires, once per reminder, as it does on Anthropic.
