from pydantic import BaseModel, Field
from .ingredients import IngredientWithQuantity

class Recipe(BaseModel):
    recipe_id: str
    title: str
    ingredients: list[IngredientWithQuantity]
    instructions: list[str] = Field(default_factory=list)
    servings: int | None = Field(default=None, ge=1)
    preparation_minutes: int | None = Field(default=None, ge=0)
    image_url: str | None = None

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
