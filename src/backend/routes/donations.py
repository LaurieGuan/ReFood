"""Donation HTTP API. Demo roles are enforced in the repository."""
from flask import Blueprint, current_app, request
from werkzeug.exceptions import BadRequest, ServiceUnavailable

from schemas.donations import (DonationCreateRequest, DonationOffer, DonationListResponse,
    ReservationCreateRequest, DonationReservation, ReservationListResponse)
from .demo_identity import demo_user_id
from .http_utils import json_response, validate_request

donations_bp = Blueprint("donations", __name__)


def repository():
    url = current_app.config.get("DATABASE_URL")
    if not url:
        raise ServiceUnavailable("Donations require DATABASE_URL and initialized tables")
    from database.engine import get_engine
    from database.donations import DonationRepository
    return DonationRepository(get_engine(url))


@donations_bp.post("/offers")
def create_offer():
    user = demo_user_id()
    payload = validate_request(DonationCreateRequest)
    return json_response(DonationOffer, repository().create_offer(user, payload), 201)


@donations_bp.get("/offers")
def list_offers():
    mine = request.args.get("mine", "false")
    if mine not in {"true", "false"}:
        raise BadRequest("mine must be true or false")
    return json_response(DonationListResponse, repository().list_offers(demo_user_id(), mine == "true"))


@donations_bp.get("/offers/<offer_id>")
def get_offer(offer_id):
    return json_response(DonationOffer, repository().get_offer(demo_user_id(), offer_id))


@donations_bp.post("/offers/<offer_id>/cancel")
def cancel_offer(offer_id):
    return json_response(DonationOffer, repository().cancel_offer(demo_user_id(), offer_id))


@donations_bp.post("/offers/<offer_id>/reservations")
def reserve(offer_id):
    user = demo_user_id()
    payload = validate_request(ReservationCreateRequest)
    return json_response(DonationReservation, repository().reserve(user, offer_id, payload), 201)


@donations_bp.get("/offers/<offer_id>/reservations")
def offer_reservations(offer_id):
    return json_response(ReservationListResponse, repository().list_reservations(demo_user_id(), offer_id))


@donations_bp.get("/reservations")
def my_reservations():
    return json_response(ReservationListResponse, repository().list_reservations(demo_user_id()))


@donations_bp.post("/reservations/<reservation_id>/cancel")
def cancel_reservation(reservation_id):
    return json_response(DonationReservation, repository().cancel_reservation(demo_user_id(), reservation_id))


@donations_bp.post("/reservations/<reservation_id>/collect")
def collect_reservation(reservation_id):
    return json_response(DonationReservation, repository().collect_reservation(demo_user_id(), reservation_id))
