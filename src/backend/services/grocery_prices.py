"""Épiceries.ca observations. Call only for selected missing ingredients/swaps."""
import copy
import json
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlencode
from urllib.request import urlopen
from schemas.prices import GroceryProduct, GrocerySearchResponse, StorePrice, UnitPrice

_CACHE = {}


def cad_cents(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        n = Decimal(str(value))
        return int((n * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)) if n.is_finite() and n >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def _date(value):
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc)
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (TypeError, ValueError, AttributeError, OverflowError, OSError):
        return None


def _unit(value):
    if isinstance(value, dict):
        try:
            return UnitPrice.model_validate(value)
        except ValueError:
            return UnitPrice(raw=str(value))
    return UnitPrice(raw=value) if isinstance(value, str) else None


def parse_product(data: dict) -> GroceryProduct:
    if data.get('id') is None or not data.get('name'):
        raise ValueError('Product lacks id/name')
    offers = []
    for p in data.get('prices') or []:
        if not isinstance(p, dict) or not p.get('store'):
            continue
        offers.append(StorePrice(store=p['store'], price_cents=cad_cents(p.get('price')),
            discounted=p.get('discounted') if isinstance(p.get('discounted'), bool) else None,
            size=p.get('size'), unit_price=_unit(p.get('unitPrice')), retailer_link=p.get('link'),
            observed_at=_date(p.get('date')) or _date(p.get('timestamp'))))
    category = data.get('category')
    return GroceryProduct(provider_product_id=str(data['id']), name=data['name'], brand=data.get('brand'),
        size=data.get('size'), category_id=category if isinstance(category, int) and not isinstance(category, bool) else None,
        image_url=data.get('image'), provider_url=data.get('url'), cheapest_store=data.get('store'),
        cheapest_price_cents=cad_cents(data.get('price')),
        discounted=data.get('discounted') if isinstance(data.get('discounted'), bool) else None,
        unit_price=_unit(data.get('unitPrice')), retailer_link=data.get('link'),
        updated_at=_date(data.get('updated')), store_prices=offers, raw_payload=copy.deepcopy(data))


def _request(**params):
    url = 'https://epiceries.ca/api?' + urlencode(params)
    cached = _CACHE.get(url)
    if cached and time.monotonic() - cached[0] < 300:
        return copy.deepcopy(cached[1])
    try:
        with urlopen(url, timeout=15) as response:
            payload = json.load(response)
        if payload.get('ok') is not True or not isinstance(payload.get('data'), dict):
            raise ValueError('Unsuccessful provider envelope')
        _CACHE[url] = (time.monotonic(), payload['data'])
        return copy.deepcopy(payload['data'])
    except (OSError, ValueError, AttributeError) as exc:
        raise RuntimeError('Épiceries.ca request failed; retry later or use an explicit test fixture') from exc


def get_grocery_categories() -> list[dict]:
    """Provider taxonomy, without enforcing an unverified local enum."""
    return _request(endpoint='categories')['categories']


def search_grocery_products(query: str, limit: int = 10) -> GrocerySearchResponse:
    if not isinstance(query, str) or len(query.strip()) < 2 or not 1 <= limit <= 100:
        raise ValueError('query needs 2 characters; limit must be 1–100')
    data = _request(endpoint='search', q=query.strip(), limit=limit, sort='price_asc')
    return GrocerySearchResponse(query=query.strip(), results=[parse_product(p) for p in data['results']],
        has_more=data.get('hasMore') is True, fetched_at=datetime.now(timezone.utc))


def get_grocery_product(product_id: str) -> GroceryProduct:
    if not isinstance(product_id, str) or not product_id.strip():
        raise ValueError('product_id is required')
    return parse_product(_request(endpoint='product', id=product_id))
