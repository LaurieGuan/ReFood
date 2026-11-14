# Integration audit — 2026-11-14

Implemented on the existing `main` working tree without committing, pushing, merging, switching branches, or changing history. The pre-existing untracked root `package.json` and `package-lock.json` were preserved. No concurrent edits were observed in the changed files. Vision, recipe importer, matcher algorithms, dietary classification, shared schemas, app wiring, config, and dependencies were not modified.

## Fixed behavior

- Real recipe retrieval uses only the cache populated by Flask search. An unknown ID fails; it never consults sample recipes or local favorites. Browsing the personal library explicitly reads local recipes/favorite snapshots.
- Flask recipe search requires a configured, populated catalog. Missing configuration or an empty catalog returns 503 instead of invoking `sample_recipes()`.
- Missing scan, grocery search, pantry repository, and substitution-suggestion modules return errors instead of successful empty mock results.
- Real-mode requests reject explicitly marked demo/mock/fixture/sample responses and recipes. Malformed JSON is an error. Unknown response provenance is labeled unknown, rather than asserted live.
- Data-source badges distinguish Flask responses, demo results, browser-local records, unknown sources, and failures. Demo mode has a visible warning and a switch back to live mode on both the entry screen and application screen.
- Legacy `localStorage['refood-demo-mode']` is ignored. Default is Flask. `VITE_REFOOD_DEMO=true` deliberately configures demo; the visible mode switch sets `?api_mode=demo` or `?api_mode=live` and reloads, clearing active results and API caches. Explicit live overrides the demo environment default.
- Personal library excludes predefined samples in live mode. Saved sample favorites remain accessible and visibly retain their demo label alongside local storage. Imported favorite snapshots and personal recipes are labeled local, rather than represented as MariaDB records. Preferences have the same browser-local label.
- Grocery baskets count distinct required ingredients with valid, relevance-classified offers. Each store lists its own missing/unpriced ingredients. Partial subtotals are explicitly non-comparable with complete baskets; complete baskets appear first and are selected first when available. Exports use the same filtering and distinguish incomplete coverage. Product, package, retailer link, source and observation date remain visible. Prices describe selected packages, not recipe-quantity fulfillment.
- `/api/v1/recipes/variations` retrieves the stored recipe and calls the existing `apply_swaps(recipe, swaps, pantry)`. Unknown recipes return 404; unknown/duplicate swap IDs return 422. Original recipes are preserved and changed instructions/nutrition require review.

## API and integration

Existing Pydantic JSON shapes are unchanged. Successful core responses add `X-Refood-Source` (`recipe_catalog`, `vision_provider`, provider attribution for groceries, or `confirmed_user_input` for pantry). Pantry also adds `X-Refood-Persistence: mariadb|memory`. The same-origin frontend consumes these headers. These labels describe response provenance, not independent verification of AI output, recipe correctness or price freshness.

Live recipes and variations require `DATABASE_URL`, initialized tables and imported recipes. Pantry without `DATABASE_URL` retains genuine confirmed input in server process memory; its response explicitly identifies that persistence. Browser favorites, personal recipes and preferences are never synchronized to MariaDB. Errors retain the shared `{ "error": ... }` shape. Live grocery failures still permit an unpriced shopping-list export, visibly marked unavailable.

## Changed files

Backend:
- `src/backend/routes/recipes.py`, `scans.py`, `grocery.py`, `pantry.py`
- `src/backend/tests/test_integration_audit.py`, `test_final_integration.py`
- `src/backend/README.md`

Frontend:
- `src/frontend/src/services/api/flaskApi.js`, `apiMode.js`, `mockApi.js`, `integrationAudit.test.js`
- `src/frontend/src/components/ApiModeControl.jsx`, `DataSource.jsx`
- `src/frontend/src/app/App.jsx`, `useAppController.js`
- `src/frontend/src/features/auth/Login.jsx`
- `src/frontend/src/features/recipes/RecipeGrid.jsx`, `RecipeDetails.jsx`, `useRecipeLibrary.js`
- `src/frontend/src/features/stores/StoreCard.jsx`, `StoreScreens.jsx`, `basket.js`
- `src/frontend/src/styles/flow.css`
- This report: `docs/integration-audit.md`

## Verification

- From `src/frontend`: `npm run build` — passed.
- From `src/frontend`: `node --test src/services/api/*.test.js src/features/scan/*.test.js` — all three test files passed, including existing confirmation/relevance regressions.
- From `src/frontend`: `node src/services/api/integrationAudit.test.js` — seven new regression tests passed, including rendered HTML assertions for demo warning, local badge and incomplete basket.
- From `src/backend`: `.venv/bin/python -m unittest discover -s tests -q` — 150 tests ran, 32 skipped, no failures. Includes focused HTTP failure-path tests, actual swap-helper tests and SQL-backed variation retrieval using SQLite.
- `git diff --check` — passed.
- The first backend test invocation was incorrectly run from repository root and failed on imports; the correctly located full run above passed. Initial misplaced frontend commands were rerun from `src/frontend`.
- No live Gemini, grocery-provider, MariaDB or browser end-to-end test was performed. SQLite route coverage is not MariaDB verification.

## Preserved demos and remaining risks

- Explicit offline sample recipes, simulated scan candidates, illustrative grocery offers and fictitious store distances remain available only through deliberate demo mode. The small ingredient catalog and preference option lists remain local reference data, not fabricated recognition results.
- Existing demo-account code already identifies browser-only demo accounts. Marketplace/donation identities remain explicitly demo identities; those endpoints require the database and do not silently fabricate responses.
- The legacy matcher `find_recipes()` still contains its sample fallback, and importer fixture helpers remain for tests/development. The HTTP recipe route no longer calls that matcher entry point. These service files belong to the main feature agent and were intentionally not changed; future callers must avoid exposing the legacy fallback.
- Current browser storage helpers tolerate storage failures and can retain changes only in session memory. Existing local features are preserved; durable storage is not guaranteed when browser storage is disabled.
- `.env.example` still contains an older comment about recipe demo storage; no shared configuration files were changed. The backend README now documents the stricter HTTP behavior.
- No teammate conflict was detected. The other agent should preserve the route guards and provenance headers while integrating its P0 changes, especially in `routes/recipes.py` and `routes/scans.py`.
