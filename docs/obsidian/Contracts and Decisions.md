---
tags: [refood, contracts]
status: proposed
---
# Contracts and Decisions

## Implemented schema files
- `ingredients.py`: `Unit`, `Certainty`, `Ingredient`, `IngredientQuantity`, `IngredientWithQuantity`.
- `scanning.py`: `ScanCandidate`, `ScanResponse`.
- `pantry.py`: `PantryItem`, `PantryResponse`, `PantryUpdateRequest`.
- `recipes.py`: `Recipe`, `RecipeMatch`, `RecipeSearchRequest`, `RecipeSearchResponse`.
- `common.py`: `APIError`, `ErrorResponse`.

## Suggested internal function interfaces
Developer 3: `scan_fridge(image_bytes: bytes) -> list[ScanCandidate]`, `normalize_ingredient(source_name: str) -> Ingredient`, `import_recipes() -> list[Recipe]`.
Developer 2: `find_recipes(request: RecipeSearchRequest) -> list[RecipeMatch]`, `get_pantry(user_id: str) -> PantryResponse`.
Developer 1: `POST /api/v1/scans`, `PUT /api/v1/pantry`, `GET /api/v1/pantry`, `POST /api/v1/recipes/search`.

These are **proposals**, not implemented code. Align their signatures before writing adapters.

## Decisions for the team
1. Canonical ID format and whether unknown detected foods may use temporary candidate IDs.
2. Inventory ownership: demo user/session ID or real authentication?
3. Recipe normalization across English/French labels and measurement units.
4. Recipe match scoring and how unknown quantities affect it.
5. Whether nutrition, marketplace and price comparison are stretch goals.
6. Which data source is primary: TheMealDB or Hugging Face.
