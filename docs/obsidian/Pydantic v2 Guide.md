---
tags: [refood, backend, pydantic]
---
# Pydantic v2 Guide
Pydantic defines **data contracts**, not database tables, UI components, business logic, or a full HTTP API.

Install `pip install "pydantic>=2,<3"`. All models inherit `BaseModel`. `Field(ge=0)` enforces numerical bounds; `Enum` restricts allowed values; `| None` with a default makes a field optional; `Field(default_factory=list)` avoids shared mutable defaults.

```python
from pydantic import ValidationError
from schemas.recipes import RecipeSearchRequest

incoming = {"ingredients": [{"ingredient_id":"ing_egg","name":"egg"}], "limit":10}
try:
    req = RecipeSearchRequest.model_validate(incoming)
except ValidationError as exc:
    print(exc.errors(include_input=False))

print(req.model_dump(mode="json"))  # JSON-safe dict
print(RecipeSearchRequest.model_json_schema())  # share with frontend
```

## Why this helps three developers
- Developer 1 validates incoming request data and serializes response objects consistently.
- Developer 2 returns `RecipeMatch` and `PantryItem` models from repositories and matchers.
- Developer 3 normalizes provider payloads into `ScanCandidate` or `Recipe` models.
- Invalid payloads fail close to the boundary rather than breaking in another teammate's code.

## Practical limits
Pydantic checks **shape, types, and bounds**, not whether the LLM actually saw eggs, a recipe is safe for an allergy, or a price is fresh. Define business constraints separately. v2 uses `model_validate`, `model_dump`, `model_json_schema` (not v1's `parse_obj`/`dict`/`schema`). Conversions can be permissive; enable stricter validation where correctness matters.

## Flask pseudo-flow
```python
request_model = RecipeSearchRequest.model_validate(request.get_json())
matches = find_recipes(request_model)
response_model = RecipeSearchResponse(results=matches)
return jsonify(response_model.model_dump(mode="json")), 200
```
Handle `ValidationError` with a consistent 422 response; catch malformed JSON separately with 400. Explicitly validate service outputs when receiving untrusted provider data.

See [[Contracts and Decisions]].
