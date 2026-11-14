from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import create_app
from database.engine import get_engine
from database.orm_models import Base, TradeNotificationRow
from services.trade_notification_demo import process_demo_notifications


def item(name):
    return {'ingredient_id': 'ing_' + name, 'name': name, 'quantity': {'amount': 3, 'unit': 'piece'}}


class NotificationFlowTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.url = 'sqlite:///' + str(Path(self.temp.name) / 'mail.db')
        self.engine = get_engine(self.url)
        Base.metadata.create_all(self.engine)
        self.client = create_app({'TESTING': True, 'DATABASE_URL': self.url}).test_client()
        ids = []
        for user, food in [('alice', 'tomato'), ('bob', 'egg')]:
            header = {'X-Demo-User-Id': user}
            self.assertEqual(self.client.put('/api/v1/pantry', headers=header, json={'items': [item(food)]}).status_code, 200)
            r = self.client.post('/api/v1/marketplace/offers', headers=header, json={'item': item(food), 'meeting_area': 'Campus'})
            self.assertEqual(r.status_code, 201); ids.append(r.get_json()['offer_id'])
        r = self.client.post('/api/v1/marketplace/proposals', headers={'X-Demo-User-Id': 'bob'}, json={
            'target_offer_id': ids[0], 'proposer_offer_id': ids[1],
            'target_quantity': {'amount': 1, 'unit': 'piece'}, 'proposer_quantity': {'amount': 1, 'unit': 'piece'}})
        self.assertEqual(r.status_code, 201)
        self.path = '/api/v1/marketplace/proposals/' + r.get_json()['proposal_id'] + '/accept'

    def tearDown(self):
        self.engine.dispose(); self.temp.cleanup()

    def rows(self):
        with Session(self.engine) as session:
            return [(x.recipient_id, x.status, x.attempts) for x in session.scalars(select(TradeNotificationRow))]

    def test_authorization_and_repeat_do_not_duplicate(self):
        self.assertEqual(self.client.post(self.path, headers={'X-Demo-User-Id': 'bob'}).status_code, 403)
        self.assertEqual(self.rows(), [])
        for _ in range(2):
            self.assertEqual(self.client.post(self.path, headers={'X-Demo-User-Id': 'alice'}).status_code, 200)
        self.assertEqual(len(self.rows()), 2)
        messages = []
        self.assertEqual(process_demo_notifications(self.engine, messages.append), {'previewed': 2, 'failed': 0})
        self.assertEqual({str(m['To']) for m in messages}, {'alice@example.org', 'bob@example.org'})
        self.assertEqual({str(m['Reply-To']) for m in messages}, {'alice@example.org', 'bob@example.org'})
        self.assertEqual(process_demo_notifications(self.engine, messages.append), {'previewed': 0, 'failed': 0})
        self.assertEqual(len(messages), 2)

    def test_failed_delivery_does_not_undo_acceptance_and_can_retry(self):
        self.assertEqual(self.client.post(self.path, headers={'X-Demo-User-Id': 'alice'}).status_code, 200)
        def fail(_message):
            raise OSError('simulated transport failure')
        self.assertEqual(process_demo_notifications(self.engine, fail), {'previewed': 0, 'failed': 2})
        self.assertEqual({row[1] for row in self.rows()}, {'failed'})
        proposal = self.client.get('/api/v1/marketplace/proposals', headers={'X-Demo-User-Id': 'alice'}).get_json()['proposals'][0]
        self.assertEqual(proposal['status'], 'accepted')
        self.assertEqual(process_demo_notifications(self.engine, lambda message: None), {'previewed': 2, 'failed': 0})
        self.assertTrue(all(status == 'previewed' and attempts == 2 for _, status, attempts in self.rows()))
