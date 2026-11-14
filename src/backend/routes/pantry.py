"""Pantry HTTP endpoints with a replaceable in-memory demo adapter."""

from importlib import import_module

from flask import Blueprint, current_app

from schemas.pantry import PantryResponse, PantryUpdateRequest
from .http_utils import json_response, validate_request
from .demo_identity import demo_user_id

pantry_bp = Blueprint("pantry", __name__)
DEMO_USER_ID = "demo_user"

# Explicit demo mock, replaced when Developer 2's repository is available.
_demo_pantry = PantryResponse()


def get_pantry(user_id: str) -> PantryResponse:
    """Call Developer 2's repository, with the local demo store as fallback."""
    if current_app.config.get("DATABASE_URL"):
        from database.catalog import SQLRepository
        from database.engine import get_engine
        return SQLRepository(get_engine(current_app.config["DATABASE_URL"])).get_pantry(user_id)
    try:
        repository = import_module("database.repositories")
    except ModuleNotFoundError as exc:
        if exc.name != "database.repositories":
            raise
        return _demo_pantry
    return repository._memory.get_pantry(user_id)


def replace_pantry(user_id: str, update: PantryUpdateRequest) -> PantryResponse:
    global _demo_pantry
    if current_app.config.get("DATABASE_URL"):
        from database.catalog import SQLRepository
        from database.engine import get_engine
        return SQLRepository(get_engine(current_app.config["DATABASE_URL"])).replace_pantry(user_id, update)
    try:
        repository = import_module("database.repositories")
    except ModuleNotFoundError as exc:
        if exc.name != "database.repositories":
            raise
        _demo_pantry = PantryResponse(items=update.items)
        return _demo_pantry
    return repository._memory.replace_pantry(user_id, update)


@pantry_bp.get("")
def read_pantry():
    return json_response(PantryResponse, get_pantry(demo_user_id()))


@pantry_bp.put("")
def update_pantry():
    update = validate_request(PantryUpdateRequest)
    from services.pantry_confirmation import confirm_pantry
    from werkzeug.exceptions import UnprocessableEntity
    try:
        update = confirm_pantry(update)
    except ValueError as exc:
        raise UnprocessableEntity(str(exc)) from None
    result = replace_pantry(demo_user_id(), update)
    return json_response(PantryResponse, result)
