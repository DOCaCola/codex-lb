## 1. Parameter descriptions

- [x] 1.1 Add the documented OpenAI image parameter table and the native `gpt-image-2` description.
- [x] 1.2 Publish `image.supported_parameters` for OpenAI API image models on `/v1/models`.
- [x] 1.3 List native `gpt-image-2` on `/v1/models`, following API-key restrictions and image redirects.

## 2. Verification

- [x] 2.1 Integration tests for documented, undocumented, native, redirected and restricted image models.
- [x] 2.2 Ruff, type checks and the image and model-list test suites pass; strict OpenSpec validation passes.
