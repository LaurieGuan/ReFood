"""Ingredient barter contracts. HTTP: Dev 1; persistence: Dev 2.

Identity, stock availability and state transitions must be checked by services.
Schema validation alone never confirms ownership or reserves inventory.
"""
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


class ExchangeOffer(BaseModel):
    offer_id: Identifier
    owner_id: Identifier
    item: TradeItem
    description: str | None = Field(default=None, max_length=1000)
    meeting_area: MeetingArea
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
