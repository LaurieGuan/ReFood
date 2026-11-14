"""Recipe search HTTP endpoint and replaceable matcher adapter."""

from importlib import import_module

from flask import Blueprint

from schemas.recipes import RecipeMatch, RecipeSearchRequest, RecipeSearchResponse
from .http_utils import json_response, validate_request

recipes_bp = Blueprint("recipes", __name__)


def find_recipes(request_model: RecipeSearchRequest) -> list[RecipeMatch]:
    """Call Developer 2's matcher, falling back to a schema-valid demo mock."""
    try:
        matcher = import_module("services.recipe_matcher").find_recipes
    except ModuleNotFoundError as exc:
        if exc.name != "services.recipe_matcher":
            raise
        return []
    return matcher(request_model)


@recipes_bp.post("/search")
def search_recipes():
    search_request = validate_request(RecipeSearchRequest)
    matches = find_recipes(search_request)
    response = RecipeSearchResponse(results=matches[: search_request.limit])
    return json_response(RecipeSearchResponse, response)
