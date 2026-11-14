# Contrats du troc — proposition à valider avec Developer 1

Statut : schémas Pydantic implémentés après accord du responsable humain dans
ce chat. Intégration routes/persistance à coordonner avec Dev 1; aucune
confirmation directe de Dev 1 n'a été reçue.
Base inspectée : main 7918964, intégré dans feature/database le 2026-11-14.
Propriétaires : Dev 1 (HTTP), Dev 2 (persistance), frontend (confirmation).

## Périmètre de la première démo

Échange de deux surplus d'ingrédients confirmés, un aliment par offre.
Deux utilisateurs de démonstration, Alice et Bob. Pas d'échange de plats préparés,
de paiement, de livraison ou de messagerie dans cette première version.
L'identité vient du contexte de requête, jamais d'un owner_id envoyé dans le JSON.
Proposition locale : en-tête X-Demo-User-Id avec alice/bob autorisés et demo_user
par défaut, utilisé également par les routes pantry. Ce mécanisme est une
simulation d'identité locale, pas de l'authentification.

## Réutilisation des schémas

Réutiliser IngredientWithQuantity, IngredientQuantity, Unit et ErrorResponse.
Ne pas créer un second modèle d'ingrédient. Les IDs sont ceux du normalizer Dev 3.
Pour le troc seulement, vérifier une quantité finie strictement positive,
unité différente de unknown. Les schémas de recettes/pantry gardent leurs règles
actuelles et continuent d'accepter les quantités inconnues.
MVP : même unité exacte entre offre, proposition et stock confirmé; conversions
et quantités/fractions ambiguës sont refusées, jamais estimées.

## Modèles proposés pour schemas/marketplace.py

Les noms/structures ci-dessous sont maintenant définis dans schemas/marketplace.py.
Les dates sont des datetime UTC avec fuseau, générées côté serveur.
Les identifiants sont opaques et générés côté serveur.

| Modèle | Champs |
|---|---|
| OfferCreateRequest | item: IngredientWithQuantity; description: str ou null; meeting_area: str |
| ExchangeOffer | offer_id: str; owner_id: str; item: IngredientWithQuantity; description: str ou null; meeting_area: str; status: OfferStatus; created_at: datetime |
| OfferListResponse | offers: list[ExchangeOffer] |
| ProposalCreateRequest | target_offer_id: str; proposer_offer_id: str; target_quantity: IngredientQuantity; proposer_quantity: IngredientQuantity |
| ExchangeProposal | proposal_id: str; target_owner_id: str; proposer_id: str; target_offer_id: str; proposer_offer_id: str; target_item: IngredientWithQuantity; proposer_item: IngredientWithQuantity; status: ProposalStatus; confirmed_by: list[str]; created_at: datetime; updated_at: datetime |
| ProposalListResponse | proposals: list[ExchangeProposal] |

OfferStatus : open, reserved, closed.
ProposalStatus : pending, accepted, rejected, cancelled, completed.
target_item/proposer_item sont des instantanés serveur avec les quantités
convenues, pas les quantités complètes de l'offre ni des champs client libres.
confirmed_by contient uniquement les IDs des participants.
Une offre correspond à un lot : une acceptation réserve l'offre entière dans
le MVP, même si l'échange porte sur une partie du lot. Le surplus reste au pantry.
Après réalisation, les deux offres ferment; le surplus peut faire une nouvelle offre.

## Routes proposées, à implémenter par Dev 1

| Méthode et chemin sous /api/v1 | Résultat |
|---|---|
| POST /marketplace/offers | ExchangeOffer, 201 |
| GET /marketplace/offers | OfferListResponse, 200; filtre status=open par défaut |
| POST /marketplace/offers/<id>/close | ExchangeOffer, 200; propriétaire seulement |
| POST /marketplace/proposals | ExchangeProposal, 201 |
| GET /marketplace/proposals | ProposalListResponse, 200; propositions du participant courant |
| POST /marketplace/proposals/<id>/accept | ExchangeProposal, 200; propriétaire cible seulement |
| POST /marketplace/proposals/<id>/reject | ExchangeProposal, 200; propriétaire cible seulement |
| POST /marketplace/proposals/<id>/cancel | ExchangeProposal, 200; un participant |
| POST /marketplace/proposals/<id>/confirm | ExchangeProposal, 200; un participant |

Les actions n'ont pas de JSON requis. Erreurs : 400 JSON malformé, 422 données
invalides, 403 action interdite, 404 ID absent, 409 conflit de stock ou d'état.
Format existant ErrorResponse, avec codes FORBIDDEN, NOT_FOUND,
INSUFFICIENT_STOCK et INVALID_STATE selon le cas.
Pas d'adresses exactes dans les offres; meeting_area est un secteur public grossier.

## Invariants de persistance et transitions — Dev 2

