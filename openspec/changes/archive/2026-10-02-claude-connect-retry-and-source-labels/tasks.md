## Implementation
- [x] Mark pre-dispatch connection failures on forwarding errors (excluding TLS).
- [x] Retry pre-dispatch Claude failures on the same account within the shared budget and recovery window.
- [x] Name the serving provider in model-source error messages.
- [x] Test retry, no-retry boundaries and wording; validate lint, typing and specs.

Verification: 1764 Claude, OpenRouter, model-source and network-recovery tests passed,
including the new DNS, refused, TLS and after-dispatch cases on all three Claude entry
paths. Ruff, formatting, ty, strict change validation and all 75 main specs passed.
Not deployed.
