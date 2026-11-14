"""Recipe ingredient substitutions — user-controlled, never silent.

These schemas describe a proposed replacement, not a claim that the recipe,
nutrition or allergen profile remains equivalent after a substitution.
"""
from enum import Enum
from pydantic import BaseModel, Field
from .ingredients import IngredientWithQuantity
from .prices import GroceryProduct


class SubstituteSource(str, Enum):
    PANTRY = "pantry"
    GROCERY = "grocery"


class SubstituteCandidate(BaseModel):
    original_ingredient_id: str
    replacement: IngredientWithQuantity
    source: SubstituteSource
    rationale: str | None = None
    # For grocery candidates, the product is an actual SKU, not an ingredient ID.
    grocery_product: GroceryProduct | None = None
    # No price guarantee: package offers are fetched separately.
    notes: list[str] = Field(default_factory=list)


class SubstitutionSuggestionRequest(BaseModel):
    recipe_id: str
    ingredient_id: str
    pantry: list[IngredientWithQuantity] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=20)


class SubstitutionSuggestionResponse(BaseModel):
    recipe_id: str
    original_ingredient_id: str
    suggestions: list[SubstituteCandidate] = Field(default_factory=list)


class IngredientSwap(BaseModel):
    original_ingredient_id: str
    replacement: IngredientWithQuantity


class RecipeVariationRequest(BaseModel):
    recipe_id: str
    swaps: list[IngredientSwap] = Field(default_factory=list)
    pantry: list[IngredientWithQuantity] = Field(default_factory=list)


class RecipeVariationResponse(BaseModel):
    original_recipe_id: str
    updated_ingredients: list[IngredientWithQuantity]
    missing_ingredients: list[IngredientWithQuantity] = Field(default_factory=list)
    # Instructions / nutrition cannot automatically be assumed valid after a swap.
    instructions_need_review: bool = True
    nutrition_needs_recalculation: bool = True
    warnings: list[str] = Field(default_factory=list)
