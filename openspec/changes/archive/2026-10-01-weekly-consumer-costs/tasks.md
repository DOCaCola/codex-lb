# Tasks

## 1. Attribution costs

- [x] 1.1 Aggregate shared request cost coverage in existing attribution query and response; verify mixed models, unknown/free data, filters and overview/projections tests.
- [x] 1.2 Display compact estimated cost cells with coverage tooltips; verify schema/formatting tests and document the two-hour basis.

## 2. Consistent subtitles

- [x] 2.1 Simplify provider dashboard card subtitles and standardize optional ID separators; verify card tests retain plan/provider, privacy, controls and model selection outside the dashboard.

## 3. Integration verification

- [x] 3.1 Check responsive rendering and capture screenshots; run focused backend/frontend tests, lint and type checking, sync specs/context and validate OpenSpec.

## Verification

- Backend: 48 weekly-pace/overview/projections tests passed; changed-path Ruff passed.
- Frontend: 419 dashboard/provider-display tests passed; typecheck and changed-path ESLint passed.
- Browser: three mocked dashboard checks passed at 320, 390 and 1440 pixels;
  screenshots captured and inspected, with no page or consumer-row overflow.
- Delta and frontend-architecture spec passed strict validation; all 75 main specs
  passed strict validation. No production changes or paid requests.
- Concurrent Claude subscription discovery was preserved; card plans use the
  same middle-dot separator and model-selection counts remain omitted.
