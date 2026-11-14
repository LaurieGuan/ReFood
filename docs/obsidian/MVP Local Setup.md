---
tags: [refood, backend, setup, mariadb, hackathon]
status: shared-local-setup
---
# Run REFOOD backend + MariaDB locally (Fedora/Linux)

## Requirements
Python 3.10+, Docker Engine with Compose plugin, and a running Docker daemon. Clone the repo; DO NOT commit any .env or credentials.

## One-time setup from repository root

```bash
cp src/backend/database/.env.example src/backend/database/.env
# Change passwords if desired; this example is LOCAL DEV ONLY.
python -m venv src/backend/.venv
source src/backend/.venv/bin/activate
pip install -r src/backend/database/requirements.txt
```

`.env` is ignored by root `.gitignore`; `.env.example` is tracked. The `--env-file` path **must be passed explicitly**. It avoids needing to export four `MARIADB_*` variables and works under `sudo`, which normally strips the caller's environment.

## Start MariaDB (from repository root)

```bash
sudo docker compose --env-file src/backend/database/.env -f src/backend/database/compose.yaml up -d --wait
sudo docker compose --env-file src/backend/database/.env -f src/backend/database/compose.yaml ps
```

On machines configured for rootless/user Docker, omit `sudo`. If the container reports `healthy`, it is ready to accept database connections. Do not run `down -v` unless you intentionally want to DELETE the database volume. Changing passwords in `.env` will not change existing credentials for an initialized volume.

## Run Flask with MariaDB (from repository root)

The following export matches the default local `.env.example`. If you edited the database username, password, port or name, adjust the URL accordingly. Percent-encode special password characters when constructing a URL.

```bash
source src/backend/.venv/bin/activate
export DATABASE_URL='mysql+pymysql://refood:devpassword@127.0.0.1:3306/refood'
cd src/backend
python -m database.engine
python app.py
```

In a second terminal use `curl http://127.0.0.1:5000/api/v1/health`. Flask needs `DATABASE_URL` only if using persistent storage; without it, the app uses demo fixtures and in-memory pantry. Health 200 alone does not verify the database.

## Seed sample real Hugging Face-derived recipes
Run from `src/backend` with the same `DATABASE_URL` set and Flask in a **separate terminal**:

```bash
python - <<'PY'
from services.recipe_import import import_recipes
from database.catalog import save_recipes, get_recipes
recipes = import_recipes()  # Three captured real dataset rows; no network.
print("Parsed:", len(recipes))
print("Saved:", save_recipes(recipes))
print("Stored:", len(get_recipes()))
PY
```

Verify a real dataset-derived recipe ID (`rahul7star:` rather than `demo_`) appears in POST `/api/v1/recipes/search`. Note: `import_recipes(live=True)` currently fetches at most 100 rows and **does not ingest the full 15,698-row dataset**. Increase catalog size only after demo flow is stable.

## Tests

```bash
cd src/backend
python -m unittest discover -s tests -v
```

The live MariaDB test in `test_mariadb_live.py` is opt-in and requires a SEPARATE disposable `TEST_DATABASE_URL` database. Do not reuse the regular refood database for destructive tests.

## Known integration gaps
- Frontend branch still uses `mockApi`; adapt to actual Flask Pydantic contract before real UI demo.
- `/api/v1/recipes/variations` currently looks for `calculate_variation(request)`, but Dev 2 supplies `apply_swaps(recipe, swaps, pantry)`; needs a lookup/orchestration adapter.
- Vision needs an actual API key and model configuration plus a real-photo check.
- Épiceries.ca query results are keyword matches, not guaranteed culinary matches (e.g. soap for lait). Category plus semantic relevance filtering required.
- Live grocery adapter identifies as `REFOOD-Hackathon/0.1` rather than the `urllib` default, which Cloudflare previously rejected.

See [[Recipe Enrichment and Substitutions]], [[Prices]], [[Codex Team Playbook]].
