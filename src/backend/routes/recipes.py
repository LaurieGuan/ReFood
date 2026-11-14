"""Recipe search HTTP endpoint and replaceable matcher adapter."""

from importlib import import_module

from flask import Blueprint
from werkzeug.exceptions import ServiceUnavailable

from schemas.recipes import RecipeMatch, RecipeSearchRequest, RecipeSearchResponse
from schemas.substitutions import (
    RecipeVariationRequest, RecipeVariationResponse,
    SubstitutionSuggestionRequest, SubstitutionSuggestionResponse,
)
from .http_utils import json_response, validate_request

recipes_bp = Blueprint("recipes", __name__)


def find_recipes(request_model: RecipeSearchRequest) -> list[RecipeMatch]:
    """Call Developer 2's matcher, falling back to a schema-valid demo mock."""
    from flask import current_app
    if current_app.config.get("DATABASE_URL"):
        from database.catalog import SQLRepository
        from database.engine import get_engine
        from services.recipe_matcher import match_recipes
        recipes = SQLRepository(get_engine(current_app.config["DATABASE_URL"])).get_recipes()
        if not recipes:
            raise ServiceUnavailable("Recipe database is empty; import refood-recipes.jsonl.gz first")
        return match_recipes(request_model, recipes)
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


def suggest_substitutions(search: SubstitutionSuggestionRequest):
    """Developer 3 integration; empty suggestions are a temporary mock."""
    try:
        service = import_module("services.substitutions")
    except ModuleNotFoundError as exc:
        if exc.name != "services.substitutions":
            raise
        return SubstitutionSuggestionResponse(
            recipe_id=search.recipe_id, original_ingredient_id=search.ingredient_id
        )
    return service.suggest_substitutions(search)


def calculate_variation(variation: RecipeVariationRequest):
    """Developer 2 computes a new variation without changing the source recipe."""
    try:
        service = import_module("services.recipe_matcher")
    except ModuleNotFoundError as exc:
        if exc.name != "services.recipe_matcher":
            raise
        raise ServiceUnavailable("Recipe variation service is not available") from exc
    if not hasattr(service, "calculate_variation"):
        raise ServiceUnavailable("Recipe variation service is not available")
    return service.calculate_variation(variation)


@recipes_bp.post("/substitutions")
def substitutions():
    search = validate_request(SubstitutionSuggestionRequest)
    return json_response(SubstitutionSuggestionResponse, suggest_substitutions(search))


@recipes_bp.post("/variations")
def variations():
    variation = validate_request(RecipeVariationRequest)
    result = RecipeVariationResponse.model_validate(calculate_variation(variation))
    if variation.swaps:
        warnings = list(result.warnings)
        for warning in (
            "Recipe instructions require review after substitutions.",
            "Nutrition requires recalculation after substitutions.",
        ):
            if warning not in warnings:
                warnings.append(warning)
        result = result.model_copy(update={
            "instructions_need_review": True,
            "nutrition_needs_recalculation": True,
            "warnings": warnings,
        })
    return json_response(RecipeVariationResponse, result)
