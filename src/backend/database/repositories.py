"""Pantry replacement with a demo memory store or explicitly selected MariaDB."""

import json
import os
from threading import RLock

from schemas.pantry import PantryResponse, PantryUpdateRequest
from .connection import connect
from .models import PantryRecord


def _validate_user(user_id):
    if not isinstance(user_id, str) or not user_id.strip() or len(user_id) > 191:
        raise ValueError("user_id must be a non-empty string of at most 191 characters")


def _response(record):
    return PantryResponse.model_validate(json.loads(record.payload)) if record else PantryResponse()


def _record(user_id, request):
    _validate_user(user_id)
    request = PantryUpdateRequest.model_validate(request)
    return PantryRecord(user_id, json.dumps(request.model_dump(mode="json")))


class MemoryPantryRepository:
    """Demo fallback: process-local and intentionally not durable."""

    def __init__(self):
        self._records = {}
        self._lock = RLock()

    def get_pantry(self, user_id: str) -> PantryResponse:
        _validate_user(user_id)
        with self._lock:
            return _response(self._records.get(user_id))

    def replace_pantry(self, user_id: str, request: PantryUpdateRequest) -> PantryResponse:
        record = _record(user_id, request)
        with self._lock:
            self._records[user_id] = record
        return _response(record)


class MariaDBPantryRepository:
    def __init__(self, connection_factory=connect):
        self._connect = connection_factory

    def get_pantry(self, user_id: str) -> PantryResponse:
        _validate_user(user_id)
        connection = self._connect()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT payload FROM pantry WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                return _response(PantryRecord(user_id, row[0]) if row else None)
            finally:
                cursor.close()
        finally:
            connection.close()

    def replace_pantry(self, user_id: str, request: PantryUpdateRequest) -> PantryResponse:
        record = _record(user_id, request)
        connection = self._connect()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    "INSERT INTO pantry (user_id, payload) VALUES (?, ?) "
                    "ON DUPLICATE KEY UPDATE payload = VALUES(payload)",
                    (record.user_id, record.payload),
                )
                connection.commit()
            finally:
                cursor.close()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return _response(record)


_memory = MemoryPantryRepository()
_mariadb = MariaDBPantryRepository()


def _repository():
    # A configured-but-broken database must fail visibly, never silently lose data.
    return _mariadb if os.environ.get("DATABASE_URL") else _memory


def get_pantry(user_id: str) -> PantryResponse:
    return _repository().get_pantry(user_id)


def replace_pantry(user_id: str, request: PantryUpdateRequest) -> PantryResponse:
    return _repository().replace_pantry(user_id, request)
