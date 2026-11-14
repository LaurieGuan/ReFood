# REFOOD backend

Python 3.10+ (recommend 3.11+), Flask, Pydantic v2, planned MariaDB.

## Install
```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

This commit defines **contracts and the directory skeleton only**. It does not yet provide a runnable Flask server or database migrations.

- `schemas/`: shared Pydantic v2 models (architecture/contract owner: Developer 1; agreed by all)
- `routes/`: HTTP endpoints / Flask (Developer 1)
- `database/`: persistence, recipe matching under services (Developer 2)
- `services/`: external vision, recipe imports, price adapters, normalization (Developer 3); matcher (Developer 2)
- `tests/`: shared

Obsidian-ready documentation: `../../docs/obsidian/`.
Pydantic: `model_validate(data)` converts and validates inbound dictionaries; `model_dump(mode="json")` serializes; `model_json_schema()` produces machine-readable JSON Schema.

**Contract conventions:** snake_case fields; stable canonical ingredient IDs; unknown quantity = amount null and unit unknown; scans produce candidates, never directly save pantry; prices expressed as integer CAD cents when implemented; API JSON vs multipart uploads. Avoid interpreting model certainty as calibrated probability.

**Open decisions:** Whether the recipe search receives ingredients explicitly (recommended for demo); precise normalization strategy; when scanned additions merge vs replace saved pantry; dietary restrictions are not allergy guarantees.
