# Dons entreprise → élèves (démo)

## Fonctionnement livré

L'entreprise shop_demo publie des portions/paquets comptés : titre, description,
quantité totale, limite par personne, unité affichée, lieu de retrait, date/heure
limite avec fuseau. pickup_starts_at permet une fenêtre de retrait facultative.
Une unité correspond par exemple à un sac ou une portion, pas à une quantité
canonique du garde-manger. Les dons ne modifient pas automatiquement le pantry.

Les élèves alice, bob et demo_user réservent des quantités entières positives.
Le plafond s'applique **par élève et par offre**, en additionnant les quantités
réservées et déjà récupérées. Une annulation avant retrait libère quantité et
plafond. Il est interdit d'annuler une quantité déjà récupérée pour contourner
la limite. L'entreprise seule confirme la récupération.

À `now >= expires_at`, le serveur refuse toute nouvelle réservation et tout
retrait. L'offre disparaît de la liste disponible; son détail montre expired et
available_quantity=0. Les réservations non récupérées deviennent expired dans
les réponses. Ce calcul se fait à chaque lecture/écriture : aucun cron requis.
La vérification se fait après acquisition du verrou, même si une requête a
commencé avant l'échéance. Le navigateur devra rafraîchir la liste/son compte à
rebours; ce backend ne pousse pas de notification temps réel.

expires_at est la limite déclarée de l'offre et du retrait. Le logiciel ne déduit
pas la salubrité d'un aliment; distinguer dans l'interface cette échéance de toute
date figurant sur son emballage.

## Comptes de démonstration

Envoyer `X-Demo-User-Id: shop_demo` pour l'entreprise, `alice` ou `bob` pour les
élèves. Sans en-tête, demo_user est utilisé. Le rôle est déduit d'une liste fixe
du serveur; aucun business_id/student_id/role transmis dans le JSON n'est accepté.
C'est une simulation locale, pas une connexion par mot de passe. Ne pas exposer
ce dispositif comme authentification réelle. Aucun écran de connexion/front de
don n'est ajouté à cette étape.

## Routes /api/v1/donations

| Méthode et chemin | Accès | Résultat |
|---|---|---|
| POST /offers | Entreprise | DonationOffer, 201 |
| GET /offers | Démo | DonationListResponse des offres disponibles, 200 |
| GET /offers?mine=true | Entreprise | Ses offres, y compris épuisées/expirées/annulées |
| GET /offers/<id> | Démo | DonationOffer avec disponibilité calculée |
| POST /offers/<id>/cancel | Propriétaire | Annule l'offre et les réservations non récupérées |
| POST /offers/<id>/reservations | Élève | DonationReservation, 201 |
| GET /offers/<id>/reservations | Propriétaire | ReservationListResponse |
| GET /reservations | Élève | Ses réservations uniquement |
| POST /reservations/<id>/cancel | Élève propriétaire | Annulation, 200 |
| POST /reservations/<id>/collect | Entreprise propriétaire | Récupération, 200 |

Exemple POST /offers, en entreprise :
```json
{
  "title": "Pains du jour",
  "description": "Un sac contient deux pains",
  "total_quantity": 10,
  "per_person_limit": 2,
  "unit_label": "sac",
  "pickup_location": "Comptoir du magasin",
  "pickup_starts_at": "2026-11-15T16:00:00-05:00",
  "expires_at": "2026-11-15T18:00:00-05:00"
}
```
Adapter les dates à l'avenir. Réservation : `{"quantity":2}`. Actions cancel et
collect : aucun corps JSON requis. Répéter cancel/collect sur leur état résultant
est sans effet supplémentaire. Répéter POST réservation crée une nouvelle
réservation si le stock et le plafond le permettent; le frontend doit bloquer
les doubles clics (clé d'idempotence à envisager ultérieurement).

Statuts d'offre : active, sold_out, expired, cancelled. Statuts de réservation :
reserved, collected, cancelled, expired. Une réservation collected reste telle
après expiration de l'offre. Une offre annulée ne peut plus être réservée.
Les limites/dates ne sont pas modifiables après publication dans ce MVP.

Erreurs au format ErrorResponse existant : 400 JSON malformé/filtre invalide,
422 schéma invalide, 403 rôle/propriétaire incorrect, 404 ID absent, 409 conflit
(PERSON_LIMIT_EXCEEDED, INSUFFICIENT_STOCK, OFFER_EXPIRED, PICKUP_NOT_STARTED,
INVALID_STATE). Sans DATABASE_URL : 503; health reste indépendant du DB.

## Persistance et intégration

Nouvelles tables SQLAlchemy : donation_offers, donation_reservations, sans
modification des contrats existants du troc/pantry. Les écritures réutilisent le
verrou global transactionnel du MVP, empêchant le dépassement du stock et des
plafonds même avec plusieurs requêtes simultanées. Annulation et rollback sont
atomiques. L'historique est conservé; l'expiration effective est calculée plutôt
que d'exiger une tâche planifiée qui change les lignes.

Depuis src/backend, avec DATABASE_URL défini :
```powershell
python -m database.engine
python app.py
```
L'initialisation explicite ajoute les tables sans supprimer les données existantes.
API Python : `DonationRepository(engine=None, clock=None)` dans database.donations,
avec create_offer, list_offers, get_offer, reserve, list_reservations,
cancel_offer, cancel_reservation, collect_reservation. clock est injectable pour
tester les frontières temporelles; les routes utilisent l'heure du serveur.
Les réponses sont les modèles existants du nouveau schemas/donations.py.

## Tests

```powershell
python -m unittest discover -s tests -p test_donations.py -v
```
Sans TEST_DATABASE_URL : SQLite temporaire. Avec TEST_DATABASE_URL : mêmes
scénarios sur MariaDB réelle, dans des bases refood_donation_test_<uuid> créées et
supprimées par chaque test. Le compte de test doit permettre CREATE/DROP DATABASE.
Ne pas utiliser un compte de production.

Scénarios : rôle entreprise/élève, publication, réservations cumulées, annulation,
plafond après récupération, expiration exacte et après attente du verrou, fenêtre
de retrait, concurrence entre élèves et pour le même élève, rollback, persistance,
confidentialité des réservations et connexion au repository depuis les routes.

Validation du 2026-11-14 : suite complète **129 tests réussis**, sans exclusion,
dont 24 tests du don (12 SQLite et 12 MariaDB réelle via Docker sur le port 3307).
Les tests existants du troc, du pantry et des recettes passent également.

## Améliorations possibles après le MVP

- Code de retrait à usage unique pour retrouver et confirmer une réservation.
- Rappel avant la fin du retrait, avec accord de l'élève.
- Photo du lot et informations d'allergènes déclarées par l'entreprise.
- Historique des dons récupérés et nombre de portions redistribuées.
- Véritable authentification et validation des entreprises avant ouverture publique.
