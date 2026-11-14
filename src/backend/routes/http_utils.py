"""Request validation errors are 422; invalid server responses remain 500."""

from flask import jsonify, request
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest


class RequestValidationError(Exception):
    def __init__(self, errors):
        super().__init__("Invalid request")
        self.errors = errors


def validate_request(model):
    if not request.is_json:
        raise BadRequest("Expected a JSON request body")
    payload = request.get_json()
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        # Exclude raw input/context, which may contain secrets or non-JSON objects.
        raise RequestValidationError(
            exc.errors(include_url=False, include_context=False, include_input=False)
        ) from exc


def json_response(model, data, status=200):
    response = model.model_validate(data)
    return jsonify(response.model_dump(mode="json")), status
