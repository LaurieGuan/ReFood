"""Transactional barter repository. No Flask, provider calls or implicit schema setup."""
from datetime import datetime, timezone
from math import isfinite
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from schemas.marketplace import (ExchangeOffer, ExchangeProposal, OfferCreateRequest,
    OfferListResponse, OfferStatus, ProposalCreateRequest, ProposalListResponse, ProposalStatus)
from .engine import get_engine
from .orm_models import (MarketplaceLockRow, ExchangeOfferRow, ExchangeProposalRow,
                        ExchangeReservationRow, PantryInventoryRow)
from .repositories import _validate_user
from .errors import MarketplaceError


def lock_marketplace(session):
    """One DB mutex for the small demo, also acquired by pantry replacement.

    MariaDB holds a row lock until commit/rollback. SQLite tests use a write
    transaction instead; this does not substitute for a live MariaDB test.
    """
    if session.bind.dialect.name == "sqlite":
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        from sqlalchemy.dialects.mysql import insert
        stmt = insert(MarketplaceLockRow).values(lock_id=1, revision=0)
        session.execute(stmt.on_duplicate_key_update(revision=MarketplaceLockRow.revision))
        session.execute(select(MarketplaceLockRow).where(
            MarketplaceLockRow.lock_id == 1).with_for_update()).scalar_one()


def _stock(items, ingredient_id, unit):
    total = 0.0
    for item in items:
        if item.ingredient_id != ingredient_id:
            continue
        # Ambiguous lots must not be silently combined with known stock.
        if (item.quantity.unit.value != unit or item.quantity.amount is None
                or not isfinite(item.quantity.amount) or item.remaining_fraction not in (None, 1)):
            raise MarketplaceError("INVALID_STATE", "Ingredient stock has ambiguous quantities or units")
        total += item.quantity.amount
    return total


def check_reserved_stock(session, user_id, items):
    totals = {}
    for row in session.scalars(select(ExchangeReservationRow).where(
            ExchangeReservationRow.user_id == user_id)):
        key = row.ingredient_id, row.unit
        totals[key] = totals.get(key, 0) + row.amount
    for (ingredient_id, unit), amount in totals.items():
        if _stock(items, ingredient_id, unit) < amount:
            raise MarketplaceError("INSUFFICIENT_STOCK", "Pantry update would consume reserved stock")


