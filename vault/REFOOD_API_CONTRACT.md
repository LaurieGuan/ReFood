# REFOOD — API & Data Contract (MVP v0.1)

**Status:** Proposed team contract, not an implemented API.  
**Stack:** React or Vue → Flask REST API → recipe dataset and MariaDB (optional initially).  
**Base URL:** `/api/v1`  
**Canonical API language:** English field names and enum values; the UI may be in French.  
**Transport:** JSON UTF-8, except image upload with `multipart/form-data`.  
**IDs:** Opaque strings. Never assume numeric IDs.  
**Currency:** CAD, two-decimal amounts encoded as strings where money is returned (`"4.99"`), or integer cents in internal calculations.  
**Dates:** ISO 8601 UTC timestamps.  
**Units:** Standardized `g`, `ml`, `unit`, with `unknown` where a quantity cannot be inferred.  
**Ownership:** The Flask backend owns validation, normalization, persistence, recommendation logic, and external API calls. The frontend never calls MariaDB directly and never exposes third-party API keys.

## 1. MVP end-to-end journey

1. Frontend uploads fridge/pantry photo to `POST /api/v1/scans`.
2. Flask calls a vision provider and returns **proposed** ingredients, without modifying the user's inventory.
3. Frontend renders checkboxes and editable names/quantities; user can remove, correct, or add items.
4. Frontend submits confirmed items to `PUT /api/v1/pantry`.
5. Frontend calls `POST /api/v1/recipes/search` using the **confirmed inventory** and optional filters.
6. Flask returns recipes with available/missing ingredients and coverage scores. For costs, return `null` if price data are not available.
7. User opens a recipe and (optionally) requests price offers for missing ingredients.

**Invariant:** A scan suggestion is never silently treated as confirmed inventory.

## 2. Data models

### Ingredient

```json
{
  "id": "ing_tomato",
  "name": "tomato",
  "display_name": "Tomate",
  "aliases": ["tomatoes", "tomates"]
}
```

- `id` is stable and canonical; do not use display text as a join key.
- The backend should canonicalize both image detections and recipe ingredients.
- For a hackathon, a manually maintained alias dictionary is sufficient.

### Scan candidate

```json
{
  "candidate_id": "cand_1",
  "ingredient_id": "ing_tomato",
  "name": "tomato",
  "certainty": "high",
  "quantity": null,
  "unit": "unknown"
}
```

- `certainty`: `high | medium | low` — a model's subjective estimate, **not** a calibrated probability.
- `ingredient_id` can be `null` for unknown/unmapped ingredients; users may correct them.
- The app must not infer precise amounts or sealed-container contents from images.

### Pantry item

```json
{
  "id": "pantry_101",
  "ingredient_id": "ing_tomato",
  "name": "tomato",
  "quantity": 2,
  "unit": "unit",
  "remaining_fraction": 1.0,
  "source": "scan_confirmed"
}
```

- `quantity`: nullable nonnegative number; `null` = amount unknown.
- `unit`: `unit | g | ml | unknown`.
- `remaining_fraction`: optional number 0–1, for issue #2. It is a fraction of the **original item quantity**, not a substitute for physical units.
- `source`: `manual | scan_confirmed`.
- If `quantity` is unknown, recipe matching may check *presence* but must not claim sufficient quantity.

### Recipe

```json
{
  "id": "recipe_123",
  "title": "Tomato omelette",
  "source": "themealdb",
  "source_url": null,
  "ingredients": [
    {"ingredient_id": "ing_egg", "name": "egg", "quantity": 2, "unit": "unit", "essential": true},
    {"ingredient_id": "ing_tomato", "name": "tomato", "quantity": 1, "unit": "unit", "essential": true}
  ],
  "instructions": "...",
  "minutes": null,
  "servings": null,
  "dietary_tags": [],
  "allergens": [],
  "nutrition": null
}
```

- Do not fabricate missing metadata. Use `null` or `[]` for unavailable values.
- Allergy flags inferred from titles alone are not sufficient. For unknown data, indicate `dietary_verification: "unknown"` in results rather than claiming safety.
- `source` distinguishes TheMealDB, Hugging Face and any other imports. Keep each source's original ID mapped to the canonical recipe ID.

### Preferences

```json
{
  "dietary_restrictions": ["vegetarian"],
  "excluded_ingredient_ids": ["ing_peanut"],
  "allergens": ["peanut"],
  "max_budget_cad": "15.00",
  "max_minutes": 30,
  "servings": 1
}
```

- Dietary restrictions use documented enums; allergens are explicit strings from a controlled list.
- All filters optional. `null` means no constraint.
- Avoid an allergy-safe claim if ingredients or cross-contact data are incomplete.

## 3. API endpoints — Core MVP

### `GET /api/v1/health`

**200** `{"status":"ok","api_version":"v1"}`

### `POST /api/v1/scans`

