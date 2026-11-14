"""Central error responses using the existing shared schema."""

from flask import jsonify
from werkzeug.exceptions import HTTPException

from schemas.common import ErrorResponse
from .http_utils import RequestValidationError
from database.errors import MarketplaceError


def error_response(code, message, status, details=None):
    response = ErrorResponse.model_validate({
        "error": {"code": code, "message": message, "details": details}
    })
    return jsonify(response.model_dump(mode="json")), status


def register_error_handlers(app):
    @app.errorhandler(MarketplaceError)
    def marketplace_error(exc):
        return error_response(exc.code, exc.message, exc.status)

    @app.errorhandler(RequestValidationError)
    def invalid_request(exc):
        return error_response(
            "VALIDATION_ERROR", "Invalid request", 422, {"errors": exc.errors}
        )

    @app.errorhandler(HTTPException)
    def http_error(exc):
        code = exc.name.upper().replace(" ", "_")
        body, status = error_response(code, exc.description, exc.code)
        # Preserve HTTP semantics, including Allow and WWW-Authenticate headers.
        response = exc.get_response()
        response.set_data(body.get_data())
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        # Do not include exception text or request payloads in public responses.
        app.logger.error("Unhandled backend exception (%s)", type(exc).__name__)
        return error_response("INTERNAL_SERVER_ERROR", "Internal server error", 500)
