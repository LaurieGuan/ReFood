"""Donation offers use counted portions/packages, separate from pantry quantities."""
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from .marketplace import Identifier, UTCTimestamp

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Count = Annotated[int, Field(strict=True, ge=1, le=1000000)]


class DonationStatus(str, Enum):
    ACTIVE = "active"
    SOLD_OUT = "sold_out"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ReservationStatus(str, Enum):
    RESERVED = "reserved"
    COLLECTED = "collected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class DonationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: ShortText
    description: str | None = Field(default=None, max_length=2000)
    total_quantity: Count
    per_person_limit: Count
    unit_label: ShortText
    pickup_location: ShortText
    pickup_starts_at: UTCTimestamp | None = None
    expires_at: UTCTimestamp

    @model_validator(mode="after")
    def valid_limits(self):
        if self.per_person_limit > self.total_quantity:
            raise ValueError("per_person_limit cannot exceed total_quantity")
        if self.pickup_starts_at is not None and self.pickup_starts_at >= self.expires_at:
            raise ValueError("Pickup must start before expiry")
        return self


class DonationOffer(DonationCreateRequest):
    offer_id: Identifier
    business_id: Identifier
    status: DonationStatus
    reserved_quantity: int = Field(ge=0)
    collected_quantity: int = Field(ge=0)
    available_quantity: int = Field(ge=0)
    created_at: UTCTimestamp


class DonationListResponse(BaseModel):
    offers: list[DonationOffer] = Field(default_factory=list)


class ReservationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quantity: Count


class DonationReservation(BaseModel):
    reservation_id: Identifier
    offer_id: Identifier
    student_id: Identifier
    quantity: Count
    status: ReservationStatus
    expires_at: UTCTimestamp
    created_at: UTCTimestamp
    collected_at: UTCTimestamp | None = None
    cancelled_at: UTCTimestamp | None = None


class ReservationListResponse(BaseModel):
    reservations: list[DonationReservation] = Field(default_factory=list)
