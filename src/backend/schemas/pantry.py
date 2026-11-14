from pydantic import BaseModel, Field
from .ingredients import IngredientWithQuantity

class PantryItem(IngredientWithQuantity):
    remaining_fraction: float | None = Field(default=None, ge=0, le=1)

class PantryResponse(BaseModel):
    items: list[PantryItem] = Field(default_factory=list)

class PantryUpdateRequest(BaseModel):
    items: list[PantryItem]
