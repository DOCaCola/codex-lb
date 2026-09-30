# Spec Delta

## MODIFIED Requirements

### Requirement: Verified readable native checkpoint recovery

After successful settled native compaction, the proxy SHALL retain scoped,
digest-bound original model/account provenance without copying the conversation
or native ciphertext. Previously retained complete readable snapshots SHALL remain
usable while valid. Native requests and compaction results MUST remain unchanged.
Source preparation SHALL first use valid readable recovery before requesting a
handoff. Missing or cross-scope provenance MUST NOT cause guessed-owner dispatch.

Existing readable snapshot restoration SHALL preserve complete ordered semantic
input. An exact recorded compact replacement prefix SHALL be removed only when it
directly precedes its checkpoint. Repeated user turns MUST NOT be deduplicated by
content alone. Recovery diagnostics MUST contain only request identity and
aggregate counts or bounded reasons.

#### Scenario: Normal native compaction
- **WHEN** native compaction succeeds, including with older opaque history
- **THEN** only checkpoint provenance is captured and no summary request is made

#### Scenario: Available readable recovery
- **WHEN** source preparation finds a valid scoped readable checkpoint snapshot
- **THEN** it restores that input without additional native generation

#### Scenario: Unknown legacy checkpoint
- **WHEN** a checkpoint has neither readable recovery, a valid handoff summary nor verified provenance
- **THEN** preparation fails at its original input index without dropping history

#### Scenario: Exact compact replacement prefix
- **WHEN** a source replays the exact preserved-message prefix returned with a retained checkpoint
- **THEN** recovery includes those messages once and leaves unrelated repeated turns intact

#### Scenario: Native and failed compact behavior
- **WHEN** native compaction succeeds or fails
- **THEN** its existing wire result and settlement are unchanged and failed compaction does not seed recovery

## ADDED Requirements

### Requirement: On-demand native checkpoint handoff

Only source requests containing an unreadable native checkpoint SHALL trigger
handoff. The proxy MUST authenticate scope and use the checkpoint's verified
original model/account under current access restrictions. The native request
SHALL contain that checkpoint and a handoff instruction, no tools, truncation,
continuation handles or unrelated conversation data. Account reselection MUST NOT
move handoff to another account. Native handoff SHALL transfer its independent
usage settlement and request log to the existing tracked persistence lifecycle
before destination dispatch. Cancellation MUST close owned upstream work and
preserve ownership of pending persistence cleanup.

Completed, nonempty, nonrefused summary text SHALL replace only the checkpoint;
surrounding messages/tools/images SHALL remain ordered and unchanged. Invalid,
incomplete or refused output and native owner/model errors MUST stop preparation
without destination dispatch. Portable summaries and normal native requests MUST
NOT generate handoffs.

Handoff summaries and provenance SHALL use bounded private 30-day retention,
without storing the whole conversation. Successful handoffs SHALL be reused across
turns and process restarts within the same authenticated conversation. Valid cached
summaries SHALL remain usable after provenance expiry, subject to current access
restrictions. Concurrent generation for the same checkpoint MUST NOT duplicate
native requests. Expired, evicted or corrupt state MUST NOT produce partial
context. Diagnostics MUST NOT include ciphertext, summary text or conversation
content.

#### Scenario: HTTP and WebSocket switch
- **WHEN** an authenticated source request replays a checkpoint with verified native provenance
- **THEN** its original account generates one metered handoff and the destination receives readable summary plus unchanged visible history

#### Scenario: Repeated source turn
- **WHEN** another source request replays a previously handed-off checkpoint
- **THEN** the cached summary is reused without another native request

#### Scenario: Concurrent switch
- **WHEN** another worker is generating the same scoped handoff
- **THEN** the request returns an explicit retryable busy error without duplicate generation

#### Scenario: Owner unavailable or restricted
- **WHEN** generation is required and the original account/model is unavailable or excluded by current API-key policy
- **THEN** handoff fails without account failover or destination dispatch

#### Scenario: Invalid handoff output
- **WHEN** the native response is incomplete, refused, malformed or empty
- **THEN** it is not cached as portable context and the destination is not contacted

#### Scenario: Ordinary source request
- **WHEN** the source input is readable or contains a valid proxy summary
- **THEN** no handoff work or extra native usage occurs

#### Scenario: Provenance expired after successful handoff
- **WHEN** a valid scoped handoff summary outlives its original provenance
- **THEN** it is reused only after checking its recorded model/account against current key permissions
