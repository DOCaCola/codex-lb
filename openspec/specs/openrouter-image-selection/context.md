# Separate image picker

Accounts → OpenRouter account → Image models lists entries from OpenRouter's
dedicated image catalog, including Sunburst. Models manages remaining catalog
entries and unavailable saved selections. Both dialogs operate on the same
selection list and retain out-of-scope entries unchanged. A model with dedicated
image metadata appears only in Image models, including dual-output models.

For example, selecting Sunburst in Image models leaves a selected Qwen model's
context/output caps intact. Saving Models leaves Sunburst selected. Missing
catalog entries are not deleted; they remain removable under Models because
their former capability cannot be inferred from the model ID.

The account Refresh action fetches the combined text/image catalog. Catalogs
otherwise refresh every six hours; an existing snapshot from before deployment
may not contain image entries yet. The picker includes a refresh hint.

This is a management UI separation, not a new routing policy: image selections
continue to serve public Images API requests. Codex's native image path and
gpt-image-2 policy remain unchanged. No schema migration is required.
