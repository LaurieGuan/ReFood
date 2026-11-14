# Troc : persistance et tests locaux

Les schémas sont dans `schemas/marketplace.py`, les tables dans `orm_models.py`
et le repository dans `database/marketplace.py`. Les endpoints HTTP sont branchés
dans `routes/marketplace.py` sous `/api/v1/marketplace`.

## Initialisation

Depuis la racine, installer les dépendances avec le Python du venv :
`python -m pip install -r src/backend/database/requirements.txt`.
Avec Docker Desktop démarré, suivre `database/README.md` pour le Compose et les
variables d'environnement. Puis depuis `src/backend`, avec DATABASE_URL défini :

```powershell
python -m database.engine
python -m unittest discover -s tests -p 'test_marketplace*.py' -v
```

`create_all` ajoute les nouvelles tables sans supprimer les données existantes.
Les tests locaux utilisent des bases SQLite temporaires supprimées à la fin.
Le moteur MariaDB n'est pas requis pour importer Flask.

## Interfaces pour Dev 1

```python
from database.marketplace import MarketplaceRepository, MarketplaceError
from schemas.marketplace import OfferCreateRequest, ProposalCreateRequest

repo = MarketplaceRepository()  # DATABASE_URL obligatoire; aucune connexion à l'import
offer = repo.create_offer("alice", OfferCreateRequest.model_validate({
    "item": {"ingredient_id": "ing_tomato", "name": "tomato",
             "quantity": {"amount": 6, "unit": "piece"}},
    "meeting_area": "Centre",
}))
```

Méthodes publiques :

- `create_offer(user_id, request) -> ExchangeOffer`
- `list_offers(status="open") -> OfferListResponse`
- `close_offer(user_id, offer_id) -> ExchangeOffer`
- `create_proposal(user_id, request) -> ExchangeProposal`
- `list_proposals(user_id) -> ProposalListResponse`
- `accept_proposal`, `reject_proposal`, `cancel_proposal`, `confirm_proposal` :
  `(user_id, proposal_id) -> ExchangeProposal`.

Les routes récupèrent l'identité dans X-Demo-User-Id (alice, bob ou demo_user).
Sans en-tête, demo_user est conservé pour compatibilité. Ce choix est commun aux
routes pantry et marketplace; il simule deux utilisateurs, sans authentification.
Le gestionnaire central transforme MarketplaceError en ErrorResponse via ses
attributs code, message, status. Le repository n'importe pas Flask.
Le stockage du troc est uniquement SQL. Sans DATABASE_URL, le pantry conserve
son ancien mode mémoire, mais le troc n'utilise pas un second pantry indépendant.
Pour une démo sans MariaDB, injecter un moteur SQLite commun aux deux repositories
et initialiser Base.metadata; voir les tests pour un exemple complet.

## API Flask pour le frontend

Les modèles/JSON détaillés figurent dans MARKETPLACE_CONTRACT_PROPOSAL.md.

| Méthode | Chemin sous /api/v1/marketplace | Réponse |
|---|---|---|
| GET | /offers?status=open | OfferListResponse, 200 |
| POST | /offers | ExchangeOffer, 201 |
| POST | /offers/<offer_id>/close | ExchangeOffer, 200 |
| GET | /proposals | ProposalListResponse du participant courant, 200 |
| POST | /proposals | ExchangeProposal, 201 |
| POST | /proposals/<proposal_id>/accept | ExchangeProposal, 200 |
| POST | /proposals/<proposal_id>/reject | ExchangeProposal, 200 |
| POST | /proposals/<proposal_id>/cancel | ExchangeProposal, 200 |
| POST | /proposals/<proposal_id>/confirm | ExchangeProposal, 200 |

Les actions close/accept/reject/cancel/confirm n'exigent aucun corps JSON.
Les créations utilisent les modèles OfferCreateRequest/ProposalCreateRequest.
Erreurs : 400 JSON malformé/en-tête ou filtre invalide, 422 schéma invalide,
403 action interdite, 404 ID absent, 409 conflit de stock/état. Sans DATABASE_URL,
le troc retourne 503; health et le pantry en mémoire restent utilisables.
Une panne DB inattendue retourne un 500 JSON sans exposer les identifiants.
Les deux routes pantry lisent également la configuration Flask DATABASE_URL,
afin d'utiliser la même base que marketplace, y compris dans les tests.

