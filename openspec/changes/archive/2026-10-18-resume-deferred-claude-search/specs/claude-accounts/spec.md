## MODIFIED Requirements

### Requirement: Codex protocol adaptation
Claude SHALL support Responses over downstream HTTP and WebSocket while using HTTPS/SSE upstream. Translation MUST preserve portable text, tool/custom-tool/namespace, image, reasoning and cache-usage semantics, or reject unsupported semantics explicitly. A custom tool with a lark or regex grammar format SHALL be projected as a single raw-text input whose description carries the grammar; the client remains responsible for validating that input. Claude catalog models SHALL advertise the freeform patch tool type. Truncation, `model_context_window_exceeded` and pause_turn MUST NOT become completed; they SHALL surface as incomplete with reason max_output_tokens. A refusal stop reason MUST NOT become completed or incomplete; for every translated projection it SHALL fail as `response.failed` with error code `invalid_prompt` and a message naming the refusal category and Claude's explanation, preserving usage, so clients end the turn without retrying. Non-streaming translated Responses and Chat SHALL return HTTP 400 `invalid_request_error` with that error, and streaming Chat SHALL emit it as an error event; refused output SHALL follow the refused-output requirement. A refusal MAY end the stream while content blocks or search calls are still open; that partial output SHALL be discarded: it MUST NOT receive done events and MUST NOT appear in the terminal output or continuation history, so an unfinished tool call is never delivered as executable or replayed without a result. Native passthrough SHALL forward such a refusal unchanged and record it as an incomplete terminal. A tool_use stop whose response contains a client tool call SHALL defer its pending search calls as the translated hosted web search requirement defines. Any other stop with open content, pending search calls or no stop reason SHALL fail with a message naming the open block types, pending search count and stop reason. Each translated message stop, including a malformed one logged with status `invalid`, SHALL log its stop reason, resulting status, upstream content block type counts, output tokens, a bounded refusal category when Claude supplies one, the withheld item count and whether output was delivered, never content, reasoning, tool input, signatures or refusal explanations. A Claude transport failure SHALL name its exception class. Durable continuation MUST be persisted before terminal delivery and scoped to compatible account/model state; compaction MUST preserve useful context.

#### Scenario: Pause turn
- **WHEN** Anthropic stops with pause_turn
- **THEN** the Responses client receives an incomplete result with reason max_output_tokens and no hidden automatic continuation

#### Scenario: Context window exhausted
- **WHEN** Anthropic stops with model_context_window_exceeded
- **THEN** the client receives an incomplete result with reason max_output_tokens, never a completed result or an unknown-stop error

#### Scenario: Refusal
- **WHEN** Anthropic stops with refusal on a translated Responses or Chat request, with or without visible reasoning
- **THEN** the response fails with error code invalid_prompt, a message naming the refusal category, and the turn's usage, so Codex does not retry it

#### Scenario: Non-streaming refusal
- **WHEN** Anthropic refuses a non-streaming translated Responses or Chat request
- **THEN** the client receives HTTP 400 invalid_request_error with code invalid_prompt

#### Scenario: Mid-stream refusal with an open tool call
- **WHEN** Anthropic stops with refusal while a tool call block is still open
- **THEN** the client receives no done event for that call, the terminal output omits it, and the response fails with invalid_prompt

#### Scenario: Native mid-stream refusal
- **WHEN** a native Messages stream stops with refusal while a content block is open
- **THEN** the stream is forwarded unchanged and settled as an incomplete terminal

#### Scenario: Unfinished non-refusal stop
- **WHEN** a stream stops with an open block, or with a pending search that a tool_use stop beside a client tool call does not defer, under any other stop reason, or without a stop reason
- **THEN** the request fails with a message naming the open block types, pending search count and stop reason, and the stop diagnostic line is logged

#### Scenario: Stop diagnostics
- **WHEN** a translated Claude message stops
- **THEN** one log line records the stop reason, status, block type counts, output tokens, refusal category, withheld count and delivered-output flag without any content or refusal explanation

