"""Integration regressions: real adapters with explicit provider-boundary fixtures."""
import io
import json
import unittest
from unittest.mock import patch, MagicMock
from app import create_app
from services.vision import scan_fridge

class VisionFlowTests(unittest.TestCase):
    def test_provider_json_through_scan_route(self):
        provider = MagicMock()
        provider.__enter__.return_value.read.return_value = json.dumps({'choices':[{'message':{'content':'```json\n{"candidates":[{"name":"oeufs","certainty":"high"},{"name":"eggs","certainty":"medium"}]}\n```'}}]}).encode()
        with patch.dict('os.environ', {'VISION_API_KEY':'test-only', 'VISION_MODEL':'gemini-test'}), patch('services.vision.urlopen', return_value=provider) as call:
            response = create_app({'TESTING':True,'DATABASE_URL':None}).test_client().post('/api/v1/scans',data={'image':(io.BytesIO(b'\x89PNG\r\n\x1a\ntest'),'photo.png','image/png')})
        self.assertEqual(response.status_code,200)
        items=response.json['candidates']
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]['ingredient_id'],'ing_egg')
        self.assertIsNone(items[0]['quantity']['amount'])
        self.assertIn('packaging',json.loads(call.call_args.args[0].data)['messages'][0]['content'][0]['text'])

    def test_provider_failure_visible(self):
        with patch('services.vision._detect',side_effect=RuntimeError('private provider body')):
            response=create_app({'TESTING':True}).test_client().post('/api/v1/scans',data={'image':(io.BytesIO(b'image'),'photo.jpg','image/jpeg')})
        self.assertEqual(response.status_code,502)
        self.assertNotIn('private provider body',response.text)

class PantryFlowTests(unittest.TestCase):
    def test_edited_and_manual_names_roundtrip(self):
        client=create_app({'TESTING':True,'DATABASE_URL':None}).test_client()
        response=client.put('/api/v1/pantry',json={'items':[
            {'ingredient_id':'stale','name':'Oeufs','quantity':{'amount':2,'unit':'piece'}},
            {'ingredient_id':'manual','name':'tomates'}]})
        self.assertEqual(response.status_code,200)
        self.assertEqual([p['ingredient_id'] for p in response.json['items']],['ing_egg','ing_tomato'])
        self.assertEqual(client.get('/api/v1/pantry').json,response.json)
        recipes=client.post('/api/v1/recipes/search',json={'ingredients':response.json['items']})
        # No configured catalog must fail explicitly, never search sample recipes.
        self.assertEqual(recipes.status_code,503)

    def test_duplicate_and_blank_confirmation(self):
        client=create_app({'TESTING':True,'DATABASE_URL':None}).test_client()
        item={'ingredient_id':'x','name':'egg'}
        response=client.put('/api/v1/pantry',json={'items':[item,item]})
        self.assertEqual(len(response.json['items']),1)
        response=client.put('/api/v1/pantry',json={'items':[item,{**item,'quantity':{'amount':3,'unit':'piece'}}]})
        self.assertEqual(response.status_code,422)
        self.assertEqual(client.put('/api/v1/pantry',json={'items':[{'ingredient_id':'x','name':' '}]}).status_code,422)

class ArtifactFlowTests(unittest.TestCase):
    def test_stream_import_idempotent_searchable(self):
        import gzip
        import tempfile
        from pathlib import Path
        from sqlalchemy import create_engine
        from database.orm_models import Base
        from database.catalog import SQLRepository
        from services.recipe_import import import_jsonl_gzip, FIXTURE
        from services.recipe_matcher import match_recipes
        from schemas.recipes import RecipeSearchRequest
        rows=[r['row'] for r in json.loads(FIXTURE.read_text())['rows']]
        from services.recipe_import import parse_recipe
        for row in rows:
            row['ingredients']=[i.name for i in parse_recipe(row).ingredients]
            row.pop('markdown',None)
        engine=create_engine('sqlite://')
        Base.metadata.create_all(engine)
        repository=SQLRepository(engine)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'recipes.jsonl.gz'
            with gzip.open(path,'wt') as f:
                for row in rows: f.write(json.dumps(row)+'\n')
                f.write('{malformed\n')
            rejections=io.StringIO()
            stats=import_jsonl_gzip(path,repository,batch_size=2,rejection_file=rejections)
            self.assertEqual(stats,{'read':4,'accepted':3,'rejected':1,'upserted':3})
            import_jsonl_gzip(path,repository)
        recipes=repository.get_recipes()
        self.assertEqual(len(recipes),3)
        self.assertEqual(recipes[0].source,'rahul7star/food-recipes')
        self.assertTrue(match_recipes(RecipeSearchRequest(ingredients=[]),recipes))
        self.assertIn('"line": 4',rejections.getvalue())
        engine.dispose()