**Request:** `multipart/form-data`, field `image` (JPEG/PNG/WebP, maximum size determined by team), optional field `context=fridge|pantry`.

**200:**

```json
{
  "scan_id": "scan_001",
  "candidates": [
    {"candidate_id":"cand_1","ingredient_id":"ing_egg","name":"egg","certainty":"high","quantity":null,"unit":"unknown"},
    {"candidate_id":"cand_2","ingredient_id":"ing_tomato","name":"tomato","certainty":"medium","quantity":null,"unit":"unknown"}
  ],
  "warnings": ["Some contents are obscured; confirm the list manually."]
}
```

**Important:** This endpoint does not store candidates in the pantry. `scan_id` can be transient; persistence is optional. Errors: `400` invalid file, `413` oversized upload, `502` vision service failed, `504` vision service timeout.

### `GET /api/v1/pantry`

**200:** `{"items":[PantryItem, ...]}`.

### `PUT /api/v1/pantry`

**Request** (replace current inventory with confirmed list):

```json
{
  "items": [
    {"ingredient_id":"ing_egg","name":"egg","quantity":6,"unit":"unit","remaining_fraction":1,"source":"scan_confirmed"},
    {"ingredient_id":"ing_tomato","name":"tomato","quantity":null,"unit":"unknown","remaining_fraction":null,"source":"manual"}
  ]
}
```

**200:** `{"items":[PantryItem, ...]}`.

A full replacement is deliberately simple for the MVP. Do **not** send unconfirmed scan candidates. New manual items may have `ingredient_id:null`; backend normalizes and returns canonical IDs. For multi-user development, decide on a demo user context; authenticated accounts are not essential for a local demo.

### `POST /api/v1/recipes/search`

**Request:**

```json
{
  "ingredient_ids": ["ing_egg", "ing_tomato", "ing_milk"],
  "preferences": {
    "dietary_restrictions": [],
    "excluded_ingredient_ids": [],
    "allergens": [],
    "max_budget_cad": "15.00",
    "max_minutes": null,
    "servings": 1
  },
  "limit": 10
}
```

**200:**

```json
{
  "recipes": [
    {
      "id": "recipe_123",
      "title": "Tomato omelette",
      "match": {
        "coverage": 1.0,
        "matched_ingredient_ids": ["ing_egg", "ing_tomato"],
        "missing_ingredient_ids": [],
        "quantity_verified": false
      },
      "estimated_missing_cost_cad": null,
      "dietary_verification": "unknown",
      "minutes": null,
      "image_url": null
    }
  ],
  "total": 1
}
```

- `coverage` is a number from 0 to 1, based on *presence* of required ingredients, not the probability of successfully cooking the recipe.
- When quantity information is incomplete, `quantity_verified` must be `false`.
- `estimated_missing_cost_cad = null` means not priced, **never $0**.
- Budget filters should not discard unpriced recipes without an explicit policy. For the demo, sort known prices separately and mark unpriced entries.
- Allergens and dietary restrictions should be checked against verified data; unknown should be presented as unknown.

### `GET /api/v1/recipes/{recipe_id}`

**200:** full `Recipe` object. **404:** unknown recipe.

## 4. API endpoints — Optional extensions

### `GET /api/v1/ingredients?q=tom`

Returns `{"items":[Ingredient, ...]}` for manual ingredient autocomplete. Can use a small static dictionary.

### `POST /api/v1/prices/compare`

**Request:** `{"ingredient_ids":["ing_milk"],"region":"Montreal, QC"}`.

**Response:**

```json
{
  "offers": [
    {
      "ingredient_id":"ing_milk",
      "product_name":"Example 2 L milk",
      "merchant":"Example store",
      "package_quantity":2,
      "package_unit":"L",
      "price_cad":"4.99",
      "currency":"CAD",
      "retrieved_at":"2026-11-14T15:00:00Z",
      "source":"epiceries.ca",
      "product_url":null
    }
  ],
  "unpriced_ingredient_ids":[]
}
```

This is an **illustrative contract**, not a claim about currently available store offers. Pricing integration must normalize grocery product packages separately from recipe consumption amounts. Preserve the source and retrieval time. Do not call an external API from the frontend if it requires secrets.

### `GET /api/v1/preferences` and `PUT /api/v1/preferences`

Return or accept the `Preferences` object defined above.

### `GET /api/v1/recipes/favorites`, `POST /api/v1/recipes/{id}/favorite`, `DELETE /api/v1/recipes/{id}/favorite`

Use stable recipe IDs.

### Marketplace — stretch goal

- `GET /api/v1/exchanges` → `{ "items": [ExchangeOffer] }`
- `POST /api/v1/exchanges` → creates an offer
- `POST /api/v1/exchanges/{id}/interests` → records a student's interest

Example ExchangeOffer:

