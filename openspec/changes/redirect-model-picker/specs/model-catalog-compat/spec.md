## MODIFIED Requirements

### Requirement: Operators manage redirects through the settings API

`GET /api/settings/model-redirects` MUST list each redirect with `status` (`active`/`inactive`), its
`reason` and the eligible targets by provider. It MUST also list `imageSources`, the image models clients request
from the image backend, and `disabledModels`, the text models each connected provider account offers but does not
publish, grouped by provider. `PUT .../{source}` MUST create or replace a redirect;
`DELETE` MUST remove it (404 `model_redirect_not_found` when absent). Writes MUST require dashboard write
access, be audited as `settings_changed` naming `model_redirects`, and invalidate the cross-replica snapshot.

#### Scenario: Storing a redirect
- **WHEN** `PUT /api/settings/model-redirects/gpt-5.4` stores target `gpt-5.5`
- **THEN** the next request on every replica uses the redirect
- **AND** a `settings_changed` audit event names `model_redirects` and `gpt-5.4`

#### Scenario: Deleting an absent redirect
- **WHEN** `DELETE /api/settings/model-redirects/gpt-5.4` is called without a stored redirect
- **THEN** the response is 404 with code `model_redirect_not_found`

#### Scenario: Listing redirect sources
- **GIVEN** an OpenRouter account offering a text model that is not enabled
- **WHEN** `GET /api/settings/model-redirects` is called
- **THEN** `imageSources` contains `gpt-image-2`
- **AND** `disabledModels` lists the OpenRouter model under its provider
