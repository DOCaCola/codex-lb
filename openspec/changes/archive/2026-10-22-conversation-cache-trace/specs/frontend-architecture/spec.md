## ADDED Requirements

### Requirement: Conversation request trace

The authenticated dashboard MUST expose `GET /api/request-logs/conversation-trace` with `conversationId`, `limit`
(1–200, default 50) and `offset`, guarded by conversation read permission. It MUST use the conversation detail
eligible-row scope, order rows by `requested_at` then ID, newest first, and return 404 for an unknown conversation.
Each row MUST expose time, model, effort, request kind and operation, status, error code, latency, first-token
latency, prompt tokens, clamped cache reads, cache writes, output tokens, cache-read ratio, cache event and idle gap.
It MUST NOT expose account identity.

A row whose prompt exceeds its cache reads by more than 20,000 tokens SHALL carry the first matching event, compared
with the previous row that carries a prompt: `first` without one; `compaction` when either is a compaction;
`model_switch`; `account_switch` when account or model source differs; `idle_expiry` when the gap from the previous
request's end exceeds 5 minutes, or 1 hour when the row wrote to the 1-hour cache; `bust` when reads are below 10% of
the previous prompt and the prompt is 0.95–1.2 times it; `growth` when reads are at least 90% of it; otherwise
`miss`. The previous row of a page's oldest row MUST be loaded so classification does not depend on pagination.

Conversation Details SHALL show the trace below the model table as a timeline: elapsed-time bar relative to the
longest loaded request, coloured by cache-read share (at least 80%, at least 30%, below, unmeasured), event tag with
its explanation, error code for failed rows, and a control to load further pages.

#### Scenario: A conversation resumes after its cache expired
- **WHEN** a request follows the previous one by 40 minutes on the same model and account and reads none of its
  120K-token prompt from the 5-minute cache
- **THEN** its trace row carries `idle_expiry` with the idle gap
- **AND** Conversation Details shows it with the low cache band and an "idle expiry" tag

#### Scenario: Paging the trace
- **WHEN** a conversation has more rows than one page
- **THEN** the first page holds the newest rows and `hasMore` is true
- **AND** the oldest row on the page is classified against the newest older row

#### Scenario: Guests cannot read the trace
- **WHEN** a dashboard user without conversation read permission requests the trace
- **THEN** the response is 403
