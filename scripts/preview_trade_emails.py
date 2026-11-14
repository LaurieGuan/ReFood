"""Show queued trade notifications with fictitious addresses; never send mail."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'backend'))
from database.engine import get_engine
from services.trade_notification_demo import process_demo_notifications

url = os.environ.get('DATABASE_URL')
if not url:
    raise SystemExit('Set DATABASE_URL to the initialized demo database.')
print('MODE LOCAL — adresses fictives, aucun courriel envoyé')
def show(message):
    print('\n--- Aperçu ---')
    print('À :', message['To'])
    print('Répondre à :', message['Reply-To'])
    print('Sujet :', message['Subject'])
    print(message.get_content())
result = process_demo_notifications(get_engine(url), show)
print(f"Aperçus : {result['previewed']}, échecs à réessayer : {result['failed']}")
