---
tags: [refood, backend, prices, epiceries]
status: contract-defined-provider-not-yet-tested
owner: Developer 3 adapter; Developer 2 persistence; Developer 1 HTTP
---
# Prices — Épiceries.ca source contract

## Verified from documentation (not a successful live API call)
Official source: https://www.epiceries.ca/developers
Base URL `https://epiceries.ca/api` (public GET, no API key). Search: `?endpoint=search&q=lait&sort=price_asc&limit=10`. `q` >=2 characters. API returns `{"ok":true,"data":{"results":[...]}}`. Search results include `id,name,brand,size,price,unitPrice,store,discounted,category,image,link,url,updated`; pagination `count,limit,offset,hasMore`. See source documentation for field meaning.

`GET ?endpoint=product&id=...` includes `prices` array with `store,price,discounted,size,unitPrice,link,timestamp,date`. The top-level `store` and `price` mean **lowest listed store and price**, not all offers. Supported retailers: maxi, iga, superc, metro, provigo, walmart. The docs say response cache 5 min, provider data refreshed weekly, courtesy of provider; source attribution required and rate limited to a few requests/sec. Cache results; retain source/time. Do not represent them as verified store availability.

**Discount:** `discounted` is Boolean. Search does **not** document a prior-price/discount-percent field. Don't fabricate percentages. The optional `storeproduct` endpoint has a separate `deal` score based on historical observations.

## Actual Pydantic models (implemented)
Read `src/backend/schemas/prices.py`:
- `GroceryProduct`: provider ID, name, brand, size, category, image, links, cheapest price/store, unit price, discount flag, updated timestamp, `store_prices` and `raw_payload`.
- `StorePrice`: store-specific price/size/discount/link/time.
- `UnitPrice`: `value`, `unit`, `raw`.
- `IngredientProductMatch`: link a *canonical recipe ingredient* to a *specific grocery product* with match quality.
- `GrocerySearchResponse`: normalized search results with fetch time.

Database suggestion (Dev 2): `grocery_products` table keyed by (`provider`, `provider_product_id`), `grocery_store_prices` keyed by (product, store), and JSON `raw_payload` on product for undocumented fields/future enrichment. Store nullable timestamps and updated-at for stale-cache controls. **Don't dump every search query result repeatedly into recipe rows**. Upsert product and store prices. Use original provider JSON only as supplemental raw data.

## Required mapping by Dev 3
`id -> provider_product_id`; `image -> image_url`; `url -> provider_url`; `link -> retailer_link`; `price -> cheapest_price_cents` via Decimal arithmetic; `store -> cheapest_store`; `discounted -> discounted`; `unitPrice -> unit_price`; `updated -> updated_at`. Product endpoint `prices[] -> store_prices[]`. Keep `raw_payload` when useful.

Recipe pipeline: confirmed pantry → recipe matcher → missing canonical ingredients → search grocery products by a localized grocery query → optionally product detail per selected ID → user chooses actual product → cache. Do **not** search every recipe's ingredient; search only missing items relevant to selected recipes. An ingredient and a grocery SKU are not equivalent. Price of a 2L milk package is not the cost of 200mL consumed.

## Implementation responsibilities
- Dev 3: `services/grocery_prices.py` HTTP adapter, responses/errors/timeouts/cache policy, normalization into Pydantic.
- Dev 2: database tables/upserts and retrieval for provider products/store observations; do after main recipe matcher/pantry.
- Dev 1: JSON API endpoint exposes normalized products and source/time fields. No provider calls in Flask routes.
- React: show price, discounted flag, store, image and link, plus source attribution.

## Limits
Provider live success was **not** verified in this review (network access blocked). Before demo, use a local machine to run `curl 'https://epiceries.ca/api?endpoint=search&q=lait&limit=2'`, validate returned keys and test a real product ID. Docs and examples aren't a substitute for a real call.

See [[Recipe Dataset Review]] and [[Backend Architecture]].
