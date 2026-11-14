# Developer 3 handoff

Work is on feature/integrations, based on local main/origin/main at 8b34cb1.
Issues #23, #24, #29 reviewed. No shared contracts, Flask routes, database files,
configuration or dependencies changed. No commits, pushes or merges performed.

Run from src/backend (same import convention as app.py):

```python
from services.normalizer import normalize_ingredient
from services.recipe_import import import_recipes
from services.vision import scan_fridge
from services.grocery_prices import search_grocery_products, get_grocery_product, get_grocery_categories
from services.substitutions import suggest_substitutions

recipes = import_recipes()  # list[Recipe], real captured 3-row offline subset
# Dev 2: save_recipes(recipes); serialize with model_dump(mode="json").
```

Interfaces:
- normalize_ingredient(name: str) -> Ingredient. IDs use ing_ plus canonical
  English alias or normalized label slug. Unknown identities retain specificity;
  aliases are intentionally limited, not a complete translation vocabulary.
  Do not strip modifiers such as powder, almond, breast or green.
- import_recipes(*, live=False, limit=100, rows=None) -> list[Recipe]. Explicit
  live=True fetches at most 100 viewer rows with a 20-second timeout. Default
  loads tests/fixtures/integrations/recipes.json, not generated demo recipes.
  Inject rows for parser tests. Invalid/ambiguous rows are skipped; an empty
  result is possible. No silent fixture fallback on network failure.
- scan_fridge(image_bytes: bytes, *, detector=None) -> list[ScanCandidate].
  detector(bytes) returns [{"name": ..., "certainty": "high|medium|low"}].
  Otherwise set VISION_API_KEY and VISION_MODEL; optional VISION_API_URL is an
  OpenAI-compatible chat/completions endpoint (default OpenAI). Accepts JPEG/PNG;
  route owner should validate actual upload MIME. 30-second timeout, 20 MiB cap.
  Qualitative certainty is not calibrated probability. Every quantity stays
  unknown, including provider-supplied amounts. No pantry writes.
- search_grocery_products(query: str, limit: int = 10) -> GrocerySearchResponse.
- get_grocery_product(product_id: str) -> GroceryProduct.
- get_grocery_categories() -> list[dict]. No FoodCategory enum enforced.
  GETs use 15-second timeout and a process-local 300-second cache. Source times
  remain distinct from search fetched_at. Provider failures raise RuntimeError;
  invalid inputs raise ValueError. Monetary conversion uses Decimal, half-up.
- suggest_substitutions(request: SubstitutionSuggestionRequest, *,
  buyable: list[IngredientProductMatch] | None = None)
  -> SubstitutionSuggestionResponse. Narrow spinach-to-kale and sour-cream-to-
  plain-yogurt rules, with context limits. Confirmed pantry first. Optional
  buyable matches are explicitly supplied by caller after product selection;
  no implicit network searches. Does not apply swaps or mutate recipe/pantry.

Call grocery search only after matching, for selected missing ingredients or
selected alternatives. Results require relevance review and user SKU selection.
Package prices are not consumed-quantity cost; discount flags are not percent off.
Attribute displayed offers to épiceries.ca. No availability guarantee.

## Source evidence and fixture provenance (2026-11-14)

Direct urllib calls to HF/categories/search failed DNS in this workspace.
Firecrawl with maxAge=0 returned HTTP 200 JSON for these exact URLs; captures are
in tests/fixtures/integrations/{recipes,categories,search,product}.json:

- https://datasets-server.huggingface.co/rows?dataset=rahul7star/food-recipes&config=default&split=train&offset=0&length=3
- https://epiceries.ca/api?endpoint=categories
- https://epiceries.ca/api?endpoint=search&q=lait&limit=2
- https://epiceries.ca/api?endpoint=product&id=B2kZGPy7um8F
- Documentation: https://www.epiceries.ca/developers

HF reports 15,698 rows. Actual features: name/description/markdown strings;
recipe_id/minutes integer; steps/tags string lists; nutrition float-valued
object; rating/num_ratings float; image feature. There is NO ingredients column!
Parser extracts the isolated Markdown Ingredients section (comma-delimited) and
checks n_ingredients to reject ambiguous parsing. No quantities or servings
were supplied in these samples. PDV nutrition fields retain their meaning.
Minutes over one week are treated as implausible/unknown. No images are fetched;
image metadata was removed from captured rows. Source image is a recipe card.

Real category response contains 71 categories: 7=Lait, 9=Oeufs, 12=Yogourt,
16=Poulet et dinde, 27=Haricots secs, lentilles et pois. These differ from docs
examples. No local category enum exists in the shared schemas.
The unfiltered lait search returned soap (category 70, $3.97 at Walmart) and
chocolate pretzels (category 64). They are deliberately retained as evidence
that text search alone does not establish ingredient suitability.
Product detail B2kZGPy7um8F returned per-store offers and original payload.

Tests replay captures and mock network boundaries; they do not establish direct
runtime provider connectivity. No real vision photo/API request was tested:
issue #24's real-photo acceptance remains outstanding. No AI substitutions.

## Validation

From src/backend: `python -m unittest discover -s tests -v`.
A schema-valid export for Dev 2 is tests/fixtures/integrations/normalized_recipes.json.
Regenerate from the captured source with:

```python
import json
from pathlib import Path
from services.recipe_import import import_recipes
Path('tests/fixtures/integrations/normalized_recipes.json').write_text(
    json.dumps([r.model_dump(mode='json') for r in import_recipes()], indent=2) + '\n')
```
