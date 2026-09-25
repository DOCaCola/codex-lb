# OpenRouter parameter and error contracts

## Why
Tool support does not imply support for the parallel-tool parameter. Numeric OpenRouter error codes also violate the Codex WebSocket string-code contract and can leave clients waiting. Provider effort ordering is not client picker ordering.

## What Changes
Preserve supported parameters, advertise parallel tools independently, omit unsupported permissive parallel hints but reject unsupported serial requirements. Normalize OpenRouter HTTP errors before they reach clients. Sort reasoning levels by ascending effort without adding levels.

## Impact
OpenRouter catalog projection and forwarding; no native OpenAI changes or deployment.
