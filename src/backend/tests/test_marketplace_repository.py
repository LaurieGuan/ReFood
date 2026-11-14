import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from database.catalog import SQLRepository
from database.marketplace import MarketplaceRepository, MarketplaceError
from database.orm_models import Base, ExchangeReservationRow
from schemas.marketplace import OfferCreateRequest, ProposalCreateRequest
from schemas.pantry import PantryUpdateRequest


def item(key, amount):
    return {"ingredient_id": "ing_" + key, "name": key,
            "quantity": {"amount": amount, "unit": "piece"}}


class MarketplaceTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.engine = create_engine('sqlite:///' + str(Path(self.temp.name) / 'trade.db'),
                                    connect_args={'timeout': 10})
        Base.metadata.create_all(self.engine)
        self.pantry = SQLRepository(self.engine)
        self.trade = MarketplaceRepository(self.engine)
        self.seed('alice', 'tomato', 6)
        self.seed('bob', 'egg', 4)
        self.a = self.offer('alice', 'tomato', 6)
        self.b = self.offer('bob', 'egg', 4)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def seed(self, user, key, amount):
        return self.pantry.replace_pantry(user, PantryUpdateRequest.model_validate(
            {'items': [item(key, amount)]}))

    def offer(self, user, key, amount):
        return self.trade.create_offer(user, OfferCreateRequest.model_validate(
            {'item': item(key, amount), 'meeting_area': 'Centre'}))

    def proposal(self, target=None, offered=None, user='bob'):
        return self.trade.create_proposal(user, ProposalCreateRequest.model_validate({
            'target_offer_id': (target or self.a).offer_id,
            'proposer_offer_id': (offered or self.b).offer_id,
            'target_quantity': {'amount': 3, 'unit': 'piece'},
            'proposer_quantity': {'amount': 4, 'unit': 'piece'}}))

    def amounts(self, user):
        result = {}
        for lot in self.pantry.get_pantry(user).items:
            result[lot.ingredient_id] = result.get(lot.ingredient_id, 0) + lot.quantity.amount
        return result

    def test_full_exchange_and_repeat_confirmation(self):
        p = self.proposal()
        self.assertEqual(self.amounts('alice'), {'ing_tomato': 6})
        self.trade.accept_proposal('alice', p.proposal_id)
        self.trade.accept_proposal('alice', p.proposal_id)
        with Session(self.engine) as s:
            self.assertEqual(s.scalar(select(func.count()).select_from(ExchangeReservationRow)), 2)
        self.trade.confirm_proposal('bob', p.proposal_id)
        self.trade.confirm_proposal('bob', p.proposal_id)
        self.assertEqual(self.amounts('alice'), {'ing_tomato': 6})
        self.assertEqual(self.trade.confirm_proposal('alice', p.proposal_id).status, 'completed')
        self.trade.confirm_proposal('alice', p.proposal_id)
        self.assertEqual(self.amounts('alice'), {'ing_tomato': 3, 'ing_egg': 4})
        self.assertEqual(self.amounts('bob'), {'ing_tomato': 3, 'ing_egg': 0})
        self.engine.dispose()
        self.assertEqual(len(MarketplaceRepository(self.engine).list_offers('closed').offers), 2)

    def test_cancel_releases_and_reopens(self):
        p = self.proposal()
        self.trade.accept_proposal('alice', p.proposal_id)
        self.trade.confirm_proposal('alice', p.proposal_id)
        self.trade.cancel_proposal('bob', p.proposal_id)
        self.trade.cancel_proposal('bob', p.proposal_id)
        self.assertEqual(len(self.trade.list_offers().offers), 2)
        self.seed('alice', 'tomato', 1)
        self.assertEqual(self.amounts('alice'), {'ing_tomato': 1})

    def test_reserved_stock_blocks_pantry_replacement(self):
        p = self.proposal()
        self.trade.accept_proposal('alice', p.proposal_id)
        for quantity in (0, 2):
            with self.assertRaises(MarketplaceError):
                self.seed('alice', 'tomato', quantity)
        self.seed('alice', 'tomato', 3)
        self.assertEqual(self.amounts('alice'), {'ing_tomato': 3})

    def test_permissions_and_unknown_ids(self):
        p = self.proposal()
        for action, user in ((self.trade.accept_proposal, 'bob'),
                             (self.trade.confirm_proposal, 'eve'),
                             (self.trade.cancel_proposal, 'eve')):
            with self.assertRaises(MarketplaceError) as ctx:
                action(user, p.proposal_id)
            self.assertEqual(ctx.exception.status, 403)
        with self.assertRaises(MarketplaceError) as ctx:
            self.trade.cancel_proposal('alice', 'unknown')
        self.assertEqual(ctx.exception.status, 404)
        with self.assertRaises(MarketplaceError):
            self.trade.close_offer('bob', self.a.offer_id)
        self.assertEqual(self.trade.list_proposals('eve').proposals, [])

    def test_reject_and_invalid_transitions(self):
        p = self.proposal()
        with self.assertRaises(MarketplaceError):
            self.trade.confirm_proposal('alice', p.proposal_id)
        self.trade.reject_proposal('alice', p.proposal_id)
        with self.assertRaises(MarketplaceError):
            self.trade.accept_proposal('alice', p.proposal_id)

    def test_stale_offer_rechecks_stock(self):
        p = self.proposal()
        self.seed('alice', 'tomato', 2)
        with self.assertRaises(MarketplaceError) as ctx:
            self.trade.accept_proposal('alice', p.proposal_id)
        self.assertEqual(ctx.exception.code, 'INSUFFICIENT_STOCK')
        self.assertEqual(len(self.trade.list_offers().offers), 2)

    def test_self_exchange_wrong_unit_and_excessive_quantity(self):
        with self.assertRaises(MarketplaceError):
            self.proposal(user='alice')
        for quantity in ({'amount': 7, 'unit': 'piece'}, {'amount': 1, 'unit': 'kg'}):
            with self.subTest(quantity=quantity), self.assertRaises(MarketplaceError):
                self.trade.create_proposal('bob', ProposalCreateRequest.model_validate({
                    'target_offer_id': self.a.offer_id, 'proposer_offer_id': self.b.offer_id,
                    'target_quantity': quantity, 'proposer_quantity': {'amount': 4, 'unit': 'piece'}}))

    def test_concurrent_pantry_update_and_acceptance(self):
        p = self.proposal()
        def accept():
            try:
                self.trade.accept_proposal('alice', p.proposal_id)
                return 'accepted'
            except MarketplaceError:
                return 'accept_blocked'
        def update():
            try:
                self.seed('alice', 'tomato', 1)
                return 'updated'
            except MarketplaceError:
                return 'update_blocked'
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(accept), pool.submit(update)
            results = (a.result(), b.result())
        self.assertIn(results, [('accepted', 'update_blocked'), ('accept_blocked', 'updated')])

    def test_ambiguous_fraction_cannot_be_traded(self):
        self.pantry.replace_pantry('alice', PantryUpdateRequest.model_validate({
            'items': [{**item('tomato', 6), 'remaining_fraction': .5}]}))
        with self.assertRaises(MarketplaceError):
            self.offer('alice', 'tomato', 1)

    def test_rollback_after_transfer_failure(self):
        p = self.proposal()
        self.trade.accept_proposal('alice', p.proposal_id)
        self.trade.confirm_proposal('bob', p.proposal_id)
        save = self.trade._save_proposal
        def fail(session, proposal):
            save(session, proposal)
            raise RuntimeError('failure after writes')
        with patch.object(self.trade, '_save_proposal', side_effect=fail):
            with self.assertRaises(RuntimeError):
                self.trade.confirm_proposal('alice', p.proposal_id)
        self.assertEqual(self.amounts('alice'), {'ing_tomato': 6})
        self.assertEqual(self.trade.list_proposals('alice').proposals[0].confirmed_by, ['bob'])
        self.trade.confirm_proposal('alice', p.proposal_id)
        self.assertEqual(self.amounts('alice')['ing_egg'], 4)

    def test_competing_proposals_and_close(self):
        first, second = self.proposal(), self.proposal()
        self.trade.accept_proposal('alice', first.proposal_id)
        states = {p.proposal_id: p.status for p in self.trade.list_proposals('alice').proposals}
        self.assertEqual(states[second.proposal_id], 'rejected')
        with self.assertRaises(MarketplaceError):
            self.trade.close_offer('alice', self.a.offer_id)
        self.trade.cancel_proposal('alice', first.proposal_id)
        third = self.proposal()
        self.trade.close_offer('alice', self.a.offer_id)
        states = {p.proposal_id: p.status for p in self.trade.list_proposals('alice').proposals}
        self.assertEqual(states[third.proposal_id], 'rejected')

    def test_concurrent_reservations_cannot_overbook_different_offers(self):
        # Different offers, same pantry stock: offer status alone cannot protect it.
        self.seed('alice', 'tomato', 3)
        second_offer = self.offer('alice', 'tomato', 3)
        self.seed('charlie', 'egg', 4)
        third_offer = self.offer('charlie', 'egg', 4)
        proposals = [self.proposal(), self.proposal(second_offer, third_offer, 'charlie')]
        def accept(p):
            try:
                self.trade.accept_proposal('alice', p.proposal_id)
                return 'accepted'
            except MarketplaceError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(accept, proposals))
        self.assertEqual(sorted(results), ['INSUFFICIENT_STOCK', 'accepted'])


