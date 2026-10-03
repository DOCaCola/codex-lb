## Verification

Unit tests cover omitted/explicit 5m markers, caller cache metadata, later short
markers, original-body immutability, repeated projection, native passthrough,
invalid original TTL ordering/values, automatic top-level policy and opaque tool
input. Route tests inspect actual prepared upstream payloads for streaming
Messages and JSON count_tokens, with native and non-native profiles.

Both endpoint tests reproduce the original valid system-1h/user-5m fixture.
Non-native projection emits user-1h/relocated-system-1h; native requests keep
system-1h/user-5m. The normalization diagnostic contains only the source ID.

The relevant regression suites pass: 205 tests. Changed-file lint/format checks,
strict change validation and all 75 main
OpenSpec validations pass. Type checking retains the existing 598 diagnostics.
No paid upstream call or production configuration change was made for this fix.
