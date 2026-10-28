# Drop OpenAI output replay for OpenRouter

## Why
Codex 0.165 requests `output.encrypted_content` from providers named OpenAI and keeps
OpenAI message/tool-call ciphertext in history after model switches. OpenRouter cannot
replay OpenAI-account state, while strict parameter routing could treat the include
value as a required provider capability.

## What Changes
- OpenRouter Responses projection removes the OpenAI output-replay include value and
  non-reasoning item ciphertext.
- OpenAI routing and other include values remain unchanged.