class MarketplaceRepository:
    def __init__(self, engine=None):
        self.engine = engine if engine is not None else get_engine()

    @staticmethod
    def _offer(session, offer_id):
        row = session.get(ExchangeOfferRow, offer_id)
        if row is None:
            raise MarketplaceError("NOT_FOUND", "Offer not found", 404)
        return ExchangeOffer.model_validate(row.payload)

    @staticmethod
    def _proposal(session, proposal_id):
        row = session.get(ExchangeProposalRow, proposal_id)
        if row is None:
            raise MarketplaceError("NOT_FOUND", "Proposal not found", 404)
        return ExchangeProposal.model_validate(row.payload)

    @staticmethod
    def _save_offer(session, offer):
        session.merge(ExchangeOfferRow(offer_id=offer.offer_id, owner_id=offer.owner_id,
            status=offer.status.value, payload=offer.model_dump(mode="json")))
        session.flush()

    @staticmethod
    def _save_proposal(session, proposal):
        # Revalidate complete snapshot after state changes.
        proposal = ExchangeProposal.model_validate(proposal.model_dump(mode="json"))
        session.merge(ExchangeProposalRow(proposal_id=proposal.proposal_id,
            target_offer_id=proposal.target_offer_id, proposer_offer_id=proposal.proposer_offer_id,
            status=proposal.status.value, payload=proposal.model_dump(mode="json")))
        session.flush()

    @staticmethod
    def _pantry(session, user_id):
        from schemas.pantry import PantryResponse
        from .catalog import SQLRepository
        return PantryResponse.model_validate({"items": [
            {**SQLRepository._item(row), "remaining_fraction": row.remaining_fraction}
            for row in session.scalars(select(PantryInventoryRow).where(
                PantryInventoryRow.user_id == user_id).order_by(PantryInventoryRow.position))]})

    def _available(self, session, user_id, item):
        available = _stock(self._pantry(session, user_id).items,
                           item.ingredient_id, item.quantity.unit.value)
        for row in session.scalars(select(ExchangeReservationRow).where(
                ExchangeReservationRow.user_id == user_id,
                ExchangeReservationRow.ingredient_id == item.ingredient_id)):
            if row.unit != item.quantity.unit.value:
                raise MarketplaceError("INVALID_STATE", "Reserved unit does not match stock")
            available -= row.amount
        if available < item.quantity.amount:
            raise MarketplaceError("INSUFFICIENT_STOCK", "Not enough unreserved stock")

    def create_offer(self, user_id, request: OfferCreateRequest) -> ExchangeOffer:
        _validate_user(user_id)
        request = OfferCreateRequest.model_validate(request.model_dump(mode="json"))
        with Session(self.engine) as session, session.begin():
            lock_marketplace(session)
            self._available(session, user_id, request.item)
            offer = ExchangeOffer(offer_id=uuid4().hex, owner_id=user_id,
                **request.model_dump(mode="json"), status=OfferStatus.OPEN,
                created_at=datetime.now(timezone.utc))
            self._save_offer(session, offer)
            return offer

    def list_offers(self, status=OfferStatus.OPEN) -> OfferListResponse:
        status = OfferStatus(status)
        with Session(self.engine) as session:
            return OfferListResponse(offers=[ExchangeOffer.model_validate(row.payload)
                for row in session.scalars(select(ExchangeOfferRow).where(
                    ExchangeOfferRow.status == status.value).order_by(ExchangeOfferRow.offer_id))])

    def create_proposal(self, user_id, request: ProposalCreateRequest) -> ExchangeProposal:
        _validate_user(user_id)
        request = ProposalCreateRequest.model_validate(request.model_dump(mode="json"))
        with Session(self.engine) as session, session.begin():
            lock_marketplace(session)
            target = self._offer(session, request.target_offer_id)
            offered = self._offer(session, request.proposer_offer_id)
            if offered.owner_id != user_id or target.owner_id == user_id:
                raise MarketplaceError("FORBIDDEN", "Proposals require offers from two distinct owners", 403)
            if target.status != OfferStatus.OPEN or offered.status != OfferStatus.OPEN:
                raise MarketplaceError("INVALID_STATE", "Both offers must be open")
            items = []
            for offer, quantity in ((target, request.target_quantity), (offered, request.proposer_quantity)):
                if quantity.unit != offer.item.quantity.unit or quantity.amount > offer.item.quantity.amount:
                    raise MarketplaceError("INVALID_STATE", "Proposed quantity does not fit offer")
                item = offer.item.model_copy(deep=True)
                item.quantity = quantity.model_copy(deep=True)
                items.append(item)
            now = datetime.now(timezone.utc)
            proposal = ExchangeProposal(proposal_id=uuid4().hex, target_owner_id=target.owner_id,
                proposer_id=user_id, target_offer_id=target.offer_id, proposer_offer_id=offered.offer_id,
                target_item=items[0], proposer_item=items[1], status=ProposalStatus.PENDING,
                created_at=now, updated_at=now)
            self._save_proposal(session, proposal)
            return proposal

    def list_proposals(self, user_id) -> ProposalListResponse:
        _validate_user(user_id)
        with Session(self.engine) as session:
            proposals = [ExchangeProposal.model_validate(row.payload)
                for row in session.scalars(select(ExchangeProposalRow).order_by(ExchangeProposalRow.proposal_id))]
            return ProposalListResponse(proposals=[p for p in proposals
                if user_id in (p.target_owner_id, p.proposer_id)])

    def close_offer(self, user_id, offer_id) -> ExchangeOffer:
        _validate_user(user_id)
        with Session(self.engine) as session, session.begin():
            lock_marketplace(session)
            offer = self._offer(session, offer_id)
            if offer.owner_id != user_id:
                raise MarketplaceError("FORBIDDEN", "Only owner may close offer", 403)
            if offer.status == OfferStatus.RESERVED:
                raise MarketplaceError("INVALID_STATE", "Cancel the accepted proposal first")
            offer.status = OfferStatus.CLOSED
            self._save_offer(session, offer)
            self._reject_competing(session, {offer_id})
            return offer

    def _reject_competing(self, session, offer_ids, except_id=None):
        for row in session.scalars(select(ExchangeProposalRow).where(
                ExchangeProposalRow.status == ProposalStatus.PENDING.value)).all():
            proposal = ExchangeProposal.model_validate(row.payload)
            if proposal.proposal_id != except_id and offer_ids & {proposal.target_offer_id, proposal.proposer_offer_id}:
                proposal.status = ProposalStatus.REJECTED
                proposal.updated_at = datetime.now(timezone.utc)
                self._save_proposal(session, proposal)

    def _action(self, user_id, proposal_id, action):
        _validate_user(user_id)
        with Session(self.engine) as session, session.begin():
            lock_marketplace(session)
            proposal = self._proposal(session, proposal_id)
            if user_id not in (proposal.target_owner_id, proposal.proposer_id):
                raise MarketplaceError("FORBIDDEN", "Only participants may act", 403)
            if action in ("accept", "reject") and user_id != proposal.target_owner_id:
                raise MarketplaceError("FORBIDDEN", "Only target owner may respond", 403)
            state = proposal.status
            if ((action == "accept" and state == ProposalStatus.ACCEPTED)
                or (action == "cancel" and state == ProposalStatus.CANCELLED)
                or (action == "reject" and state == ProposalStatus.REJECTED)
                or (action == "confirm" and state == ProposalStatus.COMPLETED)):
                return proposal
            if action in ("accept", "reject") and state != ProposalStatus.PENDING:
                raise MarketplaceError("INVALID_STATE", "Proposal is no longer pending")
            if action == "cancel" and state not in (ProposalStatus.PENDING, ProposalStatus.ACCEPTED):
                raise MarketplaceError("INVALID_STATE", "Proposal cannot be cancelled")
            if action == "confirm" and state != ProposalStatus.ACCEPTED:
                raise MarketplaceError("INVALID_STATE", "Only accepted proposals may be confirmed")
            offers = [self._offer(session, proposal.target_offer_id), self._offer(session, proposal.proposer_offer_id)]
            legs = [(proposal.target_owner_id, proposal.target_item), (proposal.proposer_id, proposal.proposer_item)]
            if action == "accept":
                if any(o.status != OfferStatus.OPEN for o in offers):
                    raise MarketplaceError("INVALID_STATE", "An offer is no longer open")
                for owner, item in legs:
                    self._available(session, owner, item)
                    session.add(ExchangeReservationRow(proposal_id=proposal.proposal_id,
                        user_id=owner, ingredient_id=item.ingredient_id,
                        amount=item.quantity.amount, unit=item.quantity.unit.value))
                for offer in offers:
                    offer.status = OfferStatus.RESERVED
                    self._save_offer(session, offer)
                proposal.status = ProposalStatus.ACCEPTED
                self._reject_competing(session, {o.offer_id for o in offers}, proposal.proposal_id)
            elif action == "reject":
                proposal.status = ProposalStatus.REJECTED
            elif action == "cancel":
                if state == ProposalStatus.ACCEPTED:
                    for offer in offers:
                        offer.status = OfferStatus.OPEN
                        self._save_offer(session, offer)
                    session.execute(delete(ExchangeReservationRow).where(
                        ExchangeReservationRow.proposal_id == proposal_id))
                proposal.status = ProposalStatus.CANCELLED
            elif action == "confirm":
                if user_id not in proposal.confirmed_by:
                    proposal.confirmed_by.append(user_id)
                if len(proposal.confirmed_by) == 2:
                    self._transfer(session, legs)
                    session.execute(delete(ExchangeReservationRow).where(
                        ExchangeReservationRow.proposal_id == proposal_id))
                    for offer in offers:
                        offer.status = OfferStatus.CLOSED
                        self._save_offer(session, offer)
                    proposal.status = ProposalStatus.COMPLETED
            proposal.updated_at = datetime.now(timezone.utc)
            self._save_proposal(session, proposal)
            return proposal

    def _transfer(self, session, legs):
        from schemas.pantry import PantryItem
        from .catalog import SQLRepository
        inventories = {owner: self._pantry(session, owner).items for owner, _ in legs}
        for owner, item in legs:
            if _stock(inventories[owner], item.ingredient_id, item.quantity.unit.value) < item.quantity.amount:
                raise MarketplaceError("INSUFFICIENT_STOCK", "Reserved stock is no longer available")
            remaining = item.quantity.amount
            for lot in inventories[owner]:
                if lot.ingredient_id == item.ingredient_id:
                    debit = min(remaining, lot.quantity.amount)
                    lot.quantity.amount -= debit
                    remaining -= debit
        for index, (owner, _) in enumerate(legs):
            received = legs[1 - index][1]
            inventories[owner].append(PantryItem.model_validate(received.model_dump(mode="json")))
            session.execute(delete(PantryInventoryRow).where(PantryInventoryRow.user_id == owner))
            for position, item in enumerate(inventories[owner]):
                SQLRepository._ingredient(session, item)
                session.add(PantryInventoryRow(user_id=owner, position=position,
                    ingredient_id=item.ingredient_id, name=item.name, amount=item.quantity.amount,
                    unit=item.quantity.unit.value, remaining_fraction=item.remaining_fraction))
            session.flush()

    def accept_proposal(self, user_id, proposal_id):
        return self._action(user_id, proposal_id, "accept")

    def reject_proposal(self, user_id, proposal_id):
        return self._action(user_id, proposal_id, "reject")

    def cancel_proposal(self, user_id, proposal_id):
        return self._action(user_id, proposal_id, "cancel")

    def confirm_proposal(self, user_id, proposal_id):
        return self._action(user_id, proposal_id, "confirm")
