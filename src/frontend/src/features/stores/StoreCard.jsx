import { basketSummary, basketLabel } from './basket.js';
import { label } from "../../utils/ingredients.js";
import { mockApi } from "../../services/api/mockApi.js";

const money = (value) =>
  new Intl.NumberFormat("fr-CA", {
    style: "currency",
    currency: "CAD",
  }).format(value);

export function StoreCard({
  merchant,
  offers,
  required,
  demo,
  selected,
  onSelect,
}) {
  const basket = basketSummary(required, offers, demo);
  offers = basket.offers;
  const total = basket.total;

  return (
    <label className={`store-card ${selected ? "chosen" : ""}`}>
      <input
        type="radio"
        name="store"
        value={merchant.id}
        checked={selected}
        onChange={onSelect}
      />
      <div className="store-card-head">
        <span className="store-icon">⌂</span>
        <span>
          <b>{merchant.name}</b>
          <small>
            {merchant.address}
            {merchant.distance_km != null
              ? ` · ${merchant.distance_km.toFixed(1)} km à vol d’oiseau`
              : ""}
          </small>
        </span>
        <i>{selected ? "✓" : ""}</i>
      </div>
      <div className="offer-list">
        {offers.map((offer) => (
          <div className="offer" key={offer.ingredient_id}>
            <span>
              {label(offer.ingredient_name ?? mockApi.ingredientName(offer.ingredient_id))}
              <small>
                {offer.retailer_link ? <a href={offer.retailer_link} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()}>{offer.product_name}</a> : offer.product_name} {offer.brand ? `· ${offer.brand}` : ""} · {offer.package_quantity ?? "format inconnu"}{" "}
                {offer.package_unit}
                <small>{demo ? "Demo · Sample data" : `Source : ${offer.source ?? "inconnue"} · ${offer.observed_at ?? "date inconnue"} · correspondance retenue`}</small>
              </small>
            </span>
            <b>{money(offer.price_cad)}</b>
          </div>
        ))}
      </div>
      <div className="store-total">
        <span>
          {basketLabel(basket)} ({basket.covered}/{basket.required} ingrédients)
        </span>
        <b>{money(total)}</b>
      </div>
      <p>Sans prix dans ce magasin : {basket.missing.map((item) => label(item.name)).join(", ") || "aucun"}</p>
      <small className="store-source">
        {offers[0]?.source ? `Source ${offers[0].source} · prix observés${offers[0].observed_at ? ` le ${new Date(offers[0].observed_at).toLocaleDateString('fr-CA')}` : ''}` : 'Source démo_catalog · valeurs illustratives'}
      </small>
    </label>
  );
}
