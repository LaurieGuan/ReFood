"""Pantry HTTP endpoints with a replaceable in-memory demo adapter."""

from importlib import import_module

from flask import Blueprint

from schemas.pantry import PantryResponse, PantryUpdateRequest
from .http_utils import json_response, validate_request

pantry_bp = Blueprint("pantry", __name__)
DEMO_USER_ID = "demo_user"

# Explicit demo mock, replaced when Developer 2's repository is available.
_demo_pantry = PantryResponse()


def get_pantry(user_id: str) -> PantryResponse:
    """Call Developer 2's repository, with the local demo store as fallback."""
    try:
        repository = import_module("database.repositories")
    except ModuleNotFoundError as exc:
        if exc.name != "database.repositories":
            raise
        return _demo_pantry
    return repository.get_pantry(user_id)


def replace_pantry(user_id: str, update: PantryUpdateRequest) -> PantryResponse:
    global _demo_pantry
    try:
        repository = import_module("database.repositories")
    except ModuleNotFoundError as exc:
        if exc.name != "database.repositories":
            raise
        _demo_pantry = PantryResponse(items=update.items)
        return _demo_pantry
    return repository.replace_pantry(user_id, update)


@pantry_bp.get("")
def read_pantry():
    return json_response(PantryResponse, get_pantry(DEMO_USER_ID))


@pantry_bp.put("")
def update_pantry():
    update = validate_request(PantryUpdateRequest)
    result = replace_pantry(DEMO_USER_ID, update)
    return json_response(PantryResponse, result)
