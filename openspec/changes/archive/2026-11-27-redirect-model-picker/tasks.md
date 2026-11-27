## 1. Implementation

- [x] 1.1 Share the client image model constant between the image routes and the model-source catalog
- [x] 1.2 Expose each provider's publishable text models and list unpublished ones as `disabledModels`
- [x] 1.3 Return `imageSources` and `disabledModels` from the redirect settings API
- [x] 1.4 Add the shared searchable, sectioned `ModelPicker` component
- [x] 1.5 Use it for both redirect fields, with client requests separated and the "Show disabled models" switch

## 2. Verification

- [x] 2.1 Integration test for the new settings response fields
- [x] 2.2 Picker and redirect-form tests, frontend typecheck, lint and build
- [x] 2.3 Backend suite, ruff, ty and strict OpenSpec validation
- [x] 2.4 Archive after deployment
