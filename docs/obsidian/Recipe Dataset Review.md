---
tags: [refood, recipes, dataset, architecture]
status: source-reviewed
owner: Developer 3
---
# Recipe Dataset Review

## Original: corbt/all-recipes
https://huggingface.co/datasets/corbt/all-recipes
- 2,147,248 train rows, ~807MB download, Parquet.
- **Only column:** `input`, one free-form string containing title, ingredients and directions. Example rows visible in dataset viewer.
- Requires robust text parsing and ingredient normalization. No separate image, time, tags, nutrition columns verified; dataset card says more information needed. License is not clearly documented.
- **Not recommended as primary hackathon source** unless a clean preprocessed subset already exists.

## Recommended primary: rahul7star/food-recipes
https://huggingface.co/datasets/rahul7star/food-recipes
- ~15.7k rows; structured fields `name,recipe_id,minutes,description,tags,steps,n_steps,ingredients,n_ingredients,nutrition,rating,num_ratings,markdown,image`.
- Advertises Apache-2.0; card also points to upstream Food.com license, so check source rights if publishing beyond hackathon.
- Useful for ingredient matching, meal time filters and instructions without parsing a giant text blob. Some values are implausible/high (e.g. minutes up to 20k), so filter. Images are rendered recipe cards, not necessarily food photographs. Import only a filtered sample (~500–3000) without image blobs.
- Inspect a real sample through HF dataset viewer or streaming before trusting exact formats; some recipe fields may need conversion.

## Alternative: Zappandy/recipe_nlg
https://huggingface.co/datasets/Zappandy/recipe_nlg
- ~400k train rows, advertised Apache-2.0, title + ingredients + directions + NER text.
- Ingredients/directions separated using the `<extra_id_99>` token; less metadata but still cleaner than corbt. Good fallback if primary sampling/download fails.

## Decision for first working demo
Developer 3 should return Pydantic `list[Recipe]`, e.g. via `import_recipes() -> list[Recipe]`, with stable `recipe_id` prefixed by source, canonical `IngredientWithQuantity` identity, instructions list, optional preparation time. Don't claim quantities where not present.

Developer 2 owns `save_recipes(recipes: list[Recipe]) -> int` and upserts into DB. Matching should work on fixtures even if DB unavailable. Later only missing ingredients of selected ranked recipes are searched on Épiceries.ca.

The existing `Unit` enum is limited (g, kg, ml, l, piece, unknown); preserve unparsed recipe quantities as unknown for now rather than force fake measurements or silently add new enum entries across branches.

See [[Prices]].