#### Scenario: Transport drop
- **WHEN** the Claude connection fails before message_stop
- **THEN** the failure message names the transport exception class

#### Scenario: Grammar-format custom tool
- **WHEN** a Responses request declares a custom tool with a lark or regex grammar, such as Codex's apply_patch
- **THEN** Claude receives a tool with one required string input documenting that grammar, and its call returns to the client as a custom_tool_call carrying the raw input

#### Scenario: Patch tool advertisement
- **WHEN** a Codex client reads the model catalog
- **THEN** Claude models advertise apply_patch_tool_type freeform so the client registers its patch tool

#### Scenario: Unsupported constrained output
- **WHEN** a Responses request declares a malformed grammar, an unknown custom tool format or a provider-specific control without a Claude equivalent
- **THEN** the adapter returns an explicit unsupported-parameter error before dispatch rather than silently ignoring it

#### Scenario: Native resource history outlives provenance retention
- **WHEN** native resource history is submitted after its thirty-day resource provenance expires
- **THEN** it fails explicitly and requires portable context rather than guessing its origin from affinity

### Requirement: Translated hosted web search
Translated Claude Responses SHALL accept nameless web_search declarations and map supported live search options to native Anthropic search. A declaration with external_web_access=false SHALL be omitted, allowing conversation to continue without granting cached or live search through that tool. Other unsupported options MUST fail before dispatch rather than silently weaken caller constraints. HTTP and WebSocket Responses SHALL expose search lifecycle and URL citations, preserve real upstream search state across continuation, and reject missing, tampered or cross-account/model/client replay state. Server search errors and unfinished searches MUST NOT become successful completion.

Anthropic defers a server search that Claude calls beside a client tool: the response stops with tool_use, carries the search call without its result, and the result opens the response to the request that returns the client tool results. A translated response that stops with tool_use and contains a client tool call SHALL complete with each pending search delivered as a done web_search_call with status in_progress, followed by authenticated opaque state holding only that call. Replay SHALL restore the deferred call ahead of its turn's client tool calls. When the request continues that turn with only tool results and still declares search, the call SHALL be forwarded so Anthropic runs it, and the result opening the response SHALL be accepted for that call and stored as the call and result pair, attributed to the original search item. Otherwise the search can no longer run: replay SHALL omit the unanswered call and log the omission count and reason without content. Readable projections SHALL represent an answered deferred search once, as for a completed search, and omit an unanswered one. A search result that matches neither a call in the response nor a resumable deferred call MUST fail.

#### Scenario: Default Codex search declaration
- **WHEN** Codex includes a nameless live web_search tool
- **THEN** the request reaches Claude as a versioned server-search declaration instead of failing name validation

#### Scenario: Cached-only search
- **WHEN** Codex includes web_search with external_web_access=false
- **THEN** the declaration is omitted and the remaining conversation and tools proceed without enabling live search

#### Scenario: Search continuation
- **WHEN** a client replays search output with its authenticated opaque state
- **THEN** the exact upstream search blocks are restored under the same authorized owner

#### Scenario: Missing search state
- **WHEN** a search output has no matching authenticated opaque state
- **THEN** preparation fails explicitly without dispatch

#### Scenario: Search deferred beside a client tool call
- **WHEN** Claude calls web search and a client tool in one response and stops with tool_use
- **THEN** the response completes with the search call delivered as in_progress, its deferred state and the executable tool call

#### Scenario: Deferred search resumes
- **WHEN** the next request returns only the client tool results and still declares search
- **THEN** Claude receives the deferred call ahead of the client tool calls, and the result opening its response is accepted and stored as a complete search for the original item

#### Scenario: Deferred search can no longer run
- **WHEN** the deferred turn is interrupted, continued with other content or search is no longer declared
- **THEN** the unanswered call is omitted from the upstream request and the omission is logged
