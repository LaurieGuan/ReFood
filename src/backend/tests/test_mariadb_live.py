"""Opt in with TEST_DATABASE_URL pointing to a dedicated disposable database."""
import os
import unittest
from uuid import uuid4


@unittest.skipUnless(os.environ.get('TEST_DATABASE_URL'), 'MariaDB test database not configured')
class MariaDBLiveTests(unittest.TestCase):
    def test_persistent_roundtrip(self):
        from sqlalchemy import create_engine
        from database.orm_models import Base
        from database.catalog import SQLRepository
        from schemas.pantry import PantryUpdateRequest
        from services.recipe_matcher import sample_recipes
        engine = create_engine(os.environ['TEST_DATABASE_URL'])
        try:
            self.assertIn(engine.dialect.name, ('mysql', 'mariadb'))
            Base.metadata.create_all(engine)
            repository = SQLRepository(engine)
            recipe = sample_recipes()[0]
            recipe.recipe_id = 'test_' + uuid4().hex
            repository.save_recipes([recipe])
            repository.save_recipes([recipe])
            engine.dispose()  # Reopen connections to verify committed data.
            matches = [r for r in repository.get_recipes() if r.recipe_id == recipe.recipe_id]
            self.assertEqual(matches, [recipe])
            user = 'test_' + uuid4().hex
            request = PantryUpdateRequest.model_validate({'items': [recipe.ingredients[0].model_dump(mode='json')]})
            repository.replace_pantry(user, request)
            self.assertEqual(repository.get_pantry(user).items, request.items)
            repository.replace_pantry(user, PantryUpdateRequest(items=[]))
            self.assertEqual(repository.get_pantry(user).items, [])
        finally:
            engine.dispose()
