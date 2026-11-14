"""Shared recipe and matching contracts. Prefer additive, backward-compatible changes."""
from pydantic import BaseModel, Field, field_validator
from math import isfinite
from .ingredients import IngredientWithQuantity


class RecipeNutrition(BaseModel):
    """Food.com-source nutrition values; *_pdv are percent daily values, not grams."""
    calories: float | None = None
    total_fat_pdv: float | None = None
    sugar_pdv: float | None = None
    sodium_pdv: float | None = None
    protein_pdv: float | None = None
    saturated_fat_pdv: float | None = None
    carbs_pdv: float | None = None


class Recipe(BaseModel):
    recipe_id: str
    title: str
    ingredients: list[IngredientWithQuantity]
    instructions: list[str] = Field(default_factory=list)
    servings: int | None = Field(default=None, ge=1)
    preparation_minutes: int | None = Field(default=None, ge=0)
    image_url: str | None = None

    # Optional source metadata — existing routes/matchers remain valid.
    source: str | None = None
    source_recipe_id: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    nutrition: RecipeNutrition | None = None
    rating: float | None = Field(default=None, ge=0)
    num_ratings: int | None = Field(default=None, ge=0)


class RecipeMatch(BaseModel):
    recipe: Recipe
    match_score: float = Field(ge=0, le=1)
    missing_ingredients: list[IngredientWithQuantity]
    quantity_uncertain: bool = False
    preference_warnings: list[str] = Field(default_factory=list)


class RecipeSearchRequest(BaseModel):
    preferences: dict = Field(default_factory=dict)

    @field_validator("preferences")
    @classmethod
    def validate_preferences(cls, value):
        for key in ("dietary_restrictions", "allergens", "intolerances", "excluded_ingredient_ids"):
            if key in value and (not isinstance(value[key], list) or not all(isinstance(x, str) for x in value[key])):
                raise ValueError(f"{key} must be a list of strings")
        numbers = [value.get("max_minutes"), value.get("max_budget_cad")]
        limits = value.get("nutrition_limits") or {}
        if not isinstance(limits, dict):
            raise ValueError("nutrition_limits must be an object")
        for bounds in limits.values():
            if not isinstance(bounds, dict):
                raise ValueError("Nutrition bounds must be objects")
            numbers.extend(bounds.get(bound) for bound in ("min", "max"))
        for number in numbers:
            if number in (None, ''):
                continue
            try:
                valid = not isinstance(number, bool) and isfinite(float(number)) and float(number) >= 0
            except (TypeError, ValueError):
                valid = False
            if not valid:
                raise ValueError("Preference limits must be finite nonnegative numbers")
        return value

    ingredients: list[IngredientWithQuantity]
    max_missing: int | None = Field(default=None, ge=0)
    limit: int = Field(default=10, ge=1, le=100)


class RecipeSearchResponse(BaseModel):
    results: list[RecipeMatch]
