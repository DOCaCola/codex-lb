## REMOVED Requirements

### Requirement: Codex catalog size is checked against the client limit

**Reason**: Codex removed the 1 MiB `model_catalog_url` response limit in openai/codex#56525; releases 0.166.0 and later accept larger catalogs, and ordinary `/models` discovery never had a limit. The requirement also misstated the consequence: with an explicit catalog URL, Codex 0.161.0–0.165.0 keep their last fetched catalog instead of using the bundled one.

**Migration**: None. Clients from 0.161.0 to 0.165.0 that use `model_catalog_url` should update to 0.166.0 or later.
