import unittest

from app import create_app
from routes.http_utils import json_response, validate_request
from schemas.pantry import PantryUpdateRequest


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "DATABASE_URL": None})

        @self.app.post("/_test/validate")
        def validate():
            data = validate_request(PantryUpdateRequest)
            return json_response(PantryUpdateRequest, data)

        @self.app.get("/_test/broken-response")
        def broken_response():
            return json_response(PantryUpdateRequest, {})

        self.client = self.app.test_client()

    def test_health_without_credentials(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok", "service": "refood"})

    def test_missing_and_malformed_json(self):
        for kwargs in ({}, {"data": "{", "content_type": "application/json"}):
            with self.subTest(kwargs=kwargs):
                response = self.client.post("/_test/validate", **kwargs)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"]["code"], "BAD_REQUEST")

    def test_invalid_request(self):
        response = self.client.post("/_test/validate", json={})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("errors", response.get_json()["error"]["details"])

    def test_valid_request_serializes_nested_enums(self):
        payload = {"items": [{"ingredient_id": "ing_egg", "name": "egg"}]}
        response = self.client.post("/_test/validate", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["items"][0]["quantity"],
                         {"amount": None, "unit": "unknown"})

    def test_missing_route(self):
        response = self.client.get("/api/v1/missing")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "NOT_FOUND")

    def test_method_not_allowed_preserves_allow_header(self):
        response = self.client.post("/api/v1/health")
        self.assertEqual(response.status_code, 405)
        self.assertIn("GET", response.headers["Allow"])

    def test_invalid_server_response_is_private_500(self):
        response = self.client.get("/_test/broken-response")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {"error": {
            "code": "INTERNAL_SERVER_ERROR", "message": "Internal server error",
            "details": None,
        }})

    def test_factories_have_independent_config(self):
        other = create_app({"TESTING": False})
        self.assertFalse(other.testing)
        self.assertTrue(self.app.testing)
