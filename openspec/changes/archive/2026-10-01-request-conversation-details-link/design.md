# Design

Use local conversation selection state in RecentRequestsTable and mount the
existing ConversationDetailsDialog only after activation by an authorized user.
The link-styled button closes Request Details before opening Conversation Details,
avoiding stacked dialogs. Closing it clears the selection.

Keep the ID's existing filtering action and CopyButton unchanged. Reuse the
conversation view's translated action label and accessible name. Fetching remains
owned by the existing dialog/query, including opaque-ID encoding, loading and
error handling. No changes to filters, pagination, or browser location are needed.
