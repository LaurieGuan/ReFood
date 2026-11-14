import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest import TestCase, skipUnless
from unittest.mock import patch
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app import create_app
from database.donations import DonationRepository
from database.engine import get_engine
from database.orm_models import Base
from schemas.donations import DonationCreateRequest
from routes.donations import repository as configured_repository


class DonationTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.url = 'sqlite:///' + str(Path(self.temp.name) / 'donations.db')
        self.engine = get_engine(self.url)
        self.initialize()

    def initialize(self):
        Base.metadata.create_all(self.engine)
        self.now = datetime(2026, 11, 14, 18, tzinfo=timezone.utc)
        self.repository = DonationRepository(self.engine, clock=lambda: self.now)
        self.app = create_app({'TESTING': True, 'DATABASE_URL': self.url})
        self.client = self.app.test_client()
        self.factory = patch('routes.donations.repository', return_value=self.repository)
        self.factory.start()

    def tearDown(self):
        self.factory.stop()
        self.engine.dispose()
        self.temp.cleanup()

    def call(self, method, path, user='alice', data=None, client=None):
        kwargs = {'headers': {'X-Demo-User-Id': user}}
        if data is not None:
            kwargs['json'] = data
        return getattr(client or self.client, method)('/api/v1/donations' + path, **kwargs)

    def payload(self, **overrides):
        return {'title': 'Pains du jour', 'description': 'Sacs de deux pains',
            'unit_label': 'sac', 'pickup_location': 'Comptoir du magasin',
            'total_quantity': 5, 'per_person_limit': 2,
            'expires_at': (self.now + timedelta(hours=1)).isoformat(), **overrides}

    def offer(self, **overrides):
        response = self.call('post', '/offers', 'shop_demo', self.payload(**overrides))
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()['offer_id']

    def reserve(self, offer, user='alice', quantity=1, client=None):
        return self.call('post', '/offers/' + offer + '/reservations', user,
                         {'quantity': quantity}, client)

    def test_full_http_lifecycle_and_cumulative_limit(self):
        offer = self.offer()
        response = self.reserve(offer, quantity=2)
        self.assertEqual(response.status_code, 201)
        reservation = response.get_json()['reservation_id']
        self.assertEqual(self.call('get', '/offers/' + offer).get_json()['available_quantity'], 3)
        self.assertEqual(self.reserve(offer).get_json()['error']['code'], 'PERSON_LIMIT_EXCEEDED')
        collect = '/reservations/' + reservation + '/collect'
        self.assertEqual(self.call('post', collect, 'shop_demo').get_json()['status'], 'collected')
        self.assertEqual(self.call('post', collect, 'shop_demo').status_code, 200)
        self.assertEqual(self.reserve(offer).status_code, 409)
        self.assertEqual(self.call('post', '/reservations/' + reservation + '/cancel').status_code, 409)
        self.assertEqual(self.reserve(offer, 'bob', 2).status_code, 201)
        snapshot = self.call('get', '/offers/' + offer).get_json()
        self.assertEqual((snapshot['available_quantity'], snapshot['collected_quantity']), (1, 2))

    def test_cancel_releases_stock_and_person_limit(self):
        offer = self.offer()
        reservation = self.reserve(offer, quantity=2).get_json()['reservation_id']
        path = '/reservations/' + reservation + '/cancel'
        self.assertEqual(self.call('post', path).status_code, 200)
        self.assertEqual(self.call('post', path).status_code, 200)
        self.assertEqual(self.call('get', '/offers/' + offer).get_json()['available_quantity'], 5)
        self.assertEqual(self.reserve(offer, quantity=2).status_code, 201)

    def test_exact_expiry_blocks_reserve_and_pickup_without_scheduler(self):
        offer = self.offer()
        reservation = self.reserve(offer).get_json()['reservation_id']
        self.now += timedelta(hours=1)
        self.assertEqual(self.call('get', '/offers').get_json(), {'offers': []})
        data = self.call('get', '/offers/' + offer).get_json()
        self.assertEqual((data['status'], data['available_quantity']), ('expired', 0))
        for response in (self.reserve(offer, 'bob'), self.call('post',
                '/reservations/' + reservation + '/collect', 'shop_demo')):
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.get_json()['error']['code'], 'OFFER_EXPIRED')
        self.assertEqual(self.call('get', '/reservations').get_json()['reservations'][0]['status'], 'expired')
        self.assertEqual(self.call('get', '/offers?mine=true', 'shop_demo').get_json()['offers'][0]['status'], 'expired')

    def test_expiry_is_checked_after_lock_wait(self):
        offer = self.offer()
        from database.marketplace import lock_marketplace
        def cross_deadline(session):
            lock_marketplace(session)
            self.now += timedelta(hours=1)
        with patch('database.donations.lock_marketplace', side_effect=cross_deadline):
            self.assertEqual(self.reserve(offer).get_json()['error']['code'], 'OFFER_EXPIRED')

    def test_role_permissions_privacy_and_server_owned_fields(self):
        self.assertEqual(self.call('post', '/offers', data=self.payload()).status_code, 403)
        offer = self.offer()
        self.assertEqual(self.reserve(offer, 'shop_demo').status_code, 403)
        reservation = self.reserve(offer).get_json()['reservation_id']
        self.assertEqual(self.call('post', '/reservations/' + reservation + '/collect').status_code, 403)
        self.assertEqual(self.call('post', '/reservations/' + reservation + '/cancel', 'bob').status_code, 403)
        self.assertEqual(self.call('get', '/reservations', 'bob').get_json(), {'reservations': []})
        self.assertEqual(self.call('get', '/offers/' + offer + '/reservations').status_code, 403)
        self.assertEqual(self.call('get', '/offers/' + offer + '/reservations', 'shop_demo').status_code, 200)
        self.assertEqual(self.call('post', '/offers', 'shop_demo', self.payload(business_id='alice')).status_code, 422)

    def test_pickup_window_and_sold_out_offer(self):
        offer = self.offer(total_quantity=2, per_person_limit=2,
                           pickup_starts_at=(self.now + timedelta(minutes=10)).isoformat())
        reservation = self.reserve(offer, quantity=2).get_json()['reservation_id']
        path = '/reservations/' + reservation + '/collect'
        self.assertEqual(self.call('get', '/offers').get_json(), {'offers': []})
        self.assertEqual(self.call('get', '/offers/' + offer).get_json()['status'], 'sold_out')
        self.assertEqual(self.call('post', path, 'shop_demo').get_json()['error']['code'], 'PICKUP_NOT_STARTED')
        self.now += timedelta(minutes=10)
        self.assertEqual(self.call('post', path, 'shop_demo').status_code, 200)

    def test_offer_cancellation_invalidates_only_uncollected_reservations(self):
        offer = self.offer()
        a = self.reserve(offer).get_json()['reservation_id']
        b = self.reserve(offer, 'bob').get_json()['reservation_id']
        self.call('post', '/reservations/' + a + '/collect', 'shop_demo')
        self.assertEqual(self.call('post', '/offers/' + offer + '/cancel', 'shop_demo').status_code, 200)
        self.assertEqual(self.call('get', '/reservations', 'bob').get_json()['reservations'][0]['status'], 'cancelled')
        self.assertEqual(self.call('get', '/reservations').get_json()['reservations'][0]['status'], 'collected')
        self.assertEqual(self.call('post', '/reservations/' + b + '/collect', 'shop_demo').status_code, 409)

    def test_concurrent_students_cannot_overbook(self):
        offer = self.offer(total_quantity=1, per_person_limit=1)
        barrier = Barrier(2)
        def reserve(user):
            with self.app.test_client() as client:
                barrier.wait(timeout=10)
                return self.reserve(offer, user, client=client).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(reserve, ['alice', 'bob']))
        self.assertEqual(sorted(outcomes), [201, 409])

    def test_concurrent_same_student_cannot_bypass_limit(self):
        offer = self.offer(per_person_limit=1)
        barrier = Barrier(2)
        def reserve(_):
            with self.app.test_client() as client:
                barrier.wait(timeout=10)
                return self.reserve(offer, client=client).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(reserve, [0, 1])), [201, 409])

    def test_validation_dates_and_errors(self):
        for changes in ({'total_quantity': 0}, {'per_person_limit': 6}, {'total_quantity': True},
                        {'total_quantity': 1.5}, {'expires_at': '2026-11-14T19:00:00'},
                        {'title': ' '}, {'pickup_starts_at': (self.now + timedelta(hours=2)).isoformat()}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                DonationCreateRequest.model_validate(self.payload(**changes))
        self.assertEqual(self.call('post', '/offers', 'shop_demo', self.payload(expires_at=self.now.isoformat())).status_code, 409)
        self.assertEqual(self.call('get', '/offers/unknown').status_code, 404)
        self.assertEqual(self.call('get', '/offers?mine=bad').status_code, 400)
        client = create_app({'TESTING': True, 'DATABASE_URL': None}).test_client()
        with patch('routes.donations.repository', side_effect=configured_repository):
            self.assertEqual(client.get('/api/v1/donations/offers').status_code, 503)
        self.assertEqual(client.get('/api/v1/health').status_code, 200)

    def test_cancel_rollback_and_committed_persistence(self):
        offer = self.offer()
        self.reserve(offer)
        with patch.object(self.repository, '_offer', side_effect=RuntimeError('private')):
            self.assertEqual(self.call('post', '/offers/' + offer + '/cancel', 'shop_demo').status_code, 500)
        self.engine.dispose()
        snapshot = DonationRepository(self.engine, clock=lambda: self.now).get_offer('alice', offer)
        self.assertEqual((snapshot.status, snapshot.available_quantity), ('active', 4))

    def test_configured_route_factory_without_repository_patch(self):
        data = self.payload(expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
        with patch('routes.donations.repository', side_effect=configured_repository):
            response = self.call('post', '/offers', 'shop_demo', data)
            self.assertEqual(response.status_code, 201, response.get_json())
            offer_id = response.get_json()['offer_id']
            self.assertEqual(self.reserve(offer_id).status_code, 201)
            self.assertEqual(self.call('get', '/offers/' + offer_id).get_json()['available_quantity'], 4)


@skipUnless(os.environ.get('TEST_DATABASE_URL'), 'Dedicated MariaDB test server not configured')
class MariaDBDonationTests(DonationTests):
    def setUp(self):
        url = make_url(os.environ['TEST_DATABASE_URL'])
        self.admin = create_engine(url)
        self.database = 'refood_donation_test_' + uuid4().hex
        with self.admin.begin() as connection:
            connection.execute(text('CREATE DATABASE `' + self.database + '`'))
        self.url = url.set(database=self.database).render_as_string(hide_password=False)
        self.engine = get_engine(self.url)
        self.initialize()

    def tearDown(self):
        self.factory.stop()
        self.engine.dispose()
        with self.admin.begin() as connection:
            connection.execute(text('DROP DATABASE `' + self.database + '`'))
        self.admin.dispose()
