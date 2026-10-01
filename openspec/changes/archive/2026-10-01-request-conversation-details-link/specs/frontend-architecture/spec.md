## ADDED Requirements

### Requirement: Request details link to conversation details

For users with `conversations:read`, request details with a conversation ID MUST
offer a separate View details action beside that ID. Activating it MUST close
request details and open the existing Conversation Details dialog for the exact
opaque conversation ID without changing request-log filters or pagination.
Existing conversation-ID filtering and copying MUST remain unchanged. Without
a conversation ID or the permission, the action MUST be absent. Conversation
details MUST NOT be fetched before activation. Closing the conversation dialog
MUST clear its selection. Loading and errors MUST use the existing dialog behavior.

#### Scenario: Opening conversation details directly
- **GIVEN** an authorized user views request details for conversation `conv / a`
- **WHEN** they activate View details
- **THEN** request details close and Conversation Details open for `conv / a`
- **AND** existing filters and pagination remain unchanged

#### Scenario: Unavailable conversation action
- **GIVEN** a request has no conversation ID or the user lacks `conversations:read`
- **WHEN** request details open
- **THEN** no conversation-details action or fetch occurs

#### Scenario: Fetch only on selection
- **GIVEN** request details display a conversation ID
- **WHEN** the user has not activated View details
- **THEN** no conversation-details fetch occurs
- **WHEN** they open, close, and select another conversation
- **THEN** the dialog displays the newly selected conversation