@skipUnless(os.environ.get('TEST_DATABASE_URL'), 'Dedicated MariaDB test database not configured')
class MariaDBMarketplaceTests(MarketplaceTests):
    """Real MariaDB scenarios, each in its own randomly named database.

    TEST_DATABASE_URL supplies a test account with CREATE/DROP DATABASE rights.
    Only a generated refood_trade_test_<uuid> database is created and removed.
    """
    def setUp(self):
        # Separate random database per suite instance requires CREATE DATABASE rights.
        from sqlalchemy.engine import make_url
        from sqlalchemy import text
        url = make_url(os.environ['TEST_DATABASE_URL'])
        self.admin_engine = create_engine(url)
        self.database_name = 'refood_trade_test_' + uuid4().hex
        with self.admin_engine.begin() as conn:
            conn.execute(text('CREATE DATABASE `' + self.database_name + '`'))
        self.engine = create_engine(url.set(database=self.database_name))
        Base.metadata.create_all(self.engine)
        self.pantry, self.trade = SQLRepository(self.engine), MarketplaceRepository(self.engine)
        self.seed('alice', 'tomato', 6)
        self.seed('bob', 'egg', 4)
        self.a, self.b = self.offer('alice', 'tomato', 6), self.offer('bob', 'egg', 4)

    def tearDown(self):
        from sqlalchemy import text
        self.engine.dispose()
        with self.admin_engine.begin() as conn:
            conn.execute(text('DROP DATABASE `' + self.database_name + '`'))
        self.admin_engine.dispose()
