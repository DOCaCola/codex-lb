## 1. Implementation

- [x] 1.1 OpenAI refresh keeps the sent refresh token when the response omits it
- [x] 1.2 Claude refresh keeps the current refresh token; the code exchange still requires one
- [x] 1.3 Tests: omitted and rotated refresh tokens for both providers

## 2. Verification

- [x] 2.1 Auth and Claude credential tests, ruff, ty and strict OpenSpec validation
- [ ] 2.2 Archive after deployment
