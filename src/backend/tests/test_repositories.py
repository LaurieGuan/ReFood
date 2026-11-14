import os
import unittest
from unittest.mock import Mock, patch

from database.connection import connect
from database.repositories import (
    MemoryPantryRepository, MariaDBPantryRepository, get_pantry, replace_pantry,
)
from schemas.pantry import PantryResponse, PantryUpdateRequest


def update(name="egg"):
    return PantryUpdateRequest.model_validate({"items": [{
        "ingredient_id": "ing_egg", "name": name, "remaining_fraction": .5,
    }]})


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryPantryRepository()

    def test_get_replace_clear_and_user_isolation(self):
        self.assertEqual(self.repo.get_pantry("alice").items, [])
        result = self.repo.replace_pantry("alice", update())
        self.assertIsInstance(result, PantryResponse)
        self.assertIsNone(result.items[0].quantity.amount)
        self.assertEqual(result.items[0].remaining_fraction, .5)
        self.assertEqual(self.repo.get_pantry("bob").items, [])
        self.repo.replace_pantry("alice", update("oeuf"))
        self.assertEqual(len(self.repo.get_pantry("alice").items), 1)
        self.assertEqual(self.repo.get_pantry("alice").items[0].name, "oeuf")
        self.repo.replace_pantry("alice", PantryUpdateRequest(items=[]))
        self.assertEqual(self.repo.get_pantry("alice").items, [])

    def test_caller_mutations_do_not_change_storage(self):
        request = update()
        result = self.repo.replace_pantry("alice", request)
        request.items.clear()
        result.items[0].name = "changed"
        read = self.repo.get_pantry("alice")
        self.assertEqual(read.items[0].name, "egg")
        read.items.clear()
        self.assertEqual(len(self.repo.get_pantry("alice").items), 1)

    def test_invalid_user(self):
        for value in ("", " ", "a" * 192, None):
            with self.assertRaises(ValueError):
                self.repo.get_pantry(value)

    def test_public_functions_without_database(self):
        with patch.dict(os.environ, {"DATABASE_URL": ""}):
            replace_pantry("test_public", update())
            self.assertEqual(get_pantry("test_public").items[0].ingredient_id, "ing_egg")
            replace_pantry("test_public", PantryUpdateRequest(items=[]))


class MariaDBAdapterTests(unittest.TestCase):
    """DB-API contract tests with fakes, not live MariaDB integration tests."""

    def setUp(self):
        self.connection = Mock()
        self.cursor = self.connection.cursor.return_value
        self.repo = MariaDBPantryRepository(lambda: self.connection)

    def test_read_maps_storage_payload(self):
        self.cursor.fetchone.return_value = (update().model_dump_json(),)
        self.assertEqual(self.repo.get_pantry("alice").items[0].name, "egg")
        self.cursor.execute.assert_called_once_with(
            "SELECT payload FROM pantry WHERE user_id = ?", ("alice",))
        self.cursor.close.assert_called_once()
        self.connection.close.assert_called_once()

    def test_missing_user(self):
        self.cursor.fetchone.return_value = None
        self.assertEqual(self.repo.get_pantry("alice").items, [])

    def test_replace_parameterizes_and_commits(self):
        self.repo.replace_pantry("x' OR 1=1", update())
        sql, parameters = self.cursor.execute.call_args.args
        self.assertNotIn("x' OR 1=1", sql)
        self.assertEqual(parameters[0], "x' OR 1=1")
        self.connection.commit.assert_called_once()
        self.connection.rollback.assert_not_called()
        self.connection.close.assert_called_once()

    def test_failure_rolls_back_and_closes(self):
        self.cursor.execute.side_effect = RuntimeError("database unavailable")
        with self.assertRaises(RuntimeError):
            self.repo.replace_pantry("alice", update())
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()
        self.cursor.close.assert_called_once()
        self.connection.close.assert_called_once()

    def test_bad_url_does_not_connect(self):
        with patch.dict(os.environ, {"DATABASE_URL": "mysql://example/db"}):
            with self.assertRaises(ValueError):
                connect()

    def test_app_creation_never_connects(self):
        from app import create_app
        with patch.dict(os.environ, {"DATABASE_URL": "mariadb://unreachable/demo"}):
            with patch("database.repositories._mariadb._connect", side_effect=AssertionError):
                self.assertEqual(create_app({"TESTING": True}).test_client().get(
                    "/api/v1/health").status_code, 200)
