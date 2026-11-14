# Database — Developer 2

## Phase 2: SQLAlchemy + PyMySQL (current durable path)
The SQLAlchemy repository now handles configured `DATABASE_URL` calls. The old
`MariaDBPantryRepository`, `connection.py` and `schema.sql` are retained solely for
compatibility with the first implementation/tests; they are not the active path.
Do not apply the old SQL schema for the relational implementation.

From repository root, in PowerShell, with Docker Desktop running:
```powershell
.\.venv\Scripts\python.exe -m pip install -r src/backend/database/requirements.txt
# Set these in your shell to your own local values (never commit credentials):
$env:MARIADB_DATABASE = 'refood'
$env:MARIADB_USER = 'refood'
# Supply MARIADB_PASSWORD and MARIADB_ROOT_PASSWORD via your environment.
docker compose -f src/backend/database/compose.yaml up -d --wait
docker compose -f src/backend/database/compose.yaml ps
```
Set `DATABASE_URL=mysql+pymysql://USER:PERCENT_ENCODED_PASSWORD@127.0.0.1:3306/refood`.
Existing `mariadb://...` URLs also map to PyMySQL. Then, from `src/backend`:
```powershell
python -m database.engine
python -m unittest discover -s tests -v
```
Schema creation is explicit, never performed by Flask. The named volume persists
across `docker compose ... down` and subsequent startup; do not use `down -v`
unless intentionally deleting local database data. Environment credentials only
initialize a fresh volume; changing them does not rotate existing DB users.

Dev 3 integration (from src/backend):
```python
from database.catalog import save_recipes, get_recipes, SQLRepository
count = save_recipes(normalized_recipes)  # list[Recipe], no fetching here
recipes = get_recipes()                  # list[Recipe]
```
`save_recipes` returns the number of distinct recipe IDs processed (including
updates), not the number newly inserted. A repeated ID updates metadata and
replaces its ordered ingredient rows in one transaction. All optional Recipe
fields are preserved in `metadata_json`, with ingredient identity/amount/unit in
relational rows. Unknown values remain null. Recipe identity is `recipe_id`;
Dev 3 must supply stable source-prefixed IDs. `source_recipe_id` alone is not
globally unique. Ingredient labels on each relation preserve original display names.

`find_recipes` keeps its existing ranking logic. With DATABASE_URL it searches
stored recipes; without it it uses the original sample fixtures. An empty DB
returns no results. A configured unavailable DB raises an error, rather than
silently presenting fixture recipes as production data. The pantry's default
in-memory behavior and public signatures remain unchanged.

`SQLRepository.save_grocery_products(products: list[GroceryProduct]) -> int` and
`get_grocery_products() -> list[GroceryProduct]` cache products and latest per-store
observations separately, including timestamps/raw payloads, with native MariaDB
upserts. Stores not present in a partial update retain their last observation;
this is a latest-observation cache, not historical price tracking. Nullable
metadata is replaced by the new observation, not invented or carried forward.

`services.recipe_matcher.apply_swaps(recipe, swaps, pantry)` returns the existing
`RecipeVariationResponse`. Swaps are `list[IngredientSwap]`; pantry is
`list[IngredientWithQuantity]`. It copies ingredients, rejects unknown/duplicate
targets, recomputes missing items, and flags changed instructions/nutrition for
review. It never persists the variation or mutates source nutrition/instructions.

Tests use disposable SQLite files for SQLAlchemy round trips plus original
in-memory/legacy tests. For real MariaDB, create a **dedicated disposable** test
database, set `TEST_DATABASE_URL=mysql+pymysql://.../refood_test`, then run
`python -m unittest discover -s tests -p test_mariadb_live.py -v`.
The opt-in live test creates tables and leaves a uniquely named recipe fixture.
It does not drop databases or touch production recipe IDs.

Limitations: no migration framework; existing legacy pantry JSON rows require an
explicit migration before switching durable storage. Sequential imports are
idempotent; concurrent bulk imports/pantry replacements may need retry after a
transaction conflict. No schema, shared config, Flask, or provider code changed.
Dependencies are scoped to database/requirements.txt pending team consolidation.

The sections below describe the initial demo implementation and matching rules.

## Interfaces (run/import from src/backend)
```python
from services.recipe_matcher import find_recipes, match_recipes
from database.repositories import get_pantry, replace_pantry

find_recipes(request: RecipeSearchRequest) -> list[RecipeMatch]
get_pantry(user_id: str) -> PantryResponse
replace_pantry(user_id: str, request: PantryUpdateRequest) -> PantryResponse
```
`find_recipes` uses an explicitly illustrative three-recipe catalog. Developer 3's
eventual `list[Recipe]` can be passed to `match_recipes(request, recipes)` without
changing schemas or introducing a provider dependency. Developer 1 wraps results
in `RecipeSearchResponse(results=...)`. There are no new Flask routes here.

## Normalization handoff to Developer 3
Proposed fixture IDs (not yet agreed with Developer 3): `ing_egg`, `ing_milk`,
`ing_tomato`, `ing_pasta`, `ing_rice`. Both requests and recipe imports must use
the same canonical IDs. Matching is exact and case-sensitive; names are display
labels. No synonym, accent, translation or ID guessing happens here.

Coverage is the fraction of distinct recipe IDs present with positive or unknown
stock. Rank by descending coverage, fewer missing IDs, known quantities, then
recipe ID. Zero stock counts as absent. Known shortages are listed as missing
with the recipe's full requirement, not an invented deficit. Unknown or
incompatible quantities flag `quantity_uncertain`; they do not assert a shortage.
Compatible g/kg and ml/l convert; pieces never convert to mass or volume.
Repeated stock amounts sum; repeated requirements in different units are treated
conservatively as unknown. Empty recipes are skipped. `max_missing` filters before
`limit`. Recipe/request objects are not mutated.

## Pantry storage
With no `DATABASE_URL`, the default is an explicitly **in-memory demo store**.
It is per-process and loses data on restart; it is not durable persistence.
Requests replace the entire inventory, including an empty list to clear it.
Users are isolated by exact ID; callers receive independent Pydantic objects.
`remaining_fraction` is stored unchanged; it does not change matcher quantities
(RecipeSearchRequest has no remaining_fraction field).

Optional MariaDB setup:
1. Install the optional `mariadb` Python connector in your environment. Shared
   requirements are unchanged pending team coordination.
2. Create a database and explicitly apply `database/schema.sql` to it.
3. Export `DATABASE_URL=mariadb://user:password@host:3306/database` in the process
   running the backend (percent-encode credentials when necessary). URL query
   parameters/fragments are currently unsupported.

Only repository calls import the driver and connect. No startup migration or
database connection occurs. Configured database failures propagate; there is no
silent fallback to memory. Each replacement uses a parameterized atomic upsert
and transaction, rolling back on failure. The InnoDB table stores a pantry JSON
document per user; `PantryRecord` is a separate storage dataclass. Recipe catalog
persistence is deferred. Custom TLS/connection options are also deferred.

## Verification
From `src/backend`: `python -m unittest discover -s tests -v`.
Matcher and memory tests run without MariaDB. MariaDB adapter tests use DB-API
fakes to exercise mapping, bound parameters, commit/rollback and cleanup;
these do **not** validate a live MariaDB server or migration.
