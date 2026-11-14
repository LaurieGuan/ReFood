"""Shared recipe and matching contracts. Prefer additive, backward-compatible changes."""
from pydantic import BaseModel, Field
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


class RecipeSearchRequest(BaseModel):
    ingredients: list[IngredientWithQuantity]
    max_missing: int | None = Field(default=None, ge=0)
    limit: int = Field(default=10, ge=1, le=100)


class RecipeSearchResponse(BaseModel):
    results: list[RecipeMatch]