class PreferenceTests(unittest.TestCase):
    def test_actual_imports_time_and_diets(self):
        from services.recipe_import import import_recipes
        from services.recipe_preferences import assess_recipe
        recipes=import_recipes()
        self.assertFalse(assess_recipe(recipes[0],{'max_minutes':30})[0])
        self.assertFalse(assess_recipe(recipes[0],{'dietary_restrictions':['halal']})[0])
        self.assertFalse(assess_recipe(recipes[1],{'dietary_restrictions':['vegan']})[0])
        self.assertFalse(assess_recipe(recipes[2],{'allergens':['peanut']})[0])
        self.assertTrue(assess_recipe(recipes[2],{'nutrition_limits':{'calories':{'max':300}}})[0])
        recipe=recipes[0].model_copy(deep=True)
        recipe.ingredients=recipe.ingredients[-1:]
        eligible,warnings=assess_recipe(recipe,{'dietary_restrictions':['halal']})
        self.assertTrue(eligible)
        self.assertTrue(any('unverified' in w for w in warnings))

class PreferenceValidationTests(unittest.TestCase):
    def test_malformed_preferences_are_422(self):
        client=create_app({'TESTING':True,'DATABASE_URL':None}).test_client()
        for preferences in ({'max_minutes':'NaN'}, {'allergens':'milk'}, {'nutrition_limits':{'calories':[]}}):
            self.assertEqual(client.post('/api/v1/recipes/search',json={'ingredients':[],'preferences':preferences}).status_code,422)

    def test_egg_vegan_and_uncertified_chicken(self):
        from schemas.recipes import Recipe
        from services.recipe_preferences import assess_recipe
        from services.normalizer import normalize_ingredient
        def recipe(name):
            return Recipe(recipe_id='test',title='test',ingredients=[normalize_ingredient(name).model_dump()])
        self.assertFalse(assess_recipe(recipe('egg'),{'dietary_restrictions':['vegan']})[0])
        eligible,warnings=assess_recipe(recipe('chicken'),{'dietary_restrictions':['halal']})
        self.assertTrue(eligible)
        self.assertTrue(any('provenance' in w for w in warnings))
        eligible,warnings=assess_recipe(recipe('mystery paste'),{'dietary_restrictions':['vegetarian']})
        self.assertTrue(eligible)
        self.assertTrue(any('unverified' in w for w in warnings))

class LargeArtifactTests(unittest.TestCase):
    def test_thousand_rows_use_bounded_batches(self):
        import gzip
        import tempfile
        from pathlib import Path
        from services.recipe_import import FIXTURE, parse_recipe, import_jsonl_gzip
        row=json.loads(FIXTURE.read_text())['rows'][0]['row']
        row['ingredients']=[i.name for i in parse_recipe(row).ingredients]
        row.pop('markdown',None)
        repository=MagicMock()
        repository.save_recipes.side_effect=lambda batch:len(batch)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'thousand.jsonl.gz'
            with gzip.open(path,'wt') as f:
                for index in range(1001):
                    f.write(json.dumps({**row,'recipe_id':index})+'\n')
            stats=import_jsonl_gzip(path,repository,batch_size=200)
        self.assertEqual(stats['upserted'],1001)
        self.assertEqual(repository.save_recipes.call_count,6)
        self.assertTrue(all(len(call.args[0])<=200 for call in repository.save_recipes.call_args_list))


class RawArtifactTests(unittest.TestCase):
    def test_raw_jsonl_import(self):
        import tempfile
        from pathlib import Path
        from services.recipe_import import import_jsonl_gzip
        repository = MagicMock()
        repository.save_recipes.side_effect = lambda batch: len(batch)
        row = {'recipe_id': 42, 'name': 'Raw tomato', 'ingredients': ['tomates'], 'n_ingredients': 1, 'steps': ['Cut tomatoes']}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'recipes.jsonl'
            path.write_text(json.dumps(row) + '\n')
            result = import_jsonl_gzip(path, repository)
        self.assertEqual(result['accepted'], 1)
        recipe = repository.save_recipes.call_args.args[0][0]
        self.assertEqual(recipe.ingredients[0].ingredient_id, 'ing_tomato')
