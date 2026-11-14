"""Bounded HF viewer ingestion. Never downloads parquet or image assets."""
import json
import math
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from schemas.recipes import Recipe, RecipeNutrition
from schemas.ingredients import IngredientWithQuantity
from .normalizer import normalize_ingredient

FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/integrations/recipes.json'


def _number(value, integer=False, minimum=0):
    try:
        n = float(value)
        if isinstance(value, bool) or not math.isfinite(n) or n < minimum or (integer and not n.is_integer()):
            return None
        return int(n) if integer else n
    except (ValueError, TypeError, OverflowError):
        return None


def _strings(value):
    return [x.strip() for x in value if isinstance(x, str) and x.strip()] if isinstance(value, list) else []


def parse_recipe(row: dict) -> Recipe:
    names = _strings(row.get('ingredients'))
    if not names:
        # Actual dataset has NO ingredients column: recover the isolated Markdown section.
        section = re.search(r'^## Ingredients\s*\n(.*?)(?=^## |\Z)', row.get('markdown') or '', re.M | re.S)
        if section:
            names = [x.strip() for x in section[1].strip().split(',') if x.strip()]
            expected = _number(row.get('n_ingredients'), integer=True)
            if expected is not None and len(names) != expected:
                raise ValueError('Ambiguous comma-delimited ingredients')
    if not names or not isinstance(row.get('name'), str) or not row['name'].strip() or row.get('recipe_id') is None:
        raise ValueError('Recipe lacks identity/title/ingredients')
    nutrition = row.get('nutrition')
    nutrition = RecipeNutrition(**{k: _number(nutrition.get(k)) for k in RecipeNutrition.model_fields}) if isinstance(nutrition, dict) else None
    minutes = _number(row.get('minutes'), integer=True)
    return Recipe(recipe_id='rahul7star:' + str(row['recipe_id']), source='rahul7star/food-recipes',
                  source_recipe_id=str(row['recipe_id']), title=row['name'].strip(),
                  ingredients=[IngredientWithQuantity(**normalize_ingredient(n).model_dump()) for n in names],
                  instructions=_strings(row.get('steps')), servings=_number(row.get('servings'), True, 1),
                  preparation_minutes=minutes if minutes is None or minutes <= 10080 else None,
                  description=row.get('description') if isinstance(row.get('description'), str) else None,
                  tags=_strings(row.get('tags')), nutrition=nutrition,
                  rating=_number(row.get('rating')), num_ratings=_number(row.get('num_ratings'), True))


def fetch_recipe_rows(limit=100):
    if not 1 <= limit <= 100:
        raise ValueError('Use a bounded sample of 1–100 rows')
    url = 'https://datasets-server.huggingface.co/rows?' + urlencode(dict(dataset='rahul7star/food-recipes', config='default', split='train', offset=0, length=limit))
    try:
        with urlopen(url, timeout=20) as response:
            return json.load(response)['rows']
    except (OSError, ValueError, KeyError) as exc:
        raise RuntimeError('HF sample unavailable; use import_recipes() for the captured fixture') from exc


def import_recipes(*, live=False, limit=100, rows=None) -> list[Recipe]:
    """Default is a reproducible real three-row capture; live is explicit, never fallback."""
    if not 1 <= limit <= 100:
        raise ValueError('limit must be 1–100')
    if rows is None:
        rows = fetch_recipe_rows(limit) if live else json.loads(FIXTURE.read_text())['rows']
    recipes = {}
    for entry in rows[:limit]:
        try:
            recipe = parse_recipe(entry.get('row', entry))
            recipes[recipe.recipe_id] = recipe
        except (ValueError, TypeError, AttributeError):
            continue
    return list(recipes.values())
