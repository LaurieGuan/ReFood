"""Normalize confirmed names; reject invalid or conflicting duplicate inventory."""
from math import isfinite
from schemas.pantry import PantryUpdateRequest
from schemas.ingredients import Unit
from .normalizer import normalize_ingredient


def confirm_pantry(request: PantryUpdateRequest) -> PantryUpdateRequest:
    unique = {}
    for original in request.items:
        if not any(c.isalnum() for c in original.name) or len(original.name) > 512:
            raise ValueError("Ingredient name must contain letters or digits and be at most 512 characters")
        identity = normalize_ingredient(original.name)
        if len(identity.ingredient_id) > 191:
            raise ValueError("Ingredient identity is too long")
        item = original.model_copy(update=identity.model_dump(), deep=True)
        if item.quantity.amount is not None and not isfinite(item.quantity.amount):
            raise ValueError('Quantity must be finite')
        if item.quantity.amount is None:
            item.quantity.unit = Unit.UNKNOWN
        previous = unique.get(item.ingredient_id)
        if previous is not None and previous != item:
            raise ValueError('Duplicate ingredient has conflicting quantities; combine it before saving')
        unique[item.ingredient_id] = item
    return PantryUpdateRequest(items=list(unique.values()))
