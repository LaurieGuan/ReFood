import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app import create_app
from database.engine import get_engine
from database.orm_models import Base


def item(key, amount):
    return {"ingredient_id": "ing_" + key, "name": key,
            "quantity": {"amount": amount, "unit": "piece"}}


class MarketplaceRouteTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.url = 'sqlite:///' + str(Path(self.temp.name) / 'http.db')
        self.initialize()

    def initialize(self):
        self.engine = get_engine(self.url)
        Base.metadata.create_all(self.engine)
        self.client = create_app({'TESTING': True, 'DATABASE_URL': self.url}).test_client()
        for user, food, amount in [('alice', 'tomato', 6), ('bob', 'egg', 4)]:
            response = self.call('put', '/pantry', user, {'items': [item(food, amount)]})
            self.assertEqual(response.status_code, 200)
        self.a = self.offer('alice', 'tomato', 6)
        self.b = self.offer('bob', 'egg', 4)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def call(self, method, path, user='alice', data=None):
        kwargs = {'headers': {'X-Demo-User-Id': user}}
        if data is not None:
            kwargs['json'] = data
        return getattr(self.client, method)('/api/v1' + path, **kwargs)

    def offer(self, user, food, amount):
        response = self.call('post', '/marketplace/offers', user,
                             {'item': item(food, amount), 'meeting_area': 'Centre'})
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()['offer_id']

    def proposal(self):
        response = self.call('post', '/marketplace/proposals', 'bob', {
            'target_offer_id': self.a, 'proposer_offer_id': self.b,
            'target_quantity': {'amount': 3, 'unit': 'piece'},
            'proposer_quantity': {'amount': 4, 'unit': 'piece'}})
        self.assertEqual(response.status_code, 201, response.get_json())
        return '/marketplace/proposals/' + response.get_json()['proposal_id']

    def amounts(self, user):
        response = self.call('get', '/pantry', user)
        self.assertEqual(response.status_code, 200)
        return {lot['ingredient_id']: lot['quantity']['amount'] for lot in response.get_json()['items']}

    def test_http_exchange_transfers_once_and_persists(self):
        path = self.proposal()
        self.assertEqual(self.call('post', path + '/accept').status_code, 200)
        self.assertEqual(self.call('post', path + '/confirm', 'bob').get_json()['status'], 'accepted')
        self.assertEqual(self.amounts('alice'), {'ing_tomato': 6})
        self.assertEqual(self.call('post', path + '/confirm').get_json()['status'], 'completed')
        self.assertEqual(self.call('post', path + '/confirm').status_code, 200)
        self.assertEqual(self.amounts('alice'), {'ing_tomato': 3, 'ing_egg': 4})
        self.assertEqual(self.amounts('bob'), {'ing_egg': 0, 'ing_tomato': 3})
        self.engine.dispose()
        self.client = create_app({'TESTING': True, 'DATABASE_URL': self.url}).test_client()
        self.assertEqual(self.amounts('alice')['ing_egg'], 4)
        self.assertEqual(len(self.call('get', '/marketplace/offers?status=closed').get_json()['offers']), 2)

    def test_pantry_conflict_then_cancellation(self):
        path = self.proposal()
        self.call('post', path + '/accept')
        response = self.call('put', '/pantry', 'alice', {'items': []})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()['error']['code'], 'INSUFFICIENT_STOCK')
        self.assertEqual(self.call('post', path + '/cancel', 'bob').status_code, 200)
        self.assertEqual(self.call('put', '/pantry', 'alice', {'items': []}).status_code, 200)

    def test_forbidden_missing_invalid_state(self):
        path = self.proposal()
        self.assertEqual(self.call('post', path + '/accept', 'bob').status_code, 403)
        self.assertEqual(self.call('post', path + '/confirm').status_code, 409)
        response = self.call('post', '/marketplace/proposals/unknown/cancel')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()['error']['code'], 'NOT_FOUND')
        self.assertEqual(self.call('post', '/marketplace/offers/' + self.a + '/close', 'bob').status_code, 403)

    def test_reject_close_and_list_visibility(self):
        path = self.proposal()
        self.assertEqual(self.call('get', '/marketplace/proposals', 'demo_user').get_json(), {'proposals': []})
        self.assertEqual(len(self.call('get', '/marketplace/proposals', 'bob').get_json()['proposals']), 1)
        self.assertEqual(self.call('post', path + '/reject').get_json()['status'], 'rejected')
        self.assertEqual(self.call('post', '/marketplace/offers/' + self.a + '/close').get_json()['status'], 'closed')

    def test_validation_identity_and_malformed_json(self):
        for payload in ({}, {'item': item('tomato', 0), 'meeting_area': 'Centre'},
                        {'item': item('tomato', 1), 'meeting_area': 'Centre', 'owner_id': 'bob'}):
            self.assertEqual(self.call('post', '/marketplace/offers', data=payload).status_code, 422)
        response = self.client.post('/api/v1/marketplace/offers', data='{', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.call('get', '/marketplace/offers?status=nope').status_code, 400)
        self.assertEqual(self.call('get', '/pantry', 'outsider').status_code, 400)
        self.assertEqual(self.call('get', '/marketplace/proposals', 'outsider').status_code, 400)

    def test_unavailable_storage_still_allows_health(self):
        client = create_app({'TESTING': True, 'DATABASE_URL': None}).test_client()
        self.assertEqual(client.get('/api/v1/health').status_code, 200)
        self.assertEqual(client.get('/api/v1/marketplace/offers').status_code, 503)
        with patch('routes.marketplace.repository', side_effect=RuntimeError('private credentials')):
            response = self.call('get', '/marketplace/offers')
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('private credentials', response.get_data(as_text=True))

    def test_default_identity_preserves_existing_pantry_behavior(self):
        self.assertEqual(self.client.get('/api/v1/pantry').get_json(), {'items': []})
        self.assertEqual(self.amounts('alice'), {'ing_tomato': 6})


@skipUnless(os.environ.get('TEST_DATABASE_URL'), 'Dedicated MariaDB test server not configured')
class MariaDBMarketplaceRouteTests(MarketplaceRouteTests):
    def setUp(self):
        url = make_url(os.environ['TEST_DATABASE_URL'])
        self.admin = create_engine(url)
        self.database = 'refood_http_test_' + uuid4().hex
        with self.admin.begin() as connection:
            connection.execute(text('CREATE DATABASE `' + self.database + '`'))
        self.url = url.set(database=self.database).render_as_string(hide_password=False)
        self.initialize()

    def tearDown(self):
        self.engine.dispose()
        with self.admin.begin() as connection:
            connection.execute(text('DROP DATABASE `' + self.database + '`'))
        self.admin.dispose()
