import os
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path

from sqlalchemy import create_engine, select, func
from database.orm_models import Base, RecipeRow, RecipeIngredientRow
from database.catalog import SQLRepository
from schemas.recipes import Recipe
from schemas.pantry import PantryUpdateRequest
from schemas.prices import GroceryProduct
from schemas.substitutions import IngredientSwap
from services.recipe_matcher import sample_recipes, find_recipes, apply_swaps


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = create_engine('sqlite:///' + str(Path(self.directory.name) / 'test.db'))
        Base.metadata.create_all(self.engine)
        self.repo = SQLRepository(self.engine)

    def tearDown(self):
        self.engine.dispose()
        self.directory.cleanup()

    def test_idempotent_enriched_roundtrip(self):
        recipe = Recipe.model_validate({**sample_recipes()[0].model_dump(mode='json'),
            'source': 'fixture', 'source_recipe_id': '123', 'tags': ['demo'],
            'description': 'Test', 'instructions': ['Mix'], 'servings': 2,
            'preparation_minutes': 10, 'rating': 4.5, 'num_ratings': 12,
            'image_url': 'https://example.test/a.jpg', 'nutrition': {'calories': 123}})
        self.assertEqual(self.repo.save_recipes([recipe]), 1)
        self.assertEqual(self.repo.save_recipes([recipe]), 1)
        self.assertEqual(self.repo.get_recipes(), [recipe])
        with self.engine.connect() as conn:
            self.assertEqual(conn.scalar(select(func.count()).select_from(RecipeRow)), 1)
        recipe.ingredients.pop()
        self.repo.save_recipes([recipe])
        self.assertEqual(self.repo.get_recipes(), [recipe])
        with self.engine.connect() as conn:
            self.assertEqual(conn.scalar(select(func.count()).select_from(RecipeIngredientRow)), 1)

    def test_pantry_durable_replace_clear_and_isolation(self):
        request = PantryUpdateRequest.model_validate({'items': [{
            **sample_recipes()[0].ingredients[0].model_dump(mode='json'),
            'remaining_fraction': .3}]})
        self.repo.replace_pantry('alice', request)
        other = SQLRepository(self.engine)
        self.assertEqual(other.get_pantry('alice').items, request.items)
        self.assertEqual(other.get_pantry('bob').items, [])
        other.replace_pantry('alice', PantryUpdateRequest(items=[]))
        self.assertEqual(self.repo.get_pantry('alice').items, [])

    def test_public_matcher_uses_catalog(self):
        recipe = sample_recipes()[0]
        self.repo.save_recipes([recipe])
        from schemas.recipes import RecipeSearchRequest
        with patch.dict(os.environ, {'DATABASE_URL': 'configured'}), patch(
                'database.catalog.get_engine', return_value=self.engine):
            results = find_recipes(RecipeSearchRequest(ingredients=recipe.ingredients))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].match_score, 1)

    def test_grocery_upsert_keeps_nullable_fields_and_offers(self):
        product = GroceryProduct.model_validate({'provider_product_id': 'sku', 'name': 'Milk',
            'updated_at': '2026-11-14T12:00:00Z', 'raw_payload': {'unknown': None},
            'store_prices': [{'store': 'A', 'price_cents': 299, 'discounted': True,
                              'observed_at': '2026-11-14T12:00:00Z'}]})
        self.repo.save_grocery_products([product])
        self.repo.save_grocery_products([product])
        self.assertEqual(self.repo.get_grocery_products(), [product])

    def test_transaction_rollback(self):
        recipes = sample_recipes()
        original = self.repo._ingredient
        calls = []
        def fail(session, item):
            calls.append(item)
            if len(calls) == 2:
                raise RuntimeError('test')
            original(session, item)
        with patch.object(self.repo, '_ingredient', side_effect=fail):
            with self.assertRaises(RuntimeError):
                self.repo.save_recipes(recipes)
        self.assertEqual(self.repo.get_recipes(), [])


class VariationTests(unittest.TestCase):
    def test_swap_recomputes_without_mutation(self):
        recipe = sample_recipes()[0]
        before = recipe.model_dump(mode='json')
        replacement = sample_recipes()[1].ingredients[0]
        swap = IngredientSwap(original_ingredient_id='ing_egg', replacement=replacement)
        variation = apply_swaps(recipe, [swap], [replacement])
        self.assertEqual(recipe.model_dump(mode='json'), before)
        self.assertEqual([i.ingredient_id for i in variation.missing_ingredients], ['ing_milk'])
        self.assertTrue(variation.instructions_need_review)
        self.assertTrue(variation.nutrition_needs_recalculation)

    def test_unrecognized_swap_rejected(self):
        swap = IngredientSwap(original_ingredient_id='unknown', replacement=sample_recipes()[0].ingredients[0])
        with self.assertRaises(ValueError):
            apply_swaps(sample_recipes()[0], [swap], [])
