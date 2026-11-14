import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from services.normalizer import normalize_ingredient
from services.recipe_import import import_recipes, parse_recipe
from services.vision import scan_fridge
from services.grocery_prices import cad_cents, parse_product, search_grocery_products, get_grocery_product
from services.substitutions import suggest_substitutions
from schemas.substitutions import SubstitutionSuggestionRequest
from schemas.ingredients import IngredientWithQuantity

FIXTURES = Path(__file__).parent / 'fixtures/integrations'
def fixture(name):
    return json.loads((FIXTURES / (name + '.json')).read_text())

class IntegrationsTest(unittest.TestCase):
    def test_aliases_and_specificity(self):
        for a,b in [('ŒUFS','eggs'), ('oignons verts','scallions'), ('Fécule de maïs','cornstarch')]:
            self.assertEqual(normalize_ingredient(a).ingredient_id, normalize_ingredient(b).ingredient_id)
        self.assertNotEqual(normalize_ingredient('garlic').ingredient_id, normalize_ingredient('garlic powder').ingredient_id)
        self.assertNotEqual(normalize_ingredient('milk').ingredient_id, normalize_ingredient('almond milk').ingredient_id)
        self.assertEqual(normalize_ingredient('mystery food').ingredient_id, 'ing_mystery_food')
        with self.assertRaises(ValueError): normalize_ingredient(' ')

    def test_real_recipes(self):
        recipes = import_recipes()
        self.assertEqual(len(recipes), 3)
        self.assertEqual(recipes[0].recipe_id, 'rahul7star:63986')
        self.assertEqual(len(recipes[0].ingredients), 7)
        self.assertEqual(recipes[0].ingredients[1].ingredient_id, 'ing_flour')
        self.assertEqual(recipes[0].num_ratings, 19)
        for recipe in recipes:
            self.assertIsNone(recipe.servings)
            self.assertTrue(recipe.instructions)
            for ingredient in recipe.ingredients:
                self.assertIsNone(ingredient.quantity.amount)
                self.assertEqual(ingredient.quantity.unit, 'unknown')

    def test_malformed_recipes(self):
        row = fixture('recipes')['rows'][0]['row']
        row.update(minutes=-1, rating='bad', num_ratings=2.5, nutrition={'calories':'NaN'})
        parsed = parse_recipe(row)
        self.assertIsNone(parsed.preparation_minutes)
        self.assertIsNone(parsed.rating)
        self.assertIsNone(parsed.num_ratings)
        self.assertIsNone(parsed.nutrition.calories)
        row['n_ingredients'] = 100
        self.assertEqual(import_recipes(rows=[{}, row]), [])

    def test_vision_mock(self):
        candidates = scan_fridge(b'offline-test', detector=lambda _: [dict(name='tomates', certainty='medium', quantity=99), dict(name='mystery jar', certainty='bad')])
        self.assertEqual(candidates[0].ingredient_id, 'ing_tomato')
        self.assertEqual(candidates[1].certainty, 'low')
        self.assertIsNone(candidates[0].quantity.amount)
        self.assertNotEqual(candidates[0].candidate_id, candidates[1].candidate_id)
        with self.assertRaises(ValueError): scan_fridge(b'')
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(RuntimeError): scan_fridge(b'x')

    def test_prices_real_capture(self):
        product = parse_product(fixture('product')['data'])
        self.assertEqual(product.provider_product_id, 'B2kZGPy7um8F')
        self.assertEqual(product.raw_payload, fixture('product')['data'])
        self.assertTrue(product.store_prices)
        self.assertEqual(cad_cents('4.995'), 500)
        for value in [None, 'bad', '-1', 'NaN', True]: self.assertIsNone(cad_cents(value))
        with patch('services.grocery_prices._request', return_value=fixture('search')['data']):
            result = search_grocery_products('lait', 2)
        self.assertEqual(result.results[0].cheapest_price_cents, 397)
        self.assertEqual(result.results[0].category_id, 70) # soap: search is NOT culinary matching
        with patch('services.grocery_prices._request', return_value=fixture('product')['data']):
            self.assertEqual(get_grocery_product('B2kZGPy7um8F'), product)

    def test_substitutions_do_not_mutate(self):
        request = SubstitutionSuggestionRequest(recipe_id='x', ingredient_id='ing_spinach', pantry=[IngredientWithQuantity(**normalize_ingredient('kale').model_dump())])
        before = copy.deepcopy(request)
        result = suggest_substitutions(request)
        self.assertEqual(result.suggestions[0].source, 'pantry')
        self.assertEqual(request, before)
        self.assertEqual(suggest_substitutions(SubstitutionSuggestionRequest(recipe_id='x', ingredient_id='ing_egg')).suggestions, [])

if __name__ == '__main__': unittest.main()
