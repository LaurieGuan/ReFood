"""HTTP regressions: missing services are errors, never successful fixtures."""
import io
import unittest
from copy import deepcopy
from unittest.mock import patch

from app import create_app
from schemas.recipes import Recipe


class IntegrationAuditTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app({'TESTING': True, 'DATABASE_URL': None}).test_client()

    def test_no_database_never_returns_sample_recipes(self):
        response = self.client.post('/api/v1/recipes/search', json={'ingredients': []})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('results', response.json)
        self.assertIn('DATABASE_URL', response.json['error']['message'])

    def test_missing_scan_and_grocery_services_return_503(self):
        cases = [('routes.scans.import_module', 'services.vision'),
                 ('routes.grocery.import_module', 'services.grocery_prices')]
        for target, name in cases:
            with self.subTest(name=name), patch(target, side_effect=ModuleNotFoundError(name=name)):
                if name.endswith('vision'):
                    response = self.client.post('/api/v1/scans', data={'image': (io.BytesIO(b'image'), 'photo.png', 'image/png')})
                else:
                    response = self.client.get('/api/v1/grocery/products/search?q=milk')
                self.assertEqual(response.status_code, 503)
                self.assertEqual(set(response.json), {'error'})

    def test_missing_substitution_service_returns_503(self):
        with patch('routes.recipes.import_module', side_effect=ModuleNotFoundError(name='services.substitutions')):
            response = self.client.post('/api/v1/recipes/substitutions', json={'recipe_id': 'r', 'ingredient_id': 'egg'})
        self.assertEqual(response.status_code, 503)

    def test_pantry_reports_memory_persistence(self):
        response = self.client.put('/api/v1/pantry', json={'items': []})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['X-Refood-Persistence'], 'memory')
        self.assertEqual(response.headers['X-Refood-Source'], 'confirmed_user_input')

    def test_variation_calls_actual_apply_swaps_and_preserves_source(self):
        recipe = Recipe.model_validate({'recipe_id': 'r', 'title': 'Eggs', 'ingredients': [{'ingredient_id': 'ing_egg', 'name': 'egg'}], 'instructions': ['Cook eggs']})
        original = deepcopy(recipe.model_dump())
        payload = {'recipe_id': 'r', 'swaps': [{'original_ingredient_id': 'ing_egg', 'replacement': {'ingredient_id': 'ing_tofu', 'name': 'tofu'}}]}
        with patch('routes.recipes.stored_recipes', return_value=[recipe]):
            response = self.client.post('/api/v1/recipes/variations', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['updated_ingredients'][0]['ingredient_id'], 'ing_tofu')
        self.assertEqual(response.json['missing_ingredients'][0]['ingredient_id'], 'ing_tofu')
        self.assertTrue(response.json['instructions_need_review'])
        self.assertTrue(response.json['nutrition_needs_recalculation'])
        self.assertEqual(recipe.model_dump(), original)
        with patch('routes.recipes.stored_recipes', return_value=[recipe]):
            payload['swaps'][0]['original_ingredient_id'] = 'unknown'
            self.assertEqual(self.client.post('/api/v1/recipes/variations', json=payload).status_code, 422)
            payload['recipe_id'] = 'missing'
            self.assertEqual(self.client.post('/api/v1/recipes/variations', json=payload).status_code, 404)

    def test_recipe_variation_with_real_sql_catalog(self):
        from sqlalchemy import create_engine
        from database.orm_models import Base
        from database.catalog import SQLRepository
        engine = create_engine('sqlite://')
        Base.metadata.create_all(engine)
        recipe = Recipe.model_validate({'recipe_id': 'sql_r', 'title': 'Eggs', 'ingredients': [{'ingredient_id': 'ing_egg', 'name': 'egg'}]})
        SQLRepository(engine).save_recipes([recipe])
        client = create_app({'TESTING': True, 'DATABASE_URL': 'sqlite://'}).test_client()
        try:
            with patch('database.engine.get_engine', return_value=engine):
                response = client.post('/api/v1/recipes/variations', json={'recipe_id': 'sql_r', 'swaps': []})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(SQLRepository(engine).get_recipes()[0], recipe)
        finally:
            engine.dispose()
