---
tags: [refood, architecture, bootstrap, branching]
status: implementation-plan
owner: all-backend-developers
---
# Shared Backend Bootstrap — Before Branching

> [!important] Goal
> Establish and **test** a minimal Flask application on `main` so Developer 1 (HTTP), Developer 2 (database/recipe engine), and Developer 3 (providers/normalization) can branch from the exact same working commit. Do not build a generic framework; keep this to a small set of boring conventions.

## Timebox and ownership
Aim for 15–25 minutes total if working together. Assign one person to type each shared file while everyone reviews it; do **not** have three people simultaneously edit `main`. Merge/bootstrap commit first, then create branches. If setup takes too long, prioritize a working health check + schemas over abstractions.

| Step | Files | Lead | All three agree on |
|---|---|---|---|
| Flask app factory | `src/backend/app.py` | Developer 1 | `create_app(test_config=None)` behavior, blueprint loading |
| Error + request conventions | `src/backend/routes/errors.py` or `http_utils.py` | Developer 1 | JSON errors, 400 vs 422, JSON/multipart validation |
| Shared Pydantic models | `src/backend/schemas/*.py` (already added) | All | IDs, optional values, API version, responses |
| Adapter function signatures | `src/backend/services/` and `database/` module contract notes | Developers 2 + 3 | Signatures and return types; no Flask dependencies |
| Config and dependency setup | `src/backend/config.py`, `requirements.txt`, `.gitignore`, `.env.example` | Developer 2 | DB URL, API keys, safe defaults, test mode |
| Smoke test | `src/backend/tests/test_health.py` | Developer 3 | Application imports and `GET /api/v1/health` returns HTTP 200 |

**Do not commit secrets or real `.env` values.**

## Minimal app factory to agree on (planned code, not yet implemented)

```python
# src/backend/app.py
from flask import Flask, jsonify
from flask_cors import CORS

def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    if test_config:
        app.config.update(test_config)
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    @app.get("/api/v1/health")
    def health():
        return jsonify({"status": "ok", "service": "refood"}), 200

    # Register only real, importable blueprints.
    # from routes.recipes import recipes_bp
    # app.register_blueprint(recipes_bp, url_prefix="/api/v1/recipes")

    return app

if __name__ == "__main__":
    create_app().run(debug=True)
```

The shared factory should **not** import a MariaDB driver, instantiate an external AI SDK, load the entire recipe dataset, or call external services at module import time. Configure those later or lazily, so health checks and mock endpoints work without credentials.

## HTTP contracts (shared conventions)
- Prefix `/api/v1`. JSON field names use `snake_case`. Use Pydantic v2 `BaseModel`.
- For JSON endpoints: `request.get_json()` → `MyRequest.model_validate(...)` → call service → `MyResponse.model_validate(...)` → `jsonify(response.model_dump(mode="json"))`.
- Handle malformed/missing JSON as **400**, schema validation errors as **422**, missing resources as **404**, unexpected backend failures as **500**. Error body follows `schemas.common.ErrorResponse`, e.g. `{"error":{"code":"VALIDATION_ERROR","message":"Invalid request","details":null}}`.
- `POST /api/v1/scans` accepts `multipart/form-data` with an `image` file; validates content type and size, invokes vision adapter, returns `ScanResponse`. **Never write detections directly to pantry**.
- `PUT /api/v1/pantry` accepts `PantryUpdateRequest`; replace pantry (not merge) in initial contract.
- `POST /api/v1/recipes/search` accepts `RecipeSearchRequest`; returns `RecipeSearchResponse`, no authentication required for core demo.
- To avoid filename collisions, endpoint handlers go in `routes/` and provider/service logic in `services/`.

## Internal interfaces (agree before splitting)
```python
# Developer 3 — external integrations
scan_fridge(image_bytes: bytes) -> list[ScanCandidate]
normalize_ingredient(source_name: str) -> Ingredient
import_recipes() -> list[Recipe]

# Developer 2 — persistence and matching
find_recipes(request: RecipeSearchRequest) -> list[RecipeMatch]
get_pantry(user_id: str) -> PantryResponse
replace_pantry(user_id: str, request: PantryUpdateRequest) -> PantryResponse
```
For the demo, choose one fixed `demo_user` ID or an optional session header, **not** a partially implemented login system. Do not make a database query mandatory to construct Flask app. These interfaces are proposed and should be adjusted together **before branching**; avoid changing shared schemas afterward without notifying everyone.

## Request lifecycle
```text
React
  │ HTTP (JSON or multipart)
  ▼
Flask route (Developer 1)
  │ parses request / validates with Pydantic
  ▼
Service or repository (Developer 2/3)
  │ returns shared Pydantic model or compatible dict
  ▼
Flask route validates response and serializes JSON
  ▼
React
```

**Provider data adapter chain:** external recipe/vision/grocery payload → Developer 3 normalizer → canonical Pydantic models → Developer 2 matching/storage → Developer 1 HTTP response. Database ORM/table models stay separate from Pydantic schemas.

## Minimum branch-ready checklist
- [ ] `cd src/backend && pip install -r requirements.txt` completes.
- [ ] `python app.py` starts without API keys or database credentials.
- [ ] `GET http://127.0.0.1:5000/api/v1/health` returns `{"status":"ok","service":"refood"}`.
- [ ] `python -c "from schemas.recipes import RecipeSearchRequest; print(RecipeSearchRequest.model_json_schema())"` works.
- [ ] One invalid JSON/schema payload produces the agreed error response (when a JSON endpoint is registered).
- [ ] `.env.example` documents expected config, secrets are ignored.
- [ ] Changes committed to `main`, each developer has fetched the same base commit.

## Branch ownership and integration
```bash
git switch main
git pull --ff-only
git switch -c feature/api
# Others start from main using feature/database and feature/integrations
```
Developer 1: `routes/`, HTTP wiring, `app.py` blueprint additions. Developer 2: `database/`, `services/recipe_matcher.py`. Developer 3: `services/vision.py`, `services/recipe_import.py`, `services/grocery_prices.py`, `services/normalizer.py`. All can read `schemas/` but changes there require explicit agreement and should be merged first.

- Commit frequently and open small pull requests; **integrate first working slice early**, not when time expires.
- Once a branch is open, rebase or merge fresh `main` before its PR; resolve conflicts together.
- Bootstrap owns `app.py`; later Developer 1 is the **only** person editing blueprint registration to reduce conflicts.
- If a teammate is blocked, return schema-valid hardcoded/mock values instead of waiting.
- The first integrated vertical slice should be **manual pantry ingredients → recipe search**; then add photo detection and pantry persistence.

## Scope exclusions for bootstrap
No authentication, no actual database migrations, no price comparison, no marketplace, no generic dependency injection framework. Those are implementation tasks, not prerequisites for branching.

## Companion notes
[[Backend Architecture]] · [[Contracts and Decisions]] · [[Pydantic v2 Guide]]
