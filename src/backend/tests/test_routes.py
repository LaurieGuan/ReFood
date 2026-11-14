import io
import unittest
from unittest.mock import patch

from app import create_app
from schemas.ingredients import Certainty
from schemas.pantry import PantryResponse
from schemas.recipes import RecipeMatch
from schemas.scanning import ScanCandidate


def ingredient_payload(ingredient_id="ing_egg", name="egg"):
    return {
        "ingredient_id": ingredient_id,
        "name": name,
        "quantity": {"amount": None, "unit": "unknown"},
    }


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "DATABASE_URL": None})
        self.client = self.app.test_client()

    def test_recipe_search_calls_matcher_and_serializes_schema_response(self):
        match = RecipeMatch.model_validate({
            "recipe": {"recipe_id": "recipe_omelette", "title": "Omelette",
                       "ingredients": [ingredient_payload()]},
            "match_score": 0.8, "missing_ingredients": [],
        })
        request_body = {"ingredients": [ingredient_payload()], "limit": 1}
        with patch("routes.recipes.find_recipes", return_value=[match, match]) as matcher:
            response = self.client.post("/api/v1/recipes/search", json=request_body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["results"]), 1)
        matcher.assert_called_once()
        self.assertEqual(matcher.call_args.args[0].ingredients[0].ingredient_id, "ing_egg")

    def test_recipe_search_returns_400_for_malformed_json_and_422_for_invalid_model(self):
        malformed = self.client.post("/api/v1/recipes/search", data="{",
                                     content_type="application/json")
        invalid = self.client.post(
            "/api/v1/recipes/search", json={"ingredients": [], "limit": 0}
        )
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(malformed.get_json()["error"]["code"], "BAD_REQUEST")
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.get_json()["error"]["code"], "VALIDATION_ERROR")

    def test_recipe_search_hides_matcher_failures(self):
        with patch("routes.recipes.find_recipes", side_effect=RuntimeError("private")):
            response = self.client.post("/api/v1/recipes/search", json={"ingredients": []})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "INTERNAL_SERVER_ERROR")
        self.assertNotIn("private", response.get_data(as_text=True))

    def test_scan_returns_candidates_without_mutating_pantry(self):
        candidate = ScanCandidate.model_validate({
            **ingredient_payload("candidate_tomato", "tomato"),
            "candidate_id": "candidate_tomato", "certainty": Certainty.LOW,
        })
        before = self.client.get("/api/v1/pantry").get_json()
        with patch("routes.scans.scan_fridge", return_value=[candidate]) as scanner:
            response = self.client.post("/api/v1/scans", data={
                "image": (io.BytesIO(b"fake image"), "fridge.jpg", "image/jpeg")
            })
        after = self.client.get("/api/v1/pantry").get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["candidates"][0]["certainty"], "low")
        self.assertTrue(response.get_json()["scan_id"].startswith("scan_"))
        self.assertEqual(before, after)
        scanner.assert_called_once_with(b"fake image")

    def test_scan_requires_nonempty_image(self):
        missing = self.client.post("/api/v1/scans", data={})
        empty = self.client.post("/api/v1/scans", data={
            "image": (io.BytesIO(b""), "fridge.jpg", "image/jpeg")
        })
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(empty.status_code, 400)

    def test_pantry_get_and_put_use_schema_and_replace_existing_items(self):
        update = {"items": [ingredient_payload("ing_milk", "milk")]}
        response = self.client.put("/api/v1/pantry", json=update)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["items"][0]["ingredient_id"], "ing_milk")
        self.assertEqual(response.get_json()["items"][0]["remaining_fraction"], None)
        fetched = self.client.get("/api/v1/pantry")
        self.assertEqual(fetched.get_json(), response.get_json())
        invalid = self.client.put("/api/v1/pantry", json={"items": [{"name": "missing id"}]})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.get_json()["error"]["code"], "VALIDATION_ERROR")

    def tearDown(self):
        # Keep the in-memory mock isolated between tests.
        from routes import pantry
        pantry._demo_pantry = PantryResponse()


if __name__ == "__main__":
    unittest.main()
