"""Recipe search HTTP endpoint and replaceable matcher adapter."""

from importlib import import_module

from flask import Blueprint, make_response
from werkzeug.exceptions import ServiceUnavailable, NotFound, UnprocessableEntity

from schemas.recipes import RecipeMatch, RecipeSearchRequest, RecipeSearchResponse
from schemas.substitutions import (
    RecipeVariationRequest, RecipeVariationResponse,
    SubstitutionSuggestionRequest, SubstitutionSuggestionResponse,
)
from .http_utils import json_response, validate_request

recipes_bp = Blueprint("recipes", __name__)


def find_recipes(request_model: RecipeSearchRequest) -> list[RecipeMatch]:
    """Only search the configured recipe catalog; fixtures are test inputs only."""
    from services.recipe_matcher import match_recipes
    return match_recipes(request_model, stored_recipes())


def stored_recipes():
    from flask import current_app
    if not current_app.config.get("DATABASE_URL"):
        raise ServiceUnavailable("Recipe database is not configured; set DATABASE_URL and import recipes")
    from database.catalog import SQLRepository
    from database.engine import get_engine
    recipes = SQLRepository(get_engine(current_app.config["DATABASE_URL"])).get_recipes()
    if not recipes:
        raise ServiceUnavailable("Recipe database is empty; import recipes first")
    return recipes


@recipes_bp.post("/search")
def search_recipes():
    search_request = validate_request(RecipeSearchRequest)
    matches = find_recipes(search_request)
    response = RecipeSearchResponse(results=matches[: search_request.limit])
    result = make_response(*json_response(RecipeSearchResponse, response))
    result.headers["X-Refood-Source"] = "recipe_catalog"
    return result


def suggest_substitutions(search: SubstitutionSuggestionRequest):
    """Delegate suggestions; a missing service is unavailable."""
    try:
        service = import_module("services.substitutions")
    except ModuleNotFoundError as exc:
        if exc.name != "services.substitutions":
            raise
        raise ServiceUnavailable("Substitution suggestions are not available") from exc
    return service.suggest_substitutions(search)


def calculate_variation(variation: RecipeVariationRequest):
    """Developer 2 computes a new variation without changing the source recipe."""
    try:
        service = import_module("services.recipe_matcher")
    except ModuleNotFoundError as exc:
        if exc.name != "services.recipe_matcher":
            raise
        raise ServiceUnavailable("Recipe variation service is not available") from exc
    if not hasattr(service, "apply_swaps"):
        raise ServiceUnavailable("Recipe variation service is not available")
    recipe = next((recipe for recipe in stored_recipes() if recipe.recipe_id == variation.recipe_id), None)
    if recipe is None:
        raise NotFound("Recipe not found in the stored catalog")
    try:
        return service.apply_swaps(recipe, variation.swaps, variation.pantry)
    except ValueError as exc:
        raise UnprocessableEntity(str(exc)) from None


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