```json
{
  "id":"offer_001",
  "creator_id":"demo_user_1",
  "item_name":"Rice",
  "quantity":1,
  "unit":"kg",
  "seeking":"Chickpeas",
  "pickup_area":"Montréal",
  "status":"open",
  "created_at":"2026-11-14T15:00:00Z"
}
```

Avoid publishing exact home addresses. Exchange listings are distinct from cooked-meal recipes. If cooked meals are added, treat allergens and preparation/storage details as unverified unless explicitly provided.

### Directions — stretch goal

Frontend may construct a provider-approved map search/directions URL using the store's **actual** address; backend need not compute routes in the MVP.

## 5. Error response contract

Every non-2xx response from Flask should have this structure:

```json
{
  "error": {
    "code": "INVALID_IMAGE",
    "message": "Upload a valid JPEG, PNG or WebP image.",
    "details": null
  }
}
```

Suggested status codes: `400` bad request, `404` not found, `413` too large, `422` invalid field values, `500` unexpected server error, `502` upstream failure, `504` upstream timeout. Never return raw HTML stack traces in API responses.

## 6. Integration rules

1. **One canonical ingredient ID** across vision, pantry, recipes, filters, and price lookup. UI translations are presentation-only.
2. **Backend owns inventory truth.** Scan candidates are suggestions until submitted by the user.
3. **Backend normalizes aliases** (`tomatoes`, `tomate` → `ing_tomato`). Do not duplicate this in every frontend component.
4. **Do not assume quantities from photos.** Unknown amount is explicit `null`.
5. **Do not conflate ingredient consumption cost and package purchase cost.** Missing price = `null`.
6. **Pick one React/Vue framework quickly.** Both consume the same API.
7. **Use environment variables** for provider keys and database connection; no secrets in commits.
8. **Enable CORS only for known local frontend origin** during development (e.g., `http://localhost:5173`).
9. **Provide mock fixtures before backend integration.** Teammates can build UI and services in parallel against these payloads.
10. **Basic tests:** no confirmed items, duplicate ingredients, uncertain detection, invalid image, no matching recipe, unknown price, missing recipe, upstream vision failure.

## 7. Suggested Python/JS organization

```text
repo/
  backend/
    app.py
    routes/
      scans.py
      pantry.py
      recipes.py
      prices.py
    services/
      vision.py
      ingredient_normalizer.py
      recipe_matcher.py
      grocery_prices.py
    data/
      recipes.json
      ingredient_aliases.json
  frontend/
    src/
      api/client.js
      components/ScanReview.jsx
      components/RecipeCard.jsx
  contracts/
    examples/
      scan-response.json
      pantry-response.json
      recipes-response.json
  README.md
```

Use MariaDB repository/model modules only if setup is already fast enough. For the demo, SQLite or even an in-memory store can unblock the team; the route contracts should remain unchanged.

## 8. Issue audit and additions

**Existing issues read:** #1–#18. Most issues have only titles; #2 explicitly proposes remaining-quantity tracking with a fractional slider. These are feature intents, not detailed acceptance criteria.

**High-priority proposed new issues:**

- `API contract v1 + JSON fixtures` — specify endpoint paths, request/response schemas, errors, ownership.
- `Scan review and manual correction` — allow checking detected items, editing names, adding missing items, then committing confirmed inventory.
- `Canonical ingredient normalization + recipe import` — connect TheMealDB/Hugging Face recipes and visual detections to a shared dictionary; support source IDs.
- `Recipe ranking and missing ingredients` — return coverage, missing list and honest quantity/cost uncertainty.
- `Vertical slice integration / demo fixtures` — one working frontend → Flask → matcher path with a fallback fridge image.

**Medium-priority proposed issue:** `Price normalization, freshness and missing-price handling` — grocery package prices vs ingredient quantities; merchant/source/timestamp; unknown prices.

**Avoid duplicate issues:** Existing #4/#5/#10/#11/#12 have overlapping dietary/allergy concerns; organize as parent/subtasks instead of starting new duplicates. Existing #3 and #18 should clarify whether favorites and saved recipes are distinct.

## 9. Acceptance test for the main demo

Given a mock fridge photo with eggs, tomatoes and milk, `/scans` returns 3 candidates. The user unchecks milk and adds rice. `/pantry` receives and returns exactly the confirmed set. `/recipes/search` returns recipes with ingredient coverage and a missing-ingredient list. If no prices are known, it returns `null` rather than `0` for estimated missing cost. A recipe detail opens via ID. This journey is complete before marketplace development starts.

## 10. Decisions to announce in the team chat

- Agree on **React or Vue** and a local frontend port.
- Agree on **ingredient canonicalization** and who owns aliases.
- Agree on **recipe source** (TheMealDB vs Hugging Face vs both), and a stable internal schema.
- Agree on **scan candidates vs confirmed pantry items** as different states.
- Agree on **money and quantity semantics**, especially unknown values.
- Assign one person to maintain mock JSON contract examples while coding progresses.
