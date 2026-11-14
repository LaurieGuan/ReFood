---
tags: [refood, codex, teamwork, hackathon]
status: working-agreement
---
# Codex Team Playbook

> [!important] Prerequisite
> Implement and verify [[Shared Backend Bootstrap]] **on main**, commit it, then create three branches from the same commit. `AGENTS.md` exists at the Git root and is automatically read by Codex in supported local repository workflows. If using a cloud Codex task, select the actual GitHub repository and the correct branch, not a pasted directory listing.

## Setup for every teammate
1. Clone/pull `https://github.com/Youssef-Hamdani/Hackthon_GIT` and ensure the shared bootstrap is merged on `main`.
2. Run `git status` and `git log -1 --oneline`; check that you have the intended shared base.
3. Create your own branch: `feature/api`, `feature/database`, or `feature/integrations` (coordinate branch names if they exist).
4. Open the **repository root** as the Codex workspace, or select the repository/branch in Codex Cloud. No files need to be individually uploaded when Codex can access the checkout.
5. Tell Codex to read `AGENTS.md`, [[Backend Architecture]], [[Contracts and Decisions]], [[Shared Backend Bootstrap]] and the applicable Python schemas; paste only your role prompt below.
6. Each developer reviews Codex's changes, runs checks, commits and pushes their own branch when ready, then opens a PR. Do not let agents push to `main` independently.

## Common first message (optional; root AGENTS.md is the persistent rules file)
```text
We are building REFOOD for a time-limited hackathon. You are working in the cloned repository on MY current feature branch. First read AGENTS.md, docs/obsidian/Shared Backend Bootstrap.md, docs/obsidian/Backend Architecture.md, docs/obsidian/Contracts and Decisions.md, and relevant src/backend/schemas/*.py. Inspect the actual branch, tree and Git status before implementing. Respect the existing contracts; do not change shared models, app initialization, config, or teammates' files without surfacing the proposal. Implement only my assigned role, keep the code simple, use schema-valid mocks for missing dependencies, and test what you implement. Never commit, push, merge, or change branches without asking. Explain integration assumptions and list actual tests at the end.
```

## Developer 1 — Flask endpoints and orchestration
Branch: `feature/api`. Owned files: `src/backend/routes/`; `app.py` for blueprint registration after shared bootstrap.

```text
Act as Developer 1 (API/orchestration) for REFOOD. Read AGENTS.md and the shared bootstrap plan and inspect the actual Pydantic schemas before writing code. Implement a minimal set of Flask blueprints and route handlers for POST /api/v1/recipes/search, POST /api/v1/scans, GET /api/v1/pantry and PUT /api/v1/pantry, prioritizing a working recipe search first. Use the exact shared Pydantic models for request validation and response serialization; malformed JSON = 400, invalid model = 422, failures use the shared ErrorResponse. The scan endpoint accepts multipart form field "image" and returns candidates without saving inventory. Delegate computation to Developer 2's find_recipes/get_pantry/replace_pantry and Developer 3's scan_fridge; do not implement their business logic. Until they exist, provide clearly marked schema-correct mocks via replaceable service adapters rather than breaking imports. Register only importable blueprints in the existing app factory. Add Flask test-client tests for the working endpoints and report any missing dependencies or agreed signatures. Do not touch database/provider implementations.
```

## Developer 2 — database, pantry persistence and recipe matcher
Branch: `feature/database`. Owned paths: `src/backend/database/`, `src/backend/services/recipe_matcher.py`.

```text
Act as Developer 2 (data/persistence + recommendation engine). Read AGENTS.md, the bootstrap note and the actual schemas. Implement the minimum useful recipe matcher first: find_recipes(request: RecipeSearchRequest) -> list[RecipeMatch], ranking by ingredient coverage and missing items, with normalized IDs; treat unknown quantities explicitly rather than assuming enough stock. Use a small schema-valid recipe fixture to make this testable without MariaDB. Then implement database connection/repository functions for get_pantry(user_id) -> PantryResponse and replace_pantry(user_id, request: PantryUpdateRequest) -> PantryResponse, and recipe retrieval/storage as time permits. Keep ORM/database rows separate from Pydantic objects and use env configuration; importing the app must not require a live database. Do not create Flask endpoints or vision/provider adapters. If schema changes are needed, explain them first; don't modify shared contracts. Add matcher and repository tests and document any DB setup required.
```

