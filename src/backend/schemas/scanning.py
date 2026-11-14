from pydantic import BaseModel, Field
from .ingredients import IngredientWithQuantity, Certainty

class ScanCandidate(IngredientWithQuantity):
    candidate_id: str
    certainty: Certainty = Certainty.LOW

class ScanResponse(BaseModel):
    scan_id: str
    candidates: list[ScanCandidate] = Field(default_factory=list)
