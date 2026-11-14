# REFOOD — Codex repository instructions

This file is shared by every Codex working in this repository. Read it before changing code. This repository is a time-limited student hackathon: prioritize one working end-to-end demo, small understandable changes, and compatibility over abstractions.

## Context map
- Start with `docs/obsidian/Shared Backend Bootstrap.md` (plan; not proof code exists).
- Read `docs/obsidian/Backend Architecture.md` and `docs/obsidian/Contracts and Decisions.md`.
- For models, read actual `src/backend/schemas/*.py`; **code is authoritative** if notes disagree.
- For your assigned role, see `docs/obsidian/Codex Team Playbook.md`.
- Backend setup: `src/backend/README.md`.

## Always
1. First inspect branch, Git status, actual files, and shared schemas. Never assume planned files exist.
2. Work ONLY on the current task and your developer-owned paths. Don't rewrite teammates' files or unrelated code.
3. Reuse Pydantic v2 schemas from `src/backend/schemas/`. Respect actual required fields, nested quantities, enums and response shapes. Don't silently alter shared contracts or invent alternate models.
4. Flask routes handle HTTP/Pydantic validation and orchestration; database and external adapters don't import Flask or return Flask Response objects.
5. Normalize external data into canonical ingredient/recipe objects. Missing information stays unknown/null, never invented. Image recognition produces reviewable candidates, not confirmed inventory.
6. Use `/api/v1` endpoints, snake_case JSON, consistent errors. For serializing models use `model_dump(mode="json")`; for incoming data use `model_validate`.
7. No unnecessary new dependencies, new frameworks, auto-generated architectural rewrites, or premature marketplace features.
8. Add focused tests or runnable demonstrations; run available checks and report what actually ran. Never claim unrun tests passed.
9. No secrets in commits/logs. Use environment variables for keys and credentials. Do not make app startup depend on external credentials or DB connectivity.
10. Before changing `schemas/`, `app.py`, `config.py`, shared dependency files, or other developer-owned areas, describe the required change and ask the team to coordinate. Don't make silent cross-branch edits.
11. At completion, report changed files, test results, API shapes and integration instructions, known issues. Do not commit, push, merge or alter branch history unless explicitly asked by your human teammate.

## Ownership once shared bootstrap is merged
- **Developer 1 / API**: `src/backend/routes/`; blueprint wiring in `src/backend/app.py` only after bootstrap.
- **Developer 2 / Database + matching**: `src/backend/database/`, `src/backend/services/recipe_matcher.py`.
- **Developer 3 / Integrations**: `src/backend/services/vision.py`, `recipe_import.py`, `grocery_prices.py`, `normalizer.py`.
- **Shared**: `src/backend/schemas/`, bootstrap/config/dependencies; coordinate all edits.

## Priority
P0: manual confirmed ingredients → recipe search → ranked matches.
P1: photo → detected candidates → user correction → pantry.
P2: budget/prices/preferences.
P3: barter marketplace, nutrition extras, maps.

If blocked on another developer's implementation, use schema-valid mocks behind the agreed interface and identify the mock clearly. Avoid making a second incompatible implementation of your teammate's component.

## Updated shared decision: recipe enrichment + substitutions (2026-11-14)
- Read `docs/obsidian/Recipe Enrichment and Substitutions.md` before implementing recipes, grocery data or swaps.
- Dataset is `rahul7star/food-recipes`; import text-only samples, do not download image-heavy dataset indiscriminately.
- Source metadata has been added to `schemas/recipes.py` as **optional** fields; `schemas/prices.py` already contains grocery product/offer data. Reuse these shared models. New `schemas/substitutions.py` contains suggested swaps and confirmed recipe variations.
- Don't change actual source recipe ingredients/steps after a user swap. Show an explicit user-approved variation; recompute missing items; original nutrition/instructions may no longer apply.
- The source/category enum from teammates is unverified against the live Épiceries.ca categories endpoint. Verify before strict filtering.
- Dev 1 & Dev 2 have existing feature branch work. They must **integrate new main into their branch**, not discard or regenerate their first prompt's work. Dev 3 starts own integration branch from updated main. Never force-push/reset other people's branches.
