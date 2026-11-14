---
tags: [refood, backend, planned]
status: unimplemented
owner: Developer 1 API; Developer 2 database
---
# Preferences

`src/backend/schemas/preferences.py` is currently a placeholder. Implement `Preferences` with dietary restrictions (vegan, vegetarian, halal, etc.), allergen exclusions, disliked ingredients, maximum preparation time, optional calories/macros, budget in CAD cents and optional serving count.

**Developer 1:** endpoints such as `GET/PUT /api/v1/preferences` and filter validation. **Developer 2:** persistence and apply filters in recipe matcher. **Developer 3:** optional source mapping from recipe tags to canonical preferences.

Differentiate preferences from hard exclusions. No dataset tags can guarantee allergen safety; unknown allergy metadata should be represented as unknown, not safe. Avoid building all filters before the scan→recipe journey works.

See [[Backend Architecture]].
