---
tags: [refood, backend, planned]
status: unimplemented
owner: Developer 3 integration; Developer 1 API
---
# Prices

`src/backend/schemas/prices.py` is a placeholder.

**Developer 3:** implement Épiceries.ca adapter `services/grocery_prices.py`; normalize product names, package quantities, retailer, sale price, original price, timestamp, provider URL and ingredient links. **Developer 1:** `GET /api/v1/prices?ingredient_id=...` or `POST /api/v1/prices/compare` and JSON response validation. **Developer 2:** optional cache/persistence if time.

Proposed price record: `ingredient_id`, `product_name`, `store_name`, `package_amount`, `package_unit`, `price_cents`, `currency='CAD'`, `observed_at`, `source_url`, `on_sale`. Unknown store or quantity should be null.

Remember: spending $4 on a 2L carton is distinct from consuming 200mL in a recipe. Price availability is provider-dependent; gracefully return no offers if unavailable.

See [[Backend Architecture]].
