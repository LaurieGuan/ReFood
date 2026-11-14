---
tags: [refood, backend, architecture, hackathon]
status: proposed
---
# Backend Architecture

## Responsibilities
| Owner | Area | Files to implement |
| --- | --- | --- |
| Developer 1 — API/orchestration | Flask app, CORS, routes, request/response validation, error handling | `src/backend/app.py`, `routes/scans.py`, `routes/pantry.py`, `routes/recipes.py`, `routes/prices.py` |
| Developer 2 — persistence/matcher | MariaDB tables, repositories, matching and ranking | `database/connection.py`, `database/models.py`, `database/repositories.py`, `services/recipe_matcher.py` |
| Developer 3 — external sources | Vision model, TheMealDB/Hugging Face ingestion, Épiceries.ca, ingredient normalization | `services/vision.py`, `services/recipe_import.py`, `services/grocery_prices.py`, `services/normalizer.py` |

Developer 1 initially owns the shared `schemas/` contracts, but **all three must agree on contract changes**. Modules should import schemas, not each other's private provider models. Do not equate roles with named people until assigned.

## Key workflow
1. React sends multipart image to `POST /api/v1/scans`.
2. Flask calls vision integration; response is `ScanResponse` with uncertain candidates.
3. React shows checkboxes, rename and add controls, then sends a **confirmed** `PantryUpdateRequest` to `PUT /api/v1/pantry`.
4. `POST /api/v1/recipes/search` takes ingredients explicitly for easy testing and returns `RecipeSearchResponse`.
5. Optional prices, preferences, marketplace are additive.

## Rules
- Source-specific formats never leak to React.
- Database ORM models are distinct from Pydantic HTTP/service contracts.
- Unknown quantities are `null`, not invented quantities.
- Grocery package price is not the cost of the recipe quantity used.
- `PUT /pantry` replaces the inventory; use a separate merge endpoint if desired.
- Use stable IDs (e.g. `ing_egg`) and canonical names. Don't assume image recognition implies verified ownership.
- Stub services using schema-correct mock results until each dependency is ready.
- No empty directories in Git: README files are intentional placeholders.

## Linked notes
[[Pydantic v2 Guide]] · [[Preferences]] · [[Prices]] · [[Marketplace]] · [[Contracts and Decisions]]
