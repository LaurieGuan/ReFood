from enum import Enum
from pydantic import BaseModel, Field

class Unit(str, Enum):
    G = "g"
    KG = "kg"
    ML = "ml"
    L = "l"
    PIECE = "piece"
    UNKNOWN = "unknown"

class Certainty(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Ingredient(BaseModel):
    ingredient_id: str
    name: str

class IngredientQuantity(BaseModel):
    amount: float | None = Field(default=None, ge=0)
    unit: Unit = Unit.UNKNOWN

class IngredientWithQuantity(Ingredient):
    quantity: IngredientQuantity = Field(default_factory=IngredientQuantity)
