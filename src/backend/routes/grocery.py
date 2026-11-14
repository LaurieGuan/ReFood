"""Search grocery products for a user-selected ingredient or substitute."""

from importlib import import_module

from flask import Blueprint, request
from werkzeug.exceptions import BadRequest

from schemas.prices import GrocerySearchResponse, GroceryProduct
from .http_utils import json_response

grocery_bp = Blueprint("grocery", __name__)


def search_grocery_products(query: str, limit: int = 10) -> GrocerySearchResponse:
    """Delegate to Developer 3; the empty mock is explicitly labeled."""
    try:
        service = import_module("services.grocery_prices")
    except ModuleNotFoundError as exc:
        if exc.name != "services.grocery_prices":
            raise
        return GrocerySearchResponse(query=query, source="mock")
    return service.search_grocery_products(query, limit=limit)


@grocery_bp.get("/search")
def search_products():
    query = request.args.get("q", "").strip()
    try:
        limit = int(request.args.get("limit", "10"))
    except ValueError as exc:
        raise BadRequest("limit must be an integer between 1 and 100") from exc
    if len(query) < 2:
        raise BadRequest("q must contain at least two characters")
    if not 1 <= limit <= 100:
        raise BadRequest("limit must be an integer between 1 and 100")
    category = request.args.get("category")
    if category is not None:
        try:
            category = int(category)
            from services.grocery_prices import search_grocery_products as provider_search
            result = provider_search(query, limit, category=category)
        except ValueError:
            raise BadRequest("Unknown or invalid grocery category") from None
    else:
        result = search_grocery_products(query, limit)
    return json_response(GrocerySearchResponse, result)


@grocery_bp.get("/<product_id>")
def product_details(product_id):
    service = import_module("services.grocery_prices")
    return json_response(GroceryProduct, service.get_grocery_product(product_id))
