import unittest
from copy import deepcopy

from pydantic import ValidationError

from schemas.ingredients import IngredientWithQuantity
from schemas.marketplace import (
    ExchangeOffer, ExchangeProposal, OfferCreateRequest, OfferListResponse,
    ProposalCreateRequest, ProposalListResponse,
)


TOMATO = {"ingredient_id": "ing_tomato", "name": "tomato",
          "quantity": {"amount": 6, "unit": "piece"}}
EGG = {"ingredient_id": "ing_egg", "name": "egg",
       "quantity": {"amount": 4, "unit": "piece"}}
DATE = "2026-11-14T12:00:00Z"


class MarketplaceSchemaTests(unittest.TestCase):
    def proposal(self, **overrides):
        return {"proposal_id": "p1", "target_owner_id": "alice", "proposer_id": "bob",
                "target_offer_id": "o1", "proposer_offer_id": "o2",
                "target_item": TOMATO, "proposer_item": EGG,
                "status": "pending", "created_at": DATE, "updated_at": DATE, **overrides}

    def test_offer_reuses_shared_ingredient_and_serializes(self):
        request = OfferCreateRequest.model_validate({"item": TOMATO, "meeting_area": " Montréal "})
        self.assertIsInstance(request.item, IngredientWithQuantity)
        offer = ExchangeOffer.model_validate({**request.model_dump(mode="json"),
            "offer_id": "o1", "owner_id": "alice", "status": "open", "created_at": DATE})
        data = OfferListResponse(offers=[offer]).model_dump(mode="json")
        self.assertEqual(data["offers"][0]["item"]["quantity"]["unit"], "piece")
        self.assertEqual(data["offers"][0]["meeting_area"], "Montréal")
        self.assertEqual(data["offers"][0]["status"], "open")

    def test_unknown_zero_negative_and_nonfinite_trade_amounts_rejected(self):
        for amount in (None, 0, -1, float("nan"), float("inf")):
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                OfferCreateRequest.model_validate({"item": {**TOMATO,
                    "quantity": {"amount": amount, "unit": "piece"}}, "meeting_area": "Centre"})
        with self.assertRaises(ValidationError):
            OfferCreateRequest.model_validate({"item": {**TOMATO, "quantity": {"amount": 1}},
                                               "meeting_area": "Centre"})

    def test_existing_pantry_recipe_quantity_contract_is_unchanged(self):
        item = IngredientWithQuantity.model_validate({"ingredient_id": "ing_tomato", "name": "tomato"})
        self.assertIsNone(item.quantity.amount)

    def test_request_cannot_supply_server_owned_identity_or_status(self):
        for field in ("owner_id", "offer_id", "status", "created_at"):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                OfferCreateRequest.model_validate({"item": TOMATO, "meeting_area": "Centre", field: "x"})

    def test_empty_fields_rejected(self):
        for changes in ({"meeting_area": " "}, {"item": {**TOMATO, "ingredient_id": " "}},
                        {"item": {**TOMATO, "name": " "}}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                OfferCreateRequest.model_validate({"item": TOMATO, "meeting_area": "Centre", **changes})

    def test_proposal_creation_and_invalid_quantities(self):
        data = {"target_offer_id": "o1", "proposer_offer_id": "o2",
                "target_quantity": {"amount": 3, "unit": "piece"},
                "proposer_quantity": {"amount": 4, "unit": "piece"}}
        self.assertEqual(ProposalCreateRequest.model_validate(data).target_quantity.amount, 3)
        for changes in ({"proposer_offer_id": "o1"}, {"target_quantity": {}}, {"proposer_id": "bob"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                ProposalCreateRequest.model_validate({**data, **changes})

    def test_completed_snapshot_requires_both_confirmations(self):
        proposal = ExchangeProposal.model_validate(self.proposal(status="completed", confirmed_by=["alice", "bob"]))
        payload = ProposalListResponse(proposals=[proposal]).model_dump(mode="json")
        self.assertEqual(payload["proposals"][0]["status"], "completed")
        for confirmations in ([], ["alice"], ["alice", "alice"], ["alice", "outsider"]):
            with self.subTest(confirmations=confirmations), self.assertRaises(ValidationError):
                ExchangeProposal.model_validate(self.proposal(status="completed", confirmed_by=confirmations))

    def test_invalid_snapshot_identity_state_and_dates(self):
        for changes in ({"proposer_id": "alice"}, {"target_offer_id": "o2"},
                        {"status": "invalid"}, {"created_at": "2026-11-14T12:00:00"},
                        {"updated_at": "2026-11-13T12:00:00Z"},
                        {"confirmed_by": ["alice"]},
                        {"status": "accepted", "confirmed_by": ["alice", "bob"]}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                ExchangeProposal.model_validate(self.proposal(**changes))

    def test_utc_normalization_and_no_mutation(self):
        data = deepcopy(self.proposal(created_at="2026-11-14T07:00:00-05:00"))
        before = deepcopy(data)
        result = ExchangeProposal.model_validate(data)
        self.assertEqual(result.model_dump(mode="json")["created_at"], DATE)
        self.assertEqual(data, before)

    def test_empty_response_lists_are_independent(self):
        first, second = OfferListResponse(), OfferListResponse()
        first.offers.append("sentinel")
        self.assertEqual(second.offers, [])
        self.assertEqual(ProposalListResponse().proposals, [])
