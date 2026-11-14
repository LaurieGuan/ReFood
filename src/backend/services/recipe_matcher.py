"""Deterministic demo matcher. IDs are supplied by the normalization adapter."""

from collections import defaultdict
from math import isclose

from schemas.ingredients import Unit
from schemas.recipes import Recipe, RecipeMatch, RecipeSearchRequest


def sample_recipes() -> list[Recipe]:
    """Small, explicitly illustrative catalog; replace with imported recipes later."""
    return [Recipe.model_validate(data) for data in (
        {"recipe_id": "demo_omelette", "title": "Demo omelette", "ingredients": [
            {"ingredient_id": "ing_egg", "name": "egg", "quantity": {"amount": 2, "unit": "piece"}},
            {"ingredient_id": "ing_milk", "name": "milk", "quantity": {"amount": 50, "unit": "ml"}},
        ]},
        {"recipe_id": "demo_pasta", "title": "Demo tomato pasta", "ingredients": [
            {"ingredient_id": "ing_pasta", "name": "pasta", "quantity": {"amount": 200, "unit": "g"}},
            {"ingredient_id": "ing_tomato", "name": "tomato"},
        ]},
        {"recipe_id": "demo_rice", "title": "Demo tomato rice", "ingredients": [
            {"ingredient_id": "ing_rice", "name": "rice", "quantity": {"amount": 150, "unit": "g"}},
            {"ingredient_id": "ing_tomato", "name": "tomato"},
        ]},
    )]


_UNITS = {
    Unit.G: ("mass", 1), Unit.KG: ("mass", 1000),
    Unit.ML: ("volume", 1), Unit.L: ("volume", 1000),
    Unit.PIECE: ("count", 1),
}


def _quantity_status(required, available):
    """Return (known_shortage, uncertain), comparing only compatible units."""
    required_unit = _UNITS.get(required.quantity.unit)
    required_amount = required.quantity.amount
    if required_amount == 0:
        return False, False
    if required_amount is None or required_unit is None:
        return False, True
    total = 0
    uncertain = False
    for item in available:
        unit = _UNITS.get(item.quantity.unit)
        amount = item.quantity.amount
        if amount is None or unit is None or unit[0] != required_unit[0]:
            uncertain = True
        else:
            total += amount * unit[1]
    needed = required_amount * required_unit[1]
    enough = total >= needed or isclose(total, needed, rel_tol=1e-9)
    return not enough and not uncertain, not enough and uncertain


def match_recipes(request: RecipeSearchRequest, recipes: list[Recipe]) -> list[RecipeMatch]:
    """Match supplied canonical recipes; no name guessing or database access.

    Coverage counts distinct ingredient IDs with available positive/unknown stock.
    A known shortage is listed as missing (full requirement, not a fabricated
    deficit). Unknown amounts/units flag uncertainty without claiming shortage.
    """
    stock = defaultdict(list)
    for item in request.ingredients:
        if item.quantity.amount != 0:
            stock[item.ingredient_id].append(item)
    results = []
    for recipe in recipes:
        requirements = defaultdict(list)
        for item in recipe.ingredients:
            requirements[item.ingredient_id].append(item)
        if not requirements:
            continue  # Incomplete source data must not become a perfect match.
        missing = []
        uncertain = False
        covered = 0
        for ingredient_id, entries in requirements.items():
            available = stock.get(ingredient_id, [])
            # Combine repeated requirements in the same unit before comparing.
            first = entries[0].model_copy(deep=True)
            units = {entry.quantity.unit for entry in entries}
            if len(units) == 1 and all(entry.quantity.amount is not None for entry in entries):
                first.quantity.amount = sum(entry.quantity.amount for entry in entries)
            elif len(entries) > 1:
                first.quantity.amount = None
                first.quantity.unit = Unit.UNKNOWN
            if not available:
                missing.append(first)
                continue
            shortage, unknown = _quantity_status(first, available)
            uncertain |= unknown
            covered += 1
            if shortage:
                missing.append(first)
        if request.max_missing is not None and len(missing) > request.max_missing:
            continue
        results.append(RecipeMatch(
            recipe=recipe.model_copy(deep=True),
            match_score=covered / len(requirements),
            missing_ingredients=missing, quantity_uncertain=uncertain,
        ))
    results.sort(key=lambda match: (
        -match.match_score, len(match.missing_ingredients),
        match.quantity_uncertain, match.recipe.recipe_id,
    ))
    return results[:request.limit]


def find_recipes(request: RecipeSearchRequest) -> list[RecipeMatch]:
    import os
    if os.environ.get("DATABASE_URL"):
        from database.catalog import get_recipes
        return match_recipes(request, get_recipes())
    return match_recipes(request, sample_recipes())


def apply_swaps(recipe, swaps, pantry):
    """Apply confirmed swaps to a copy, never to the persisted source recipe."""
    from schemas.substitutions import RecipeVariationResponse
    updated = recipe.model_copy(deep=True)
    originals = {item.ingredient_id for item in recipe.ingredients}
    selected = {}
    for swap in swaps:
        key = swap.original_ingredient_id
        if key not in originals or key in selected:
            raise ValueError("Unknown or duplicate swap ingredient ID")
        selected[key] = swap.replacement
    updated.ingredients = [selected.get(item.ingredient_id, item).model_copy(deep=True)
                           for item in recipe.ingredients]
    results = match_recipes(RecipeSearchRequest(ingredients=pantry), [updated])
    return RecipeVariationResponse(original_recipe_id=recipe.recipe_id,
        updated_ingredients=updated.ingredients,
        missing_ingredients=results[0].missing_ingredients if results else [],
        instructions_need_review=bool(swaps), nutrition_needs_recalculation=bool(swaps),
        warnings=["Review cooking instructions, nutrition and allergens after substitutions."] if swaps else [])
