"""Donation reservations: atomic quantities, per-student limits and server expiry."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from schemas.donations import (DonationCreateRequest, DonationOffer, DonationListResponse,
    DonationReservation, ReservationCreateRequest, ReservationListResponse,
    DonationStatus, ReservationStatus)
from .engine import get_engine
from .errors import DonationError
from .marketplace import lock_marketplace
from .orm_models import DonationOfferRow, DonationReservationRow


def demo_role(user_id):
    # Trusted mapping for the demo, never a role supplied in request JSON.
    if user_id == "shop_demo":
        return "business"
    if user_id in {"alice", "bob", "demo_user"}:
        return "student"
    raise DonationError("FORBIDDEN", "Unknown demo identity", 403)


def _require(user_id, role):
    if demo_role(user_id) != role:
        raise DonationError("FORBIDDEN", "This operation requires a " + role, 403)


def _data(row):
    return DonationCreateRequest.model_validate({key: value for key, value in row.payload.items()
                                               if key != "created_at"})


class DonationRepository:
    def __init__(self, engine=None, clock=None):
        self.engine = engine if engine is not None else get_engine()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _row(session, offer_id):
        row = session.get(DonationOfferRow, offer_id)
        if row is None:
            raise DonationError("NOT_FOUND", "Donation offer not found", 404)
        return row

    @staticmethod
    def _reservations(session, offer_id):
        return session.scalars(select(DonationReservationRow).where(
            DonationReservationRow.offer_id == offer_id).order_by(DonationReservationRow.reservation_id)).all()

    def _offer(self, session, row, now):
        data = _data(row)
        reservations = self._reservations(session, row.offer_id)
        reserved = sum(r.quantity for r in reservations if r.status == "reserved")
        collected = sum(r.quantity for r in reservations if r.status == "collected")
        status = (DonationStatus.CANCELLED if row.cancelled else
                  DonationStatus.EXPIRED if now >= data.expires_at else
                  DonationStatus.SOLD_OUT if reserved + collected >= data.total_quantity else
                  DonationStatus.ACTIVE)
        return DonationOffer(**data.model_dump(mode="json"), offer_id=row.offer_id,
            business_id=row.business_id, created_at=row.payload["created_at"], status=status,
            reserved_quantity=reserved if status not in (DonationStatus.EXPIRED, DonationStatus.CANCELLED) else 0,
            collected_quantity=collected,
            available_quantity=max(0, data.total_quantity - reserved - collected) if status == DonationStatus.ACTIVE else 0)

    @staticmethod
    def _reservation(row, offer, now):
        status = row.status
        if status == "reserved":
            if offer.cancelled:
                status = "cancelled"
            elif now >= _data(offer).expires_at:
                status = "expired"
        return DonationReservation.model_validate({**row.payload, "status": status})

    def create_offer(self, business_id, request: DonationCreateRequest) -> DonationOffer:
        _require(business_id, "business")
        data = DonationCreateRequest.model_validate(request.model_dump(mode="json"))
        with Session(self.engine) as session, session.begin():
            lock_marketplace(session)
            now = self.clock()
            if data.expires_at <= now:
                raise DonationError("OFFER_EXPIRED", "Expiry must be in the future")
            row = DonationOfferRow(offer_id=uuid4().hex, business_id=business_id, cancelled=0,
                payload={**data.model_dump(mode="json"), "created_at": now.isoformat()})
            session.add(row)
            session.flush()
            return self._offer(session, row, now)

    def list_offers(self, user_id, mine=False) -> DonationListResponse:
        demo_role(user_id)
        if mine:
            _require(user_id, "business")
        with Session(self.engine) as session:
            query = select(DonationOfferRow).order_by(DonationOfferRow.offer_id)
            if mine:
                query = query.where(DonationOfferRow.business_id == user_id)
            now = self.clock()
            offers = [self._offer(session, row, now) for row in session.scalars(query)]
            return DonationListResponse(offers=offers if mine else [o for o in offers if o.status == DonationStatus.ACTIVE])

    def get_offer(self, user_id, offer_id) -> DonationOffer:
        demo_role(user_id)
        with Session(self.engine) as session:
            return self._offer(session, self._row(session, offer_id), self.clock())

    def reserve(self, student_id, offer_id, request: ReservationCreateRequest) -> DonationReservation:
        _require(student_id, "student")
        request = ReservationCreateRequest.model_validate(request.model_dump(mode="json"))
        with Session(self.engine) as session, session.begin():
            lock_marketplace(session)
            now = self.clock()  # Read after waiting for the lock, never before.
            offer = self._row(session, offer_id)
            snapshot = self._offer(session, offer, now)
            if snapshot.status == DonationStatus.EXPIRED:
                raise DonationError("OFFER_EXPIRED", "This donation has expired")
            if snapshot.status == DonationStatus.CANCELLED:
                raise DonationError("INVALID_STATE", "This donation was cancelled")
            consumed = sum(r.quantity for r in self._reservations(session, offer_id)
                if r.student_id == student_id and r.status in ("reserved", "collected"))
            if consumed + request.quantity > snapshot.per_person_limit:
                raise DonationError("PERSON_LIMIT_EXCEEDED", "Per-student limit exceeded")
            if request.quantity > snapshot.available_quantity:
                raise DonationError("INSUFFICIENT_STOCK", "Not enough donation portions available")
            reservation = DonationReservation(reservation_id=uuid4().hex, offer_id=offer_id,
                student_id=student_id, quantity=request.quantity, status=ReservationStatus.RESERVED,
                expires_at=snapshot.expires_at, created_at=now)
            session.add(DonationReservationRow(reservation_id=reservation.reservation_id,
                offer_id=offer_id, student_id=student_id, quantity=request.quantity,
                status=reservation.status.value, payload=reservation.model_dump(mode="json")))
            return reservation

    def list_reservations(self, user_id, offer_id=None) -> ReservationListResponse:
        with Session(self.engine) as session:
            query = select(DonationReservationRow).order_by(DonationReservationRow.reservation_id)
            if offer_id is None:
                _require(user_id, "student")
                query = query.where(DonationReservationRow.student_id == user_id)
            else:
                _require(user_id, "business")
                offer = self._row(session, offer_id)
                if offer.business_id != user_id:
                    raise DonationError("FORBIDDEN", "Only offer owner may see reservations", 403)
                query = query.where(DonationReservationRow.offer_id == offer_id)
            now = self.clock()
            return ReservationListResponse(reservations=[self._reservation(row,
                self._row(session, row.offer_id), now) for row in session.scalars(query)])

    def _reservation_action(self, user_id, reservation_id, collect):
        _require(user_id, "business" if collect else "student")
        with Session(self.engine) as session, session.begin():
            lock_marketplace(session)
            now = self.clock()
            row = session.get(DonationReservationRow, reservation_id)
            if row is None:
                raise DonationError("NOT_FOUND", "Reservation not found", 404)
            offer = self._row(session, row.offer_id)
            if (offer.business_id if collect else row.student_id) != user_id:
                raise DonationError("FORBIDDEN", "This reservation belongs to another user", 403)
            target = "collected" if collect else "cancelled"
            if row.status == target:
                return self._reservation(row, offer, now)
            snapshot = self._offer(session, offer, now)
            if snapshot.status == DonationStatus.EXPIRED:
                raise DonationError("OFFER_EXPIRED", "This donation has expired")
            if offer.cancelled or row.status != "reserved":
                raise DonationError("INVALID_STATE", "Reservation is no longer active")
            if collect and snapshot.pickup_starts_at and now < snapshot.pickup_starts_at:
                raise DonationError("PICKUP_NOT_STARTED", "Pickup window has not started")
            row.status = target
            row.payload = {**row.payload, "status": target,
                "collected_at" if collect else "cancelled_at": now.isoformat()}
            session.flush()
            return self._reservation(row, offer, now)

    def cancel_reservation(self, student_id, reservation_id) -> DonationReservation:
        return self._reservation_action(student_id, reservation_id, False)

    def collect_reservation(self, business_id, reservation_id) -> DonationReservation:
        return self._reservation_action(business_id, reservation_id, True)

    def cancel_offer(self, business_id, offer_id) -> DonationOffer:
        _require(business_id, "business")
        with Session(self.engine) as session, session.begin():
            lock_marketplace(session)
            now = self.clock()
            offer = self._row(session, offer_id)
            if offer.business_id != business_id:
                raise DonationError("FORBIDDEN", "Only offer owner may cancel it", 403)
            offer.cancelled = 1
            for reservation in self._reservations(session, offer_id):
                if reservation.status == "reserved":
                    reservation.status = "cancelled"
                    reservation.payload = {**reservation.payload, "status": "cancelled", "cancelled_at": now.isoformat()}
            session.flush()
            return self._offer(session, offer, now)
