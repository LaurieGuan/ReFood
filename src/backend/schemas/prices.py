"""Shared grocery-product contracts derived from Épiceries.ca documented API.

These models represent cached *observations*, not guaranteed real-time prices.
Provider parsing/conversion belongs in services/grocery_prices.py (Developer 3).
Persistence belongs to Developer 2. HTTP belongs to Developer 1.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class UnitPrice(BaseModel):
    value: float | None = Field(default=None, ge=0)
    unit: str | None = None
    raw: str | None = None


class StorePrice(BaseModel):
    store: str
    price_cents: int | None = Field(default=None, ge=0)
    discounted: bool | None = None
    size: str | None = None
    unit_price: UnitPrice | None = None
    retailer_link: str | None = None
    observed_at: datetime | None = None


class GroceryProduct(BaseModel):
    provider: str = "epiceries.ca"
    provider_product_id: str
    name: str
    brand: str | None = None
    size: str | None = None
    category_id: int | None = None
    image_url: str | None = None
    provider_url: str | None = None
    cheapest_store: str | None = None
    cheapest_price_cents: int | None = Field(default=None, ge=0)
    discounted: bool | None = None
    unit_price: UnitPrice | None = None
    retailer_link: str | None = None
    updated_at: datetime | None = None
    store_prices: list[StorePrice] = Field(default_factory=list)
    # Keeps provider-specific fields without polluting the normalized contract.
    raw_payload: dict = Field(default_factory=dict)


class IngredientProductMatch(BaseModel):
    """An explicit, uncertain mapping: rice != any arbitrary rice product."""
    ingredient_id: str
    product: GroceryProduct
    match_quality: str | None = None


class GrocerySearchResponse(BaseModel):
    query: str
    results: list[GroceryProduct] = Field(default_factory=list)
    has_more: bool = False
    source: str = "epiceries.ca"
    fetched_at: datetime | None = None
