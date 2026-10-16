## MODIFIED Requirements

### Requirement: On-demand native checkpoint handoff

Only source requests containing an unreadable native checkpoint SHALL trigger
handoff. The proxy MUST authenticate scope and recheck the checkpoint's verified
original model under current access restrictions. Native checkpoints are not
bound to the account that produced them, so the native request SHALL use ordinary
account selection for that model under the key's current account restrictions,
with ordinary failover when an account is paused, limited or exhausted. A
selection failure SHALL return the same error an ordinary native request receives.
The native request SHALL contain that checkpoint and a handoff instruction, no
tools, truncation, continuation handles, client affinity headers or unrelated
conversation data. Its request log SHALL name the destination turn's conversation.
Native handoff SHALL transfer its independent usage settlement and request log to
the existing tracked persistence lifecycle before destination dispatch.
Cancellation MUST close owned upstream work and preserve ownership of pending
persistence cleanup.

Completed, nonempty, nonrefused summary text SHALL replace only the checkpoint;
surrounding messages/tools/images SHALL remain ordered and unchanged. Invalid,
incomplete or refused output, native checkpoint rejections and selection failures
MUST stop preparation without destination dispatch. Portable summaries and normal
native requests MUST NOT generate handoffs.

Handoff summaries and provenance SHALL use bounded private 30-day retention,
without storing the whole conversation. Successful handoffs SHALL be reused across
turns, forked conversations and process restarts for the same authenticated API
key. Valid cached summaries SHALL remain usable after provenance expiry, subject
to current model access restrictions. Concurrent generation for the same key and
checkpoint MUST NOT duplicate native requests. Expired, evicted or corrupt state
MUST NOT produce partial context. Diagnostics MUST NOT include ciphertext, summary
text or conversation content.

#### Scenario: HTTP and WebSocket switch
- **WHEN** an authenticated source request replays a checkpoint with verified native provenance
- **THEN** one eligible native account generates one metered handoff and the destination receives readable summary plus unchanged visible history

#### Scenario: Repeated source turn
- **WHEN** another source request replays a previously handed-off checkpoint
- **THEN** the cached summary is reused without another native request

#### Scenario: Forked source turn
- **WHEN** a forked conversation of the same key replays a previously handed-off checkpoint
- **THEN** the cached summary is reused without another native request

#### Scenario: Concurrent switch
- **WHEN** another worker is generating the same handoff for the same key and checkpoint
- **THEN** the request returns an explicit retryable busy error without duplicate generation

#### Scenario: Owner unavailable or restricted
- **WHEN** generation is required and the producing account is paused, rate-limited, quota-exhausted or outside the key's account scope
- **THEN** another eligible account generates the handoff
- **AND** a key whose model restriction excludes the original model fails with an access error without native or destination dispatch

#### Scenario: No eligible native account
- **WHEN** no account can serve the handoff
- **THEN** the request fails with the error an ordinary native request receives in that state, without destination dispatch

#### Scenario: Replacement rejects the checkpoint
- **WHEN** the serving account rejects the checkpoint with `invalid_encrypted_content`
- **THEN** the rejection reaches the client unchanged, nothing is cached or dispatched to the destination, and the account's health is unchanged

#### Scenario: Handoff log names the conversation
- **WHEN** a handoff is generated for a destination turn that identifies its conversation
- **THEN** the handoff request log carries that conversation ID while the native request carries no client affinity headers

#### Scenario: Invalid handoff output
- **WHEN** the native response is incomplete, refused, malformed or empty
- **THEN** it is not cached as portable context and the destination is not contacted

#### Scenario: Ordinary source request
- **WHEN** the source input is readable or contains a valid proxy summary
- **THEN** no handoff work or extra native usage occurs

#### Scenario: Provenance expired after successful handoff
- **WHEN** a valid handoff summary for the same key outlives its original provenance
- **THEN** it is reused only after checking its recorded model against current key permissions