1. Publier/proposer ne réserve et ne transfère rien. Revalider le stock à l'acceptation.
2. Refuser une proposition sur sa propre offre; chaque offre appartient au bon
   participant. Les quantités demandées ne dépassent pas les lots annoncés.
3. pending -> accepted : verrouiller utilisateurs/inventaires et offres dans
   un ordre déterministe, vérifier le stock disponible moins les réservations,
   créer deux réservations et marquer les offres reserved dans une transaction.
   Les autres propositions en attente utilisant un de ces lots deviennent rejected.
4. pending -> rejected par la cible; pending/accepted -> cancelled par un participant.
   Annuler libère toutes les réservations et rouvre les deux offres si acceptées.
5. accepted : la première confirmation enregistre son auteur; la seconde réalise
   les deux débits/crédits de stock, libère les réservations, ferme les offres et
   passe à completed dans une seule transaction.
6. Répéter accept/confirm/cancel sur l'état résultant est sans effet supplémentaire.
   Une transition incompatible retourne 409. Aucune double application des stocks.
7. replace_pantry doit partager les mêmes verrous et rejeter une modification
   qui supprime/réduit le stock sous une réservation ou rend son unité ambiguë.
   Les anciennes recettes/matchers ne changent pas.
8. Stock : agréger les lignes d'un même ID et unité connue. Pour débiter,
   parcourir les lignes en ordre stable. Refuser un remaining_fraction différent
   de null ou 1 pour les lots échangés; aucune multiplication implicite.
   Les crédits utilisent la quantité absolue reçue et remaining_fraction=null.
9. Une erreur provoque un rollback complet. Les offres peuvent devenir périmées
   avant acceptation : publier plusieurs offres ne garantit pas le stock.

Tables proposées : marketplace_offers, marketplace_proposals,
marketplace_reservations et une ligne de verrou utilisateur stable par utilisateur
(nécessaire même pour un pantry vide). Garder les modèles SQLAlchemy séparés
des contrats Pydantic; aucun import Flask dans les repositories.

## Interfaces de repository proposées

```text
create_offer(user_id, request: OfferCreateRequest) -> ExchangeOffer
list_offers(status=OfferStatus.OPEN) -> OfferListResponse
close_offer(user_id, offer_id) -> ExchangeOffer
create_proposal(user_id, request: ProposalCreateRequest) -> ExchangeProposal
list_proposals(user_id) -> ProposalListResponse
accept_proposal(user_id, proposal_id) -> ExchangeProposal
reject_proposal(user_id, proposal_id) -> ExchangeProposal
cancel_proposal(user_id, proposal_id) -> ExchangeProposal
confirm_proposal(user_id, proposal_id) -> ExchangeProposal
```

## Scénario local et critères d'acceptation

Alice a 6 tomates (piece); Bob a 4 œufs (piece). Alice publie ses tomates,
Bob ses œufs puis propose 4 œufs contre 3 tomates. Alice accepte; deux
réservations existent mais les stocks bruts n'ont pas changé. Chacun confirme.
Résultat : Alice a 3 tomates et 4 œufs; Bob a 3 tomates et 0 œuf.
Les deux offres sont closed et la proposition completed.

Tests requis : schémas valides/invalides, isolation des utilisateurs, refus de
sa propre offre, permissions, stock insuffisant, annulation/libération, confirmation
double sans double débit, rollback et persistance après nouvelle connexion.
Deux transactions MariaDB concurrentes doivent réserver le même stock une seule
fois. Tester aussi un PUT pantry concurrent à l'acceptation. SQLite ne prouve
pas la correction des verrous MariaDB. Utiliser une base de test dédiée.

## Handoff à Dev 1 et prochaine phase

Aligner les routes sur les modèles ci-dessus, puis valider X-Demo-User-Id partagé avec pantry,
la réservation du lot entier et la confirmation par les deux participants.
La modification partagée effectuée est limitée à schemas/marketplace.py;
Les routes ont également été branchées après autorisation explicite du responsable
humain dans ce chat. Aucun message externe n'a été envoyé à l'équipe.
Voir MARKETPLACE.md pour le repository, les routes, les tests et le choix
d'un verrou global de démo plutôt que les verrous par utilisateur proposés ici.

Contraintes effectives : quantités finies > 0, unités connues, noms/IDs non vides,
secteur de 1 à 200 caractères, description de 1000 caractères maximum.
Les requêtes refusent les champs supplémentaires, notamment les IDs et statuts
gérés par le serveur. Les dates doivent inclure un fuseau et sont normalisées UTC.
Un snapshot completed exige deux confirmations distinctes des participants;
accepted en autorise au plus une. cancelled peut conserver une confirmation
antérieure pour audit. Ces contrôles ne remplacent jamais les vérifications
transactionnelles de stock, permissions et transitions.

Tests des contrats : depuis src/backend, exécuter
`python -m unittest discover -s tests -p test_marketplace_schemas.py -v`.
