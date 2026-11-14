"""HTTP validation and delegation for confirmed ingredient exchanges."""
from flask import Blueprint, current_app, request
from werkzeug.exceptions import BadRequest, ServiceUnavailable

from schemas.marketplace import (ExchangeOffer, ExchangeProposal, OfferCreateRequest,
    OfferListResponse, OfferStatus, ProposalCreateRequest, ProposalListResponse)
from .demo_identity import demo_user_id
from .http_utils import json_response, validate_request

marketplace_bp = Blueprint("marketplace", __name__)


def repository():
    url = current_app.config.get("DATABASE_URL")
    if not url:
        raise ServiceUnavailable("Marketplace requires DATABASE_URL and initialized tables")
    from database.engine import get_engine
    from database.marketplace import MarketplaceRepository
    return MarketplaceRepository(get_engine(url))


@marketplace_bp.post("/offers")
def create_offer():
    user_id = demo_user_id()
    payload = validate_request(OfferCreateRequest)
    return json_response(ExchangeOffer, repository().create_offer(user_id, payload), 201)


@marketplace_bp.get("/offers")
def list_offers():
    try:
        status = OfferStatus(request.args.get("status", "open"))
    except ValueError as exc:
        raise BadRequest("status must be open, reserved or closed") from exc
    return json_response(OfferListResponse, repository().list_offers(status))


@marketplace_bp.post("/offers/<offer_id>/close")
def close_offer(offer_id):
    return json_response(ExchangeOffer, repository().close_offer(demo_user_id(), offer_id))


@marketplace_bp.post("/proposals")
def create_proposal():
    user_id = demo_user_id()
    payload = validate_request(ProposalCreateRequest)
    return json_response(ExchangeProposal, repository().create_proposal(user_id, payload), 201)


@marketplace_bp.get("/proposals")
def list_proposals():
    return json_response(ProposalListResponse, repository().list_proposals(demo_user_id()))


@marketplace_bp.post("/proposals/<proposal_id>/accept")
def accept_proposal(proposal_id):
    return json_response(ExchangeProposal, repository().accept_proposal(demo_user_id(), proposal_id))


@marketplace_bp.post("/proposals/<proposal_id>/reject")
def reject_proposal(proposal_id):
    return json_response(ExchangeProposal, repository().reject_proposal(demo_user_id(), proposal_id))


@marketplace_bp.post("/proposals/<proposal_id>/cancel")
def cancel_proposal(proposal_id):
    return json_response(ExchangeProposal, repository().cancel_proposal(demo_user_id(), proposal_id))


@marketplace_bp.post("/proposals/<proposal_id>/confirm")
def confirm_proposal(proposal_id):
    return json_response(ExchangeProposal, repository().confirm_proposal(demo_user_id(), proposal_id))
