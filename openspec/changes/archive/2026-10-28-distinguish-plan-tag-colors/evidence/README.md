# Plan tag color verification

Verified 2026-10-28 against the local production frontend build.

- Before: both browser cases reproduced only four distinct colors for eighteen known keys.
- After: all eighteen keys have distinct text, background, and border colors in both themes.
- All 108 light/dark palette tokens exactly match the approved HTML preview JSON export.
- Normal and hovered text contrast meets 4.5:1 for every key in both themes.
- Request-table tests: 109 passed, including provider equivalence, normalized keys, unknown values, and null/blank snapshots.
- TypeScript project build and Vite production build passed.
- Both theme browser cases passed against built assets (2 tests).
- Strict validation passed for all 78 main specifications and this change.

## Commands

From `frontend/`:

```sh
node node_modules/vitest/vitest.mjs run src/features/dashboard/components/recent-requests-table.test.tsx
node node_modules/@typescript/native/bin/tsc -b
node node_modules/vite/bin/vite.js build --outDir /tmp/codex-lb-plan-colors-build
node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4177 --outDir /tmp/codex-lb-plan-colors-build
SCREENSHOT_PORT=4177 node node_modules/playwright/cli.js test --config screenshots/playwright.config.ts --grep 'distinct plan tag colors' --reporter=line
```

From the repository root:

```sh
openspec validate distinguish-plan-tag-colors --strict
openspec validate --specs --strict
```

## Screenshots

- [Before, light](before-light.png) / [After, light](after-light.png)
- [Before, dark](before-dark.png) / [After, dark](after-dark.png)

Before screenshots use the original 1440×900 capture viewport. After screenshots use a taller 1920×1800 viewport so fixed application bars do not obscure plan rows. Request fixtures are identical. API data is mocked; no live accounts were modified.
