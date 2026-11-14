---
tags: [refood, backend, integration, recipes, substitutions]
status: shared-contract-v1
owner: all-backend-developers
---
# Recipe Enrichment and Ingredient Substitutions

> [!important] Branch safety
> Current `main` has additive shared contracts. Dev 1's `feature/api` and Dev 2's `feature/database` already contain separate work and were behind `main` when this note was written. **Do not restart their Codex tasks.** Each developer first commits/stashes local changes, pulls `main`, then merges `origin/main` into their EXISTING branch (or rebases only if coordinated). New Dev 3 branch starts from updated `main`.

## Decision: datasets
Primary: `rahul7star/food-recipes` (about 15.7k entries; structured `recipe_id,name,ingredients,steps,minutes,description,tags,nutrition,rating,num_ratings`; image data is large). Source reference: https://huggingface.co/datasets/rahul7star/food-recipes. Inspect real samples and exact field formats before coding parsers. Fetch only text columns and a manageable sample; never clone/download the entire image-heavy dataset for the demo. Data parser must handle nulls and odd time values. Keep source ID using a `rahul7star:` or other agreed prefix to prevent collisions.

Existing `src/backend/schemas/recipes.py` was extended with OPTIONAL `source,source_recipe_id,description,tags,nutrition,rating,num_ratings`. Keep existing RecipeSearchRequest/Response and RecipeMatch fields unchanged for Dev 1/2 compatibility. Nutrition *_pdv fields are percentages of daily values (not grams). Preserve unknown fields as null. Recipe instructions are source instructions; changing an ingredient may invalidate them.

## Decision: grocery product API
Provider https://www.epiceries.ca/developers (documented, live request still needs to be verified on developer machine). Search AFTER recipe matching and only for missing ingredients or selected substitutions. Data contracts already exist in `src/backend/schemas/prices.py`; **do not create duplicate GroceryProduct or StorePrice classes**. A provider product/SKU is not equal to a canonical ingredient ID.

Dev 3 adapter: `search_grocery_products(query: str, limit: int = 10) -> GrocerySearchResponse`, `get_grocery_product(product_id: str) -> GroceryProduct` (candidate signatures; coordinate if API uses another). Retain `raw_payload` as a JSON-compatible dict for caching provider data, and all known fields: name, provider ID, brand, size, category, image, links, cheapest store/price, discount flag, unit price, timestamp, store-specific offers when fetched. No invented discount percentages or stale prices labelled live. Convert monetary amounts with Decimal to integer CAD cents.

Dev 2: optional tables keyed by (provider, provider_product_id) for products and (product, store) for store offers; upsert to avoid duplicates, retain timestamps/nullable fields/raw JSON and source attribution. Implement **after** working recipe storage/matching. Cache only relevant results rather than scraping all API data.

FoodCategory IntEnum from teammate is a candidate filter, NOT yet a verified taxonomy. Call `GET https://epiceries.ca/api?endpoint=categories` on developer machine; compare IDs and category names before enforcing. Exclude irrelevant categories only when source IDs match actual API. Keep query relevance filtering because membership in a broad food category does not prove an item fits a recipe.

## User-editable scan
`POST /api/v1/scans` returns candidate items; no automatic pantry mutation. Frontend presents checkboxes, rename/remove/add missed foods, and user explicitly confirms by `PUT /api/v1/pantry`. Stable ingredient IDs are crucial. Unknown quantities remain null. Human-edited IDs must be normalized rather than trusting arbitrary client strings blindly.

## User-controlled substitutions (NEW)
User may reject a recipe ingredient and choose:
1. a plausible ingredient they ALREADY HAVE (from confirmed pantry);
2. a candidate missing from pantry that can be searched as a grocery product/SKU;
3. a manually specified ingredient, normalized to canonical identity.

New `src/backend/schemas/substitutions.py` contains `SubstitutionSuggestionRequest/Response`, `SubstituteCandidate`, `RecipeVariationRequest/Response`, `IngredientSwap`, `SubstituteSource`.
A recommendation is **not** an automatic modification. UI displays candidates; the user accepts a swap explicitly. Applying a swap changes a recipe **variation**, not the source dataset record. Re-evaluate missing ingredients and quantities against pantry. Mark instructions and nutritional analysis as requiring review/recalculation (don't reuse original nutrition as accurate after swaps). For allergy/diet restrictions never assert safety without ingredient data and review.

### Proposed endpoints (Dev 1 after existing API tests pass)
- `POST /api/v1/recipes/substitutions` → `SubstitutionSuggestionResponse`.
- `POST /api/v1/recipes/variations` → `RecipeVariationResponse`.
- Existing `POST /api/v1/recipes/search` and scan/pantry endpoints stay backward compatible.
Keep a single route owner: Dev 1. Do not have Dev 3 edit Flask routes. Dev 2 may implement a pure `apply_swaps(recipe, swaps, pantry)` function and rank recalculation. Dev 3 implements ingredient-name normalization, optional substitute suggestions (rules/LLM), and grocery lookup, but not recipe persistence.

### Practical substitution algorithm for MVP
- First show hand-curated substitution aliases (e.g., spinach ↔ kale if sensible for dish, milk ↔ suitable alternative with limits); use the confirmed pantry as candidate pool.
- Rank by semantic culinary suitability and user inventory, not mere string similarity.
- For buy alternatives: map the chosen canonical ingredient to localized retailer product search, present actual offers, **user picks SKU**.
- Require a confirmation action before applying a change. Preserve original recipe; this is not a permanent dataset rewrite.
- Respect culinary constraints: substitutions can alter cooking time, technique, servings and allergen profile. Don't claim a recipe remains equivalent.

## Integration and delivery priorities
P0: Dev 3 returns sample `list[Recipe]`; Dev 2's matcher (already on their branch) uses it; Dev 1 route (already on branch) returns matches; frontend renders.
P1: Vision candidates + confirmation + pantry storage.
P2: Suggested substitutions + manual swap (can start as rules/static candidates); grocery lookup for missing ingredients.
P3: Product caching, richer price comparison, full nutrition preferences, marketplace.

## No-conflict checklist
- [ ] Pull shared schema/docs updates from `origin/main` into every EXISTING feature branch.
- [ ] No one edits `schemas/recipes.py`, `schemas/prices.py`, `schemas/substitutions.py` in a feature branch without agreement.
- [ ] Dev 1 works only on routes and their tests, preserving existing endpoints.
- [ ] Dev 2 works on database, matcher and DB-specific tests, preserving existing code.
- [ ] Dev 3 works on provider integrations and their tests; start `feature/integrations` from updated main.
- [ ] Verify canonical IDs and imported recipes by running a shared sample fixture.
- [ ] Merge PRs in small increments and test both matching and vision with mocks.
- [ ] Do not postpone cross-module integration until last minute.

See [[Recipe Dataset Review]] · [[Prices]] · [[Codex Team Playbook]] · [[Backend Architecture]].
