from datetime import datetime, timezone
from unittest import TestCase
from schemas.marketplace import ExchangeProposal
from services.trade_email import build_trade_confirmation


def proposal(status='accepted'):
    now = datetime.now(timezone.utc)
    def item(name):
        return {'ingredient_id': 'ing_' + name, 'name': name, 'quantity': {'amount': 1, 'unit': 'piece'}}
    return ExchangeProposal.model_validate({'proposal_id':'p1', 'target_owner_id':'alice',
        'proposer_id':'bob', 'target_offer_id':'a', 'proposer_offer_id':'b',
        'target_item':item('tomato'), 'proposer_item':item('egg'), 'status':status,
        'created_at':now, 'updated_at':now})


class TradeEmailTests(TestCase):
    def test_messages_are_individually_addressed(self):
        for user, recipient, partner in [('alice', 'alice@example.org', 'bob@example.org'), ('bob', 'bob@example.org', 'alice@example.org')]:
            message = build_trade_confirmation(proposal(), user, recipient, partner, 'refood@example.org')
            self.assertEqual(message['To'], recipient)
            self.assertEqual(message['Reply-To'], partner)
            self.assertIn(partner, message.get_content())
            self.assertIn('egg', message.get_content())

    def test_requires_acceptance_participation_and_single_addresses(self):
        for candidate, user, address in [(proposal('pending'), 'alice', 'alice@example.org'),
                                         (proposal(), 'outsider', 'alice@example.org'),
                                         (proposal(), 'alice', 'alice@example.org, other@example.org')]:
            with self.subTest(user=user, address=address), self.assertRaises(ValueError):
                build_trade_confirmation(candidate, user, address, 'bob@example.org', 'refood@example.org')
