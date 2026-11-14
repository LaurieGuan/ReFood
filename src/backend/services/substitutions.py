"""Suggestions only. Never modifies recipes or asserts nutritional equivalence."""
from schemas.ingredients import IngredientWithQuantity
from schemas.substitutions import SubstituteCandidate, SubstituteSource, SubstitutionSuggestionRequest, SubstitutionSuggestionResponse
from schemas.prices import IngredientProductMatch

# Deliberately narrow, directional culinary rules with explicit constraints.
_RULES = {
    'ing_spinach': [('ing_kale', 'Suitable in cooked greens dishes; remove tough stems and adjust cooking time.')],
    'ing_sour_cream': [('ing_plain_yogurt', 'May work as a cold topping; heat can curdle yogurt.')],
}


def suggest_substitutions(request: SubstitutionSuggestionRequest, *, buyable: list[IngredientProductMatch] | None = None) -> SubstitutionSuggestionResponse:
    suggestions = []
    pantry = {p.ingredient_id: p for p in request.pantry}
    for replacement_id, reason in _RULES.get(request.ingredient_id, []):
        item = pantry.get(replacement_id)
        if item is not None:
            suggestions.append(SubstituteCandidate(original_ingredient_id=request.ingredient_id,
                replacement=IngredientWithQuantity(**item.model_dump()), source=SubstituteSource.PANTRY,
                rationale=reason, notes=['Confirm suitability and quantity. Instructions and nutrition require review.']))
        else:
            for match in buyable or []:
                if match.ingredient_id == replacement_id:
                    suggestions.append(SubstituteCandidate(original_ingredient_id=request.ingredient_id,
                        replacement=IngredientWithQuantity(ingredient_id=replacement_id, name=replacement_id.removeprefix('ing_').replace('_', ' ')),
                        source=SubstituteSource.GROCERY, grocery_product=match.product, rationale=reason,
                        notes=['User must confirm ingredient-to-SKU match and select the product.']))
    return SubstitutionSuggestionResponse(recipe_id=request.recipe_id, original_ingredient_id=request.ingredient_id,
        suggestions=suggestions[:request.limit])
