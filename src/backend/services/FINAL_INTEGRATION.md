# Final integration verification — 2026-11-14

Existing main checkout preserved; no commit, push, merge, branch changes or
changes to the unrelated root package.json/package-lock.json. Issues #33–#39
reviewed. Existing database and frontend components reused.

## Phase status

1. Vision: configured gemini-3-flash-preview successfully read the synthetic
   milk label in tests/fixtures/integrations/packaging_test.png. Real authenticated
   Gemini call, unknown quantity, qualitative certainty, normalized identity.
   Browser upload/Flask/React candidate review verified. No genuine refrigerator
   photo was available, so broad food-recognition accuracy remains untested.
   Hardened provider JSON parsing, deduplication, MIME handling and errors; normal
   Flask startup now loads the ignored backend .env. No keys logged or added.
2. Confirmation: browser renamed a detection to flour, set 500 g, added/discarded
   an incorrect item, added salt/dry mustard/garlic powder/oil, saved to MariaDB
   and read back the corrected inventory. Original demo pantry restored after
   both successful browser runs (HTTP 200). Duplicate conflicts and invalid names
   are rejected; identical normalized duplicates collapse. kg/L are selectable.
3. Catalog: streaming gzip JSONL command uses existing SQLRepository upserts,
   bounded batches, count validation and line-numbered rejection output. Three
   real captured recipes imported/reimported in MariaDB: 3 accepted, 0 rejected,
   3 upsert operations each time; final catalog remained 3 rows. A 1,001-row test
   checks six bounded batches; this larger test uses an explicit mock repository.
   Actions artifact listing returned no available artifacts. Full-catalog import
   remains blocked until refood-recipes.jsonl.gz is supplied. No original dataset
   or images were downloaded. Empty configured catalog returns actionable 503.
4. Ranking/preferences: full SQL catalog filtered before result limit; coverage
   stays primary. Existing compatible-unit comparisons retained. Deterministic
   dietary/allergen rules exclude known incompatibilities and mark ambiguous
   classifications unverified. Meat is never certified halal by its name.
   Time/calorie/available-PDV limits, exclusions, invalid preferences tested.
   Browser set 600-minute/200-kcal controls and confirmed their API payload;
   separate live HTTP search verified a 30-minute cutoff. Nutrition displayed
   with kcal or % VQ, never converting PDV into grams. Budget remains explicitly
   unverified until grocery observations are available.
5. Groceries: real categories/search/detail verified. Categories contain 71
   entries; 7=Lait. Backend validates optional category against the actual
   categories endpoint. Frontend uses bilingual queries, name/category relevance,
   label exclusions and per-store detail observations. Soap, pretzels, evaporated/
   condensed/powdered/flavored milk cannot count as regular milk. Ambiguous
   candidates are excluded from totals. Prices are CAD cents; missing prices stay
   unknown. Incomplete baskets show subtotals, not complete-basket claims.
   Final live milk regression returned plain skim/1% milk at all six retailers
   ($2.15–$2.23 observed package prices); 19 ambiguous names were excluded from
   totals. Earlier live checks exposed coconut, flavored and limited-edition
   labels; regression rules now use conservative plain-milk vocabulary and
   retailer-link evidence. Search considers 100 products, details the top three
   suitable candidates; totals are bounded observations, not a global market minimum.
6. Browser: scripts/smoke_demo.cjs completed twice against real Flask, Gemini,
   MariaDB and Épiceries.ca, including download. No page errors, API HTTP failures
   or console errors in the final run. Export contained a relevant pork-chop
   offer and explicitly unknown chicken/rice soup price. Browser snapshot:
   /tmp/refood-stores.png; text export: /tmp/refood-shopping-list.txt.

Phase 7 intentionally deferred: full-catalog P0 verification remains blocked.
No routing/location data or fabricated travel costs added. Existing variation
endpoint still needs its separate apply_swaps integration (#37).

## Run/import

Use the existing backend virtual environment and ignored .env:

```bash
cd src/backend
.venv/bin/python -m services.recipe_import /path/to/refood-recipes.jsonl.gz --batch-size 200 --rejections /tmp/refood-rejections.jsonl
.venv/bin/python -m unittest discover -s tests -q
.venv/bin/python -m flask --app app:create_app run --port 5000
```

Importer reports read/accepted/rejected/upserted counts. Upserted is operations,
not new rows. Batches commit independently; retry is safe after interruption.
No Hugging Face dependency during app usage.

Frontend: `npm run dev` / `npm run build` from src/frontend. Optional
REFOOD_BACKEND_URL overrides the Vite proxy target when port 5000 is occupied.
Browser script uses a separately installed Playwright (not a repo dependency):

```bash
NODE_PATH=/tmp/refood-browser/node_modules node scripts/smoke_demo.cjs src/backend/tests/fixtures/integrations/packaging_test.png
```

Requires browser binaries, a running Vite/Flask pair and the three captured
recipes already in MariaDB. This makes a live vision call and restores pantry
contents afterward; do not run concurrently with another pantry editor.

## Contracts/files

Optional shared additions: RecipeSearchRequest.preferences (validated dictionary
matching existing frontend names), RecipeMatch.preference_warnings (string list).
Existing recipe, ingredient, price and scan field shapes retained.
GET /api/v1/grocery/products/<product_id> now returns existing GroceryProduct.
GET product search accepts optional provider category. Invalid category -> 400.
Vision provider failure -> 502, invalid image -> 400. Pantry normalization failure
-> 422. No silent fallback on configured provider/database failures.

Changed areas: app startup; scan/pantry/recipe/grocery routes; recipe schema;
vision, pantry_confirmation, recipe_import, recipe_matcher, recipe_preferences,
grocery_prices services; backend regression tests and synthetic image; React
confirmation/preferences/recipe displays/grocery API/relevance/store displays;
Vite proxy override; browser smoke runner. Existing database files untouched.

Verification: backend suite 138 tests run, 32 skipped (opt-in database suites);
frontend confirmation/relevance Node checks passed; Vite production build passed.
Live MariaDB/browser checks above are separate from the skipped opt-in suites.
Direct sandbox DNS initially failed; successful live checks used permitted
network access outside that sandbox. No mock vision/provider results were used
in the successful browser runs.
