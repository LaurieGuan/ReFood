"""Conservative bilingual identities; unknown labels keep their specificity."""
import hashlib
import re
import unicodedata
from schemas.ingredients import Ingredient


def _key(name):
    name = unicodedata.normalize('NFKD', name.casefold().replace('œ', 'oe'))
    return ' '.join(re.sub(r'[^\w]+', ' ', ''.join(c for c in name if not unicodedata.combining(c))).split())


_GROUPS = {
    'egg': 'egg|eggs|oeuf|oeufs', 'milk': 'milk|lait',
    'tomato': 'tomato|tomatoes|tomate|tomates', 'onion': 'onion|onions|oignon|oignons',
    'garlic': 'garlic|ail', 'potato': 'potato|potatoes|pomme de terre|pommes de terre',
    'spinach': 'spinach|epinards', 'kale': 'kale|chou frise',
    'rice': 'rice|riz', 'flour': 'flour|farine', 'salt': 'salt|sel',
    'butter': 'butter|beurre', 'olive_oil': 'olive oil|huile d olive',
    'chicken': 'chicken|poulet', 'chicken_breast': 'chicken breast|chicken breasts|poitrine de poulet',
    'green_onion': 'green onion|green onions|scallion|scallions|oignon vert|oignons verts',
    'chickpea': 'chickpea|chickpeas|pois chiche|pois chiches',
    'zucchini': 'zucchini|courgette|courgettes', 'cilantro': 'cilantro|coriander leaves|coriandre fraiche',
    'cornstarch': 'cornstarch|corn starch|fecule de mais',
    'plain_yogurt': 'plain yogurt|yogourt nature|yaourt nature',
    'sour_cream': 'sour cream|creme sure',
}
_ALIASES = {_key(alias): canonical for canonical, group in _GROUPS.items() for alias in group.split('|')}


def normalize_ingredient(name: str) -> Ingredient:
    if not isinstance(name, str) or not name.strip():
        raise ValueError('Ingredient name must be nonempty text')
    key = _key(name)
    canonical = _ALIASES.get(key)
    if canonical:
        return Ingredient(ingredient_id='ing_' + canonical, name=canonical.replace('_', ' '))
    slug = key.replace(' ', '_') or hashlib.sha256(name.encode()).hexdigest()[:16]
    return Ingredient(ingredient_id='ing_' + slug, name=name.strip().casefold())
