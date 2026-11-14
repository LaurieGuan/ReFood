import unittest
from copy import deepcopy
from unittest.mock import patch

from app import create_app


EGG = {"ingredient_id": "ing_egg", "name": "egg"}
TOFU = {"ingredient_id": "ing_tofu", "name": "tofu"}


class EnrichmentRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app({"TESTING": True}).test_client()

    def test_search_preserves_optional_metadata_and_old_recipes(self):
        base = {"recipe_id": "r1", "title": "Recipe", "ingredients": [EGG]}
        enriched = {**base, "source": "dataset", "source_recipe_id": "42",
                    "description": "A recipe", "tags": ["easy"],
                    "nutrition": {"calories": 120, "protein_pdv": 15},
                    "rating": 4.5, "num_ratings": 3}
        matches = [{"recipe": item, "match_score": 1, "missing_ingredients": []}
                   for item in (base, enriched)]
        with patch("routes.recipes.find_recipes", return_value=matches):
            response = self.client.post("/api/v1/recipes/search", json={"ingredients": []})
        self.assertEqual(response.status_code, 200)
        old, new = [match["recipe"] for match in response.get_json()["results"]]
        self.assertIsNone(old["nutrition"])
        self.assertEqual(new["source_recipe_id"], "42")
        self.assertEqual(new["nutrition"]["protein_pdv"], 15)
        self.assertEqual(new["tags"], ["easy"])

    def test_grocery_search_passes_query_and_serializes_products(self):
        result = {"query": "tofu", "results": [{"provider_product_id": "sku1",
                  "name": "Tofu", "cheapest_price_cents": 399}], "source": "test"}
        with patch("routes.grocery.search_grocery_products", return_value=result) as search:
            response = self.client.get("/api/v1/grocery/products/search?q=tofu&limit=3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["results"][0]["cheapest_price_cents"], 399)
        search.assert_called_once_with("tofu", 3)

    def test_grocery_mock_and_bad_queries(self):
        # Route tests must not depend on live provider connectivity.
        mock_result = {"query": "milk", "results": [], "source": "mock"}
        with patch("routes.grocery.search_grocery_products", return_value=mock_result):
            response = self.client.get("/api/v1/grocery/products/search?q=milk")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["source"], "mock")
        for query in ("", "?q=a", "?q=milk&limit=x", "?q=milk&limit=0"):
            with self.subTest(query=query):
                response = self.client.get("/api/v1/grocery/products/search" + query)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"]["code"], "BAD_REQUEST")

    def test_suggestions_are_proposals_and_do_not_apply_swaps(self):
        request = {"recipe_id": "r1", "ingredient_id": "ing_egg", "pantry": [TOFU]}
        result = {"recipe_id": "r1", "original_ingredient_id": "ing_egg",
                  "suggestions": [{"original_ingredient_id": "ing_egg",
                                   "replacement": TOFU, "source": "pantry"}]}
        with patch("routes.recipes.suggest_substitutions", return_value=result) as suggest, \
             patch("routes.recipes.calculate_variation") as apply:
            response = self.client.post("/api/v1/recipes/substitutions", json=request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["suggestions"][0]["source"], "pantry")
        self.assertEqual(suggest.call_args.args[0].ingredient_id, "ing_egg")
        apply.assert_not_called()

    def test_variation_returns_missing_items_and_forces_review_flags(self):
        payload = {"recipe_id": "r1", "swaps": [{"original_ingredient_id": "ing_egg",
                   "replacement": TOFU}], "pantry": []}
        original = deepcopy(payload)
        result = {"original_recipe_id": "r1", "updated_ingredients": [TOFU],
                  "missing_ingredients": [TOFU], "instructions_need_review": False,
                  "nutrition_needs_recalculation": False, "warnings": ["Existing warning"]}
        with patch("routes.recipes.calculate_variation", return_value=result) as calculate:
            response = self.client.post("/api/v1/recipes/variations", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["missing_ingredients"][0]["ingredient_id"], "ing_tofu")
        self.assertTrue(body["instructions_need_review"])
        self.assertTrue(body["nutrition_needs_recalculation"])
        self.assertIn("Existing warning", body["warnings"])
        self.assertEqual(payload, original)
        self.assertEqual(calculate.call_args.args[0].swaps[0].replacement.ingredient_id, "ing_tofu")

    def test_missing_variation_service_returns_503(self):
        response = self.client.post("/api/v1/recipes/variations", json={"recipe_id": "r1"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"]["code"], "SERVICE_UNAVAILABLE")

    def test_invalid_requests_and_provider_failure_are_json(self):
        for path in ("/api/v1/recipes/substitutions", "/api/v1/recipes/variations"):
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, json={}).status_code, 422)
                self.assertEqual(self.client.post(path, data="{", content_type="application/json").status_code, 400)
        with patch("routes.grocery.search_grocery_products", side_effect=RuntimeError("private")):
            response = self.client.get("/api/v1/grocery/products/search?q=milk")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
