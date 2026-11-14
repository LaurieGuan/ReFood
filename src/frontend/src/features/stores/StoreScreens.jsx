import { label } from "../../utils/ingredients.js";
import { mockApi } from "../../services/api/mockApi.js";
import { StoreCard } from "./StoreCard.jsx";

export function StoreScreen({
  recipe,
  ingredientIds,
  priceData,
  selectedStore,
  setSelectedStore,
  onLocate,
  onContinue,
}) {
  const missing = recipe.match?.missing_ingredients ?? recipe.ingredients.filter(
    (item) => item.essential && !ingredientIds.includes(item.ingredient_id),
  );
  const merchants = priceData.stores.filter((store) =>
    priceData.offers.some((offer) => offer.store_id === store.id),
  );
  const hasNeeds = missing.length > 0;
  return (
    <section className="store-screen">
      <div className="store-heading">
        <div>
          <h2>Pour cuisiner : {recipe.title}</h2>
          <p>
            Les produits trouvés sont à vérifier. Les montants correspondent au prix du paquet complet, pas à la quantité utilisée.
          </p>
        </div>
        <span className="demo-tag">{priceData.demo ? "PRIX ILLUSTRATIFS" : "PRIX OBSERVÉS"}</span>
      </div>
      {!hasNeeds && (
        <div className="panel no-purchases">
          <span>✓</span>
          <div>
            <b>Tout est déjà dans votre liste confirmée.</b>
            <small>Aucun achat essentiel à comparer pour cette recette.</small>
          </div>
        </div>
      )}
      {hasNeeds && merchants.length === 0 && (
        <div className="panel no-purchases">
          <span>i</span>
          <div>
            <b>Aucune offre trouvée pour les ingrédients manquants.</b>
            <small>
              Vous pourrez tout de même exporter votre liste sans prix.
            </small>
          </div>
        </div>
      )}
      {priceData.demo && <div className="store-location">
        Classez les magasins fictifs selon votre position.{" "}
        <button className="text-button" onClick={onLocate}>
          Utiliser ma position
        </button>
      </div>}
      {!!merchants.length && (
        <div className="store-grid">
          {merchants.map((merchant) => {
            const offers = priceData.offers.filter(
              (item) => item.store_id === merchant.id,
            );
            return (
              <StoreCard
                key={merchant.id}
                merchant={merchant}
                offers={offers}
                missingCount={missing.length}
                selected={selectedStore === merchant.id}
                onSelect={() => setSelectedStore(merchant.id)}
              />
            );
          })}
        </div>
      )}
      {!!priceData.unverified?.length && <p className="safety-note">Correspondances non vérifiées, exclues des totaux : {priceData.unverified.map((p) => `${p.ingredient_name} → ${p.product_name}`).join('; ')}</p>}
      {priceData.unpriced_ingredient_ids.length > 0 && (
        <p className="unpriced-note">
          Prix introuvable pour :{" "}
          {priceData.unpriced_ingredient_ids
            .map((id) => label(priceData.missing_ingredients?.find((item) => item.ingredient_id === id)?.name ?? mockApi.ingredientName(id)))
            .join(", ")}
          .
        </p>
      )}
      <div className="store-footer">
        <button className="button primary" onClick={onContinue}>
          Continuer vers l’export →
        </button>
      </div>
      <p className="price-disclaimer">
        {priceData.demo ? "Offres fictives fournies par l’API de démonstration." : "Produits trouvés par recherche : vérifiez leur correspondance et les prix auprès du détaillant."}
      </p>
    </section>
  );
}

export function ExportScreen({
  recipe,
  ingredientIds,
  priceData,
  selectedStore,
  origin,
  setOrigin,
  onDownload,
  onRestart,
}) {
  const missing = recipe.match?.missing_ingredients ?? recipe.ingredients.filter(
    (item) => item.essential && !ingredientIds.includes(item.ingredient_id),
  );
  const offers =
    priceData?.offers.filter((offer) => offer.store_id === selectedStore) ?? [];
  const store = priceData?.stores.find((item) => item.id === selectedStore);
  const mapUrl = store?.address
    ? `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(store.address)}${origin.trim() ? `&origin=${encodeURIComponent(origin.trim())}` : ""}`
    : null;
  return (
    <section className="export-screen">
      <div className="export-top">
        <span className="export-check">✓</span>
        <div>
          <h2>Votre liste est prête</h2>
          <p>
            {recipe.title}
            {store ? ` · ${store.name}` : ""}
          </p>
        </div>
      </div>
      <div className="panel export-list">
        <div className="export-list-head">
          <h3>À acheter</h3>
          <span>
            {missing.length} article{missing.length === 1 ? "" : "s"}
          </span>
        </div>
        {missing.length ? (
          missing.map((item) => {
            const offer = offers.find(
              (entry) => entry.ingredient_id === item.ingredient_id,
            );
            return (
              <div className="export-item" key={item.ingredient_id}>
                <span className="export-checkbox" />
                <span className="export-name">
                  {label(item.name)}
                  <small>
                    {item.quantity == null
                      ? "Quantité inconnue"
                      : `${item.quantity} ${item.unit}`}
                    {offer ? ` · ${offer.product_name}` : ""}
                  </small>
                </span>
                <b>{offer ? `${offer.price_cad} $` : "Prix inconnu"}</b>
              </div>
            );
          })
        ) : (
          <div className="all-set">
            Vous avez confirmé tous les ingrédients essentiels pour cette
            recette.
          </div>
        )}
        {selectedStore && offers.length > 0 && (
          <div className="export-total">
            <span>{offers.length === missing.length ? "Panier complet · coût indicatif" : "Panier incomplet · sous-total indicatif"}</span>
            <b>
              {offers
                .reduce((sum, offer) => sum + Number(offer.price_cad), 0)
                .toFixed(2)}{" "}
              $ CAD
            </b>
          </div>
        )}
      </div>
      <label className="route-origin">
        Adresse de départ (facultative)
        <input
          value={origin}
          onChange={(event) => setOrigin(event.target.value)}
          placeholder="Votre adresse"
        />
      </label>
      <div className="export-actions">
        <button className="button primary" onClick={onDownload}>
          ↓ &nbsp; Télécharger la liste (.txt)
        </button>
        {mapUrl && (
          <a
            className="button secondary"
            href={mapUrl}
            target="_blank"
            rel="noreferrer"
          >
            Ouvrir l’itinéraire dans Maps ↗
          </a>
        )}
        <button className="button text-only" onClick={onRestart}>
          Nouveau scan
        </button>
      </div>
      <p className="price-disclaimer">
        {priceData?.demo ? "La liste est créée sur votre appareil. Les prix affichés sont fictifs." : "La liste est créée sur votre appareil. Vérifiez les produits et les prix auprès du détaillant."}
      </p>
    </section>
  );
}
