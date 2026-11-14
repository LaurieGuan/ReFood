"""Confirmed user pantry, with explicit memory or MariaDB persistence metadata."""

from importlib import import_module

from flask import Blueprint, current_app, make_response

from schemas.pantry import PantryResponse, PantryUpdateRequest
from werkzeug.exceptions import ServiceUnavailable
from .http_utils import json_response, validate_request
from .demo_identity import demo_user_id

pantry_bp = Blueprint("pantry", __name__)
def get_pantry(user_id: str) -> PantryResponse:
    """Store genuine user data; report process memory when MariaDB is unconfigured."""
    if current_app.config.get("DATABASE_URL"):
        from database.catalog import SQLRepository
        from database.engine import get_engine
        return SQLRepository(get_engine(current_app.config["DATABASE_URL"])).get_pantry(user_id)
    try:
        repository = import_module("database.repositories")
    except ModuleNotFoundError as exc:
        if exc.name != "database.repositories":
            raise
        raise ServiceUnavailable("Pantry repository is not installed") from exc
    return repository._memory.get_pantry(user_id)


def replace_pantry(user_id: str, update: PantryUpdateRequest) -> PantryResponse:
    if current_app.config.get("DATABASE_URL"):
        from database.catalog import SQLRepository
        from database.engine import get_engine
        return SQLRepository(get_engine(current_app.config["DATABASE_URL"])).replace_pantry(user_id, update)
    try:
        repository = import_module("database.repositories")
    except ModuleNotFoundError as exc:
        if exc.name != "database.repositories":
            raise
        raise ServiceUnavailable("Pantry repository is not installed") from exc
    return repository._memory.replace_pantry(user_id, update)


@pantry_bp.get("")
def read_pantry():
    return pantry_response(get_pantry(demo_user_id()))


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
    return pantry_response(result)


def pantry_response(result):
    response = make_response(*json_response(PantryResponse, result))
    response.headers["X-Refood-Source"] = "confirmed_user_input"
    response.headers["X-Refood-Persistence"] = "mariadb" if current_app.config.get("DATABASE_URL") else "memory"
    return response