## Developer 3 — provider adapters and normalization
Branch: `feature/integrations`. Owned paths: `src/backend/services/vision.py`, `recipe_import.py`, `grocery_prices.py`, `normalizer.py`.

```text
Act as Developer 3 (external data integrations). Read AGENTS.md, the bootstrap note and the actual schemas. Implement normalize_ingredient(source_name: str) -> Ingredient, import_recipes() -> list[Recipe], and scan_fridge(image_bytes: bytes) -> list[ScanCandidate], starting with data normalization and a small predictable recipe fixture. Use the selected TheMealDB or Hugging Face source only after checking its actual shape; map all provider-specific data into shared Pydantic objects. For vision scanning, use a configurable external vision API with credentials only from environment variables; model detections are uncertain suggestions, never confirmed pantry entries, and output quantities are unknown unless plainly justified. Keep provider calls behind functions that can be mocked in tests, use timeouts and actionable errors, and don't require API access at app startup. If time remains, implement an Épiceries.ca price adapter without assuming a grocery package price equals the consumed ingredient cost. Do not edit Flask routes, DB modules or shared schemas without proposing the change. Add fixture tests for messy/multilingual names and provider JSON.
```

## Merge protocol
- Verify branch base, keep commits small, make a PR from each feature branch into `main`.
- Read changed files and run the smoke test + relevant role tests; verify one demo journey end to end after integration.
- If a shared contract must change, propose and merge the schema change into `main` first, then update the three branches.
- Integrate first working path before implementing optional features.
- Never use the existence of a plan or README as evidence an endpoint is implemented.

## Need-to-know Pydantic v2
`MyModel.model_validate(incoming_dict)` validates and parses. `model_dump(mode="json")` creates JSON-safe Python objects. `model_json_schema()` exports a schema for a frontend teammate. Pydantic does not create Flask routes or SQL tables.

See [[Pydantic v2 Guide]].


## Update: existing branches and second-phase prompts
**Use [[Recipe Enrichment and Substitutions]] for all new work.** Dev 1 completed first API prompt; Dev 2 completed first DB/matcher prompt but has NOT run its database/Docker second prompt; Dev 3 has NOT run first integration prompt. Do not restart previous tasks. Both existing branches are behind main and should merge `origin/main` after committing or stashing local work. Main now has extended optional recipe metadata and shared substitutions schema.

**Dev 1 follow-up (on feature/api only):** Read AGENTS.md, [[Recipe Enrichment and Substitutions]], existing route files and new schemas. Preserve tested routes and their mocks. Add provider-backed missing ingredient product search endpoint only after Dev 3 adapter exists; add `POST /api/v1/recipes/substitutions` and `POST /api/v1/recipes/variations` using the shared models, with schema-valid mocks if service isn't implemented. Keep confirmation in frontend; routes never silently mutate the source recipe or pantry. Add tests. Coordinate internal function signatures; no shared schema edits.

**Dev 2 follow-up (on feature/database only):** Read AGENTS.md, [[Recipe Enrichment and Substitutions]], preserve existing matcher and pantry repositories/tests. Implement Docker Compose MariaDB + persistence/recipe upsert using `save_recipes(recipes: list[Recipe]) -> int` and fetch methods. Store optional recipe metadata and source IDs without changing shared schemas. If time, implement pure recipe variation apply/recompute helper; then optional grocery product/offer cache using the existing prices schema. Do not create a second independent importer or rewrite matcher unnecessarily. Avoid requiring DB at startup. Coordinate shared dependencies/config changes first.

**Dev 3 first prompt (on feature/integrations only):** Read AGENTS.md, [[Recipe Enrichment and Substitutions]], dataset/price notes and real schemas. Implement normalized text-only subset of `rahul7star/food-recipes`, stable canonical IDs, recipe import returning `list[Recipe]`, fixture tests. Implement vision image → `ScanCandidate` with uncertainty and no auto-persist. Implement Épiceries.ca search/detail adapter mapped to **existing** `schemas/prices.py`; verify category ID taxonomy live and don't hardcode unchecked enum as truth. For substitutions, implement source-agnostic candidate suggestion from confirmed pantry first, optional grocery alternatives later. Don't alter routes, DB or shared schemas.

Refer to the role prompts in this conversation/coordination for exact acceptance tests. Never have multiple Codex agents modify shared files in parallel.
