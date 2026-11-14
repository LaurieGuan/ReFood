import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from app import create_app
from database.engine import get_engine
from database.orm_models import Base


class OfferPhotoTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.url = 'sqlite:///' + str(Path(self.temp.name) / 'offers.db')
        self.engine = get_engine(self.url)
        Base.metadata.create_all(self.engine)
        self.client = create_app({'TESTING': True, 'DATABASE_URL': self.url}).test_client()
        self.headers = {'X-Demo-User-Id': 'alice'}
        self.item = {'ingredient_id': 'ing_egg', 'name': 'egg', 'quantity': {'amount': 2, 'unit': 'piece'}}
        self.assertEqual(self.client.put('/api/v1/pantry', headers=self.headers, json={'items': [self.item]}).status_code, 200)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def test_photo_and_description_survive_publication_and_listing(self):
        photo = 'data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode()
        response = self.client.post('/api/v1/marketplace/offers', headers=self.headers,
            json={'item': self.item, 'meeting_area': 'Campus', 'description': 'Œufs frais', 'photo_data_url': photo})
        self.assertEqual(response.status_code, 201)
        listed = self.client.get('/api/v1/marketplace/offers', headers=self.headers).get_json()['offers'][0]
        self.assertEqual((listed['photo_data_url'], listed['description']), (photo, 'Œufs frais'))

    def test_old_offers_work_and_invalid_photo_rejected(self):
        payload = {'item': self.item, 'meeting_area': 'Campus'}
        self.assertEqual(self.client.post('/api/v1/marketplace/offers', headers=self.headers, json=payload).status_code, 201)
        for value in ['data:image/svg+xml;base64,PHN2Zz4=', 'data:image/png;base64,AAAA', 'data:image/png;base64,' + 'A' * 700001]:
            with self.subTest(value=value[:30]):
                response = self.client.post('/api/v1/marketplace/offers', headers=self.headers, json={**payload, 'photo_data_url': value})
                self.assertEqual(response.status_code, 422)
