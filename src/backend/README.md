# REFOOD backend

Python 3.10+ (recommend 3.11+), Flask, Pydantic v2, planned MariaDB.

## Install
```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On direct interactive first run (`python app.py`), the backend creates an ignored `.env` and prompts securely for a Gemini API key (Enter to skip). If `database/.env` already exists, it also configures `DATABASE_URL` for persistent MariaDB. No interactive prompt runs in tests, imports or CI. Existing shell environment variables take precedence over `.env`.

## Run and test
From `src/backend`, with the virtual environment activated:
```bash
python app.py
python -m unittest discover -s tests -v
```
`GET /api/v1/health` returns HTTP 200 with `{"status":"ok","service":"refood"}`.
`create_app(test_config=None)` loads environment settings, then applies test overrides.
See `.env.example` for local settings. `python app.py` loads `src/backend/.env` automatically. This file is already covered by root `.gitignore`; never commit credentials. `DATABASE_URL` is required for persistent database use; omitting it uses in-memory/demo fallback.

## Add a resource blueprint
Create `routes/<resource>.py` with a uniquely named Flask `Blueprint`. Import and
register it explicitly in `routes/__init__.py` using `/api/v1/<resource>` as the
prefix; define resource-relative paths inside the module. Register only implemented
routes. Keep service and database initialization out of imports and the factory.

Use `validate_request(RequestModel)` from `routes.http_utils` for JSON requests,
then call the service and return `json_response(ResponseModel, result)`.
These helpers use `model_validate` and `model_dump(mode="json")`.
Missing/non-JSON or malformed bodies return 400; request schema failures return
422. Response validation failures return a private 500, because they are server
errors. Central errors follow the existing `ErrorResponse` schema:
`{"error":{"code":"VALIDATION_ERROR","message":"Invalid request","details":{"errors":[]}}}`.
Other HTTP errors (including 404 and 405) also return JSON. Unexpected errors use
`INTERNAL_SERVER_ERROR` and `details: null` without exposing exception text.
Health checks only confirm that the Flask application is running.

- `schemas/`: shared Pydantic v2 models (architecture/contract owner: Developer 1; agreed by all)
- `routes/`: HTTP endpoints / Flask (Developer 1)
- `database/`: persistence, recipe matching under services (Developer 2)
- `services/`: external vision, recipe imports, price adapters, normalization (Developer 3); matcher (Developer 2)
- `tests/`: shared

Obsidian-ready documentation: `../../docs/obsidian/`.
Pydantic: `model_validate(data)` converts and validates inbound dictionaries; `model_dump(mode="json")` serializes; `model_json_schema()` produces machine-readable JSON Schema.

**Contract conventions:** snake_case fields; stable canonical ingredient IDs; unknown quantity = amount null and unit unknown; scans produce candidates, never directly save pantry; prices expressed as integer CAD cents when implemented; API JSON vs multipart uploads. Avoid interpreting model certainty as calibrated probability.

**Open decisions:** Whether the recipe search receives ingredients explicitly (recommended for demo); precise normalization strategy; when scanned additions merge vs replace saved pantry; dietary restrictions are not allergy guarantees.
