# Design

Keep account_id and model_source_id separate. Batch-resolve names for page source IDs; never expose credentials. accountId filter values beginning `source:` select model_source_id; native account IDs retain their existing meaning. Source-filtered counts use raw logs because demand rollups have no source dimension. Facets include persisted IDs even after deletion. Provider names follow account-identity permission and email privacy rules. Do not infer provider identity from a model string.
