# Database — Developer 2

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
