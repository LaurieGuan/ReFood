"""Ingredient barter contracts. HTTP: Dev 1; persistence: Dev 2.

Identity, stock availability and state transitions must be checked by services.
Schema validation alone never confirms ownership or reserves inventory.
"""
import base64
import binascii
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .ingredients import IngredientQuantity, IngredientWithQuantity, Unit


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=191)]
MeetingArea = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


def _known_quantity(quantity: IngredientQuantity) -> IngredientQuantity:
    if quantity.amount is None or not isfinite(quantity.amount) or quantity.amount <= 0:
        raise ValueError("Trade quantities must be finite and strictly positive")
    if quantity.unit == Unit.UNKNOWN:
        raise ValueError("Trade quantities require a known unit")
    return quantity


def _trade_item(item: IngredientWithQuantity) -> IngredientWithQuantity:
    if not item.ingredient_id.strip() or not item.name.strip():
        raise ValueError("Trade items require a canonical ingredient ID and name")
    _known_quantity(item.quantity)
    return item


TradeQuantity = Annotated[IngredientQuantity, AfterValidator(_known_quantity)]
TradeItem = Annotated[IngredientWithQuantity, AfterValidator(_trade_item)]
UTCTimestamp = Annotated[AwareDatetime, AfterValidator(lambda value: value.astimezone(timezone.utc))]


def _offer_photo(value: str | None) -> str | None:
    if value is None:
        return None
    prefixes = {"data:image/jpeg;base64,": b"\xff\xd8\xff", "data:image/png;base64,": b"\x89PNG\r\n\x1a\n", "data:image/webp;base64,": b"RIFF"}
    prefix = next((key for key in prefixes if value.startswith(key)), None)
    if prefix is None or len(value) > 700000:
        raise ValueError("Photo must be a JPEG, PNG or WebP of at most 512 KiB")
    try:
        data = base64.b64decode(value[len(prefix):], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid photo encoding") from exc
    if len(data) > 512 * 1024 or not data.startswith(prefixes[prefix]):
        raise ValueError("Invalid photo or photo exceeds 512 KiB")
    if prefix == "data:image/webp;base64," and data[8:12] != b"WEBP":
        raise ValueError("Invalid WebP photo")
    return value


OfferPhoto = Annotated[str | None, AfterValidator(_offer_photo)]


class OfferStatus(str, Enum):
    OPEN = "open"
    RESERVED = "reserved"
    CLOSED = "closed"


class ProposalStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class OfferCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: TradeItem
    description: str | None = Field(default=None, max_length=1000)
    meeting_area: MeetingArea
    photo_data_url: OfferPhoto = None


class ExchangeOffer(BaseModel):
    offer_id: Identifier
    owner_id: Identifier
    item: TradeItem
    description: str | None = Field(default=None, max_length=1000)
    meeting_area: MeetingArea
    photo_data_url: OfferPhoto = None
    status: OfferStatus
    created_at: UTCTimestamp


class OfferListResponse(BaseModel):
    offers: list[ExchangeOffer] = Field(default_factory=list)


class ProposalCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_offer_id: Identifier
    proposer_offer_id: Identifier
    target_quantity: TradeQuantity
    proposer_quantity: TradeQuantity

    @model_validator(mode="after")
    def distinct_offers(self):
        if self.target_offer_id == self.proposer_offer_id:
            raise ValueError("An offer cannot be exchanged with itself")
        return self


class ExchangeProposal(BaseModel):
    proposal_id: Identifier
    target_owner_id: Identifier
    proposer_id: Identifier
    target_offer_id: Identifier
    proposer_offer_id: Identifier
    target_item: TradeItem
    proposer_item: TradeItem
    status: ProposalStatus
    confirmed_by: list[Identifier] = Field(default_factory=list)
    created_at: UTCTimestamp
    updated_at: UTCTimestamp

    @model_validator(mode="after")
    def consistent_snapshot(self):
        if self.target_owner_id == self.proposer_id:
            raise ValueError("A user cannot trade with themselves")
        if self.target_offer_id == self.proposer_offer_id:
            raise ValueError("An offer cannot be exchanged with itself")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        participants = {self.target_owner_id, self.proposer_id}
        confirmations = set(self.confirmed_by)
        if len(confirmations) != len(self.confirmed_by) or not confirmations <= participants:
            raise ValueError("Confirmations must identify distinct participants")
        if self.status == ProposalStatus.COMPLETED and confirmations != participants:
            raise ValueError("Completion requires both participants' confirmations")
        if self.status == ProposalStatus.ACCEPTED and len(confirmations) > 1:
            raise ValueError("Both confirmations must atomically complete the exchange")
        if self.status in (ProposalStatus.PENDING, ProposalStatus.REJECTED) and confirmations:
            raise ValueError("An unaccepted proposal cannot have confirmations")
        return self


class ProposalListResponse(BaseModel):
    proposals: list[ExchangeProposal] = Field(default_factory=list)
