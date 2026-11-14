"""Add sample offers to an explicitly selected, initialized demo database."""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'backend'))
from database.donations import DonationRepository
from database.engine import get_engine
from schemas.donations import DonationCreateRequest

url = os.environ.get('DATABASE_URL')
if not url:
    raise SystemExit('Set DATABASE_URL to an initialized demo database first.')
repo = DonationRepository(get_engine(url))
existing = {offer.title for offer in repo.list_offers('shop_demo', True).offers if offer.status.value == 'active'}
for title, description, count, limit, unit in [
    ('Démo REFOOD — pains du jour', 'Sac de pains à récupérer au comptoir.', 8, 2, 'sac'),
    ('Démo REFOOD — légumes', 'Panier de légumes de saison.', 5, 1, 'panier'),
]:
    if title in existing:
        print(f'Offre déjà active : {title}')
        continue
    offer = repo.create_offer('shop_demo', DonationCreateRequest(
        title=title, description=description, total_quantity=count, per_person_limit=limit,
        unit_label=unit, pickup_location='Comptoir du commerce démo', expires_at=datetime.now(timezone.utc) + timedelta(days=7)))
    print(f'Offre créée : {offer.title}')
print('Identités simulées : shop_demo, alice, bob. Aucun mot de passe ni prix dans le contrat actuel.')
