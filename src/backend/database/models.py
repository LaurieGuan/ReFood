"""Storage records, separate from the public Pydantic models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PantryRecord:
    user_id: str
    payload: str
