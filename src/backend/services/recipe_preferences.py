"""Conservative deterministic checks; absence of evidence is never certification."""
import re
from .normalizer import _key

# Ingredient phrases -> incompatible diets/allergens. Mixed products remain unknown.
_RULES = [
 ('pork|bacon|ham|prosciutto|lard|porc|jambon', {'vegan','vegetarian','halal'}, set()),
 ('wine|beer|rum|vodka|bourbon|brandy|vin|biere', {'halal'}, set()),
 ('chicken|beef|turkey|lamb|poulet|boeuf|dinde|gelatin', {'vegan','vegetarian'}, set()),
 ('fish|salmon|tuna|anchovy|anchovies|poisson|saumon', {'vegan','vegetarian'}, {'fish'}),
 ('shrimp|crab|lobster|crevette', {'vegan','vegetarian'}, {'shellfish'}),
 ('milk|butter|cream|cheese|yogurt|yogourt|lait|beurre|fromage|whey', {'vegan'}, {'milk','lactose'}),
 ('egg|eggs|oeuf|oeufs', {'vegan'}, {'egg'}),
 ('honey|miel', {'vegan'}, set()),
 ('flour|bread|pasta|wheat|noodles|farine|pain|pates', set(), {'wheat','gluten'}),
 ('soy|soya|tofu', set(), {'soy'}),
 ('peanut|peanuts|arachide', set(), {'peanut'}),
 ('almond|walnut|cashew|pecan|amande|noix', set(), {'tree_nut'}),
 ('sesame', set(), {'sesame'}),
]
_PLANTS = set('salt pepper water sugar rice tomato onion garlic potato spinach kale zucchini carrot broccoli chickpea lentil cornstarch oil olive cucumber basil parsley cilantro cumin paprika cinnamon mustard sel poivre eau sucre riz tomate oignon ail courgette'.split())

def assess_recipe(recipe, preferences):
    incompatible, allergens, unknown = set(), set(), []
    meat = False
    for item in recipe.ingredients:
        text = _key(item.name)
        matched = False
        for phrases, diets, contains in _RULES:
            if re.search(r'\b(?:' + phrases + r')\b', text):
                incompatible |= diets
                allergens |= contains
                matched = True
                meat |= 'vegetarian' in diets
        if re.search(r'\b(soup|sauce|mix|wrap|chips|extract|blend)\b', text) or (not matched and not any(re.search(r'\b' + p + r'\b',text) for p in _PLANTS)):

            unknown.append(item.name)
    warnings = []
    if unknown:
        warnings.append('Ingredient classifications need review: ' + ', '.join(unknown[:8]))
    diets = preferences.get('dietary_restrictions') or []
    for diet in diets:
        if diet in incompatible:
            return False, [f'Incompatible with {diet}']
        if diet == 'halal':
            warnings.append('Halal status unverified; meat provenance and certification are unknown.' if meat else 'Halal certification unverified.')
        elif diet not in ('vegan','vegetarian'):
            warnings.append(f'{diet} eligibility unverified.')
        elif unknown:
            warnings.append(f'{diet} eligibility unverified.')
    avoided = set(preferences.get('allergens') or []) | set(preferences.get('intolerances') or [])
    if avoided & allergens:
        return False, ['Contains: ' + ', '.join(sorted(avoided & allergens))]
    if avoided:
        warnings.append('Allergen/intolerance assessment needs packaging and cross-contact review.')
    if any(i.ingredient_id in (preferences.get('excluded_ingredient_ids') or []) for i in recipe.ingredients):
        return False, ['Excluded ingredient']
    maximum = preferences.get('max_minutes')
    if maximum not in (None, '') and (recipe.preparation_minutes is None or recipe.preparation_minutes > float(maximum)):
        return False, ['Cooking time exceeds limit or is unknown']
    for nutrient, bounds in (preferences.get('nutrition_limits') or {}).items():
        value = getattr(recipe.nutrition, nutrient, None) if recipe.nutrition else None
        for bound in ('min','max'):
            limit = bounds.get(bound)
            if limit in (None,''):
                continue
            if value is None or (value < float(limit) if bound == 'min' else value > float(limit)):
                return False, ['Nutrition limit unsatisfied or unavailable: ' + nutrient]
    if preferences.get('max_budget_cad') not in (None,''):
        warnings.append('Recipe budget unverified until relevant grocery offers are selected.')
    return True, warnings
