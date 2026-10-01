# Request model metadata presentation

Scope: the dashboard request-log model cell, not raw metadata in request details.
The name retains the current catalog lookup and readable historical-ID formatting.
Model names stay primary; reasoning effort and exceptional service tiers use the
existing muted foreground token. No new color, badge, pricing or routing state.

For example, `GPT-6.1-Sol (medium, default)` becomes `GPT-6.1-Sol medium`, where
medium is grey. A priority request shows `GPT-6.1-Sol medium · priority` with both
metadata values grey. The exact model ID remains in the native hover title.

The model catalog does not carry separate human-readable effort labels. Existing
effort identifiers remain unchanged; empty values do not create punctuation.
Missing catalog data uses the existing historical formatter without delaying logs.
Requested-priority/actual-default differences remain visible below the label and
in details, preventing a silent loss of operational diagnostics.