Exemple de publication après avoir confirmé le stock d'Alice par PUT /api/v1/pantry :
```json
{
  "item": {
    "ingredient_id": "ing_tomato",
    "name": "tomato",
    "quantity": {"amount": 6, "unit": "piece"}
  },
  "meeting_area": "Centre"
}
```
Envoyer X-Demo-User-Id: alice. Une proposition de Bob précise target_offer_id,
proposer_offer_id, target_quantity et proposer_quantity; pas de propriétaire fourni
par le client. Les IDs renvoyés servent aux actions suivantes.
L'interface frontend n'est pas implémentée ici.

## Transactions et quantités

Le MVP sérialise les écritures troc et les remplacements SQL du pantry avec un
**verrou global**. MariaDB verrouille une ligne de `marketplace_lock` jusqu'au
commit/rollback; SQLite utilise BEGIN IMMEDIATE. C'est une simplification des
verrous par utilisateur proposés initialement, adaptée au volume de la démo.
Toutes les écritures de stock doivent passer par ces repositories.

Accepter vérifie le stock disponible et crée deux réservations sans débit.
Les offres sont réservées entièrement; les propositions concurrentes sur ces
offres sont rejetées. Plusieurs offres sur un même ingrédient restent protégées
par la somme des réservations. Annuler les libère. La deuxième confirmation
transfère les deux quantités et ferme les offres dans une seule transaction.
Répéter accept/confirm/cancel sur l'état résultant n'applique pas un second transfert.

Les lots d'un même ingrédient sont agrégés pour vérifier le stock et débités dans
l'ordre de stockage. Unités différentes/inconnues, quantité non finie/inconnue ou
fraction autre que null/1 rendent cet ingrédient non échangeable. Pas de conversion
ou de normalisation implicite. Les lignes à quantité zéro sont conservées après
transfert; les crédits créent une ligne avec remaining_fraction=null.

## Validation réelle MariaDB

Les tests SQLite vérifient les transactions applicatives et les courses entre
threads, mais ne prouvent pas le comportement du verrou MariaDB. Définir
TEST_DATABASE_URL avec un **compte de test** disposant de CREATE/DROP DATABASE
sur un serveur local de test, puis relancer les tests marketplace.
Chaque test MariaDB crée une base `refood_trade_test_<uuid>` et supprime uniquement
cette base à la fin. Il ne vide pas la base indiquée dans l'URL.

Les scénarios couvrent le parcours Alice/Bob, la double confirmation, l'annulation,
les permissions, le stock devenu insuffisant, le rollback après les écritures,
les offres concurrentes sur le même stock et un PUT pantry concurrent à l'acceptation.

Limites : aucune expiration automatique des réservations, aucune pagination,
aucune authentification réelle. Les snapshots des offres/propositions sont en JSON
avec colonnes relationnelles d'identité, de statut et références; réservations et
inventaire sont relationnels. Le verrou global privilégie la simplicité à la capacité.

## Validation exécutée le 2026-11-14

Après branchement des routes, les 14 tests de `test_marketplace_routes.py` passent
également : 7 sur MariaDB réelle et 7 sur SQLite. Ils vérifient les appels HTTP
Flask avec deux identités, les confirmations, les conflits du pantry, les codes
d'erreur et la persistance après création d'une nouvelle application Flask.
Commande : `python -m unittest discover -s tests -p test_marketplace_routes.py -v`
(définir TEST_DATABASE_URL pour inclure les tests MariaDB).

Docker Desktop en mode Linux, image mariadb:11.4, conteneur
`refood-test-mariadb-1` healthy sur 127.0.0.1:3307.
Les 34 tests marketplace passent sans exclusion : 12 sur MariaDB, 12 sur SQLite
et 10 de validation des contrats. Le test réel de persistance des recettes et du
pantry (`test_mariadb_live.py`) passe également. Les bases temporaires des tests
marketplace ont été supprimées par leur teardown.

L'instance de test reste démarrée avec un volume distinct `refood-test_refood_data`.
Ses identifiants sont dans `database/.env.mariadb-test`, ignoré par Git.
Pour l'arrêter depuis la racine sans supprimer le volume :
```powershell
docker compose -p refood-test --env-file src/backend/database/.env.mariadb-test -f src/backend/database/compose.yaml stop
```
