import { useCallback, useEffect, useState } from "react";
import "./marketplace.css";

const names = { alice: "Alice", bob: "Bob", demo_user: "Utilisateur démo" };
const statusNames = { pending: "En attente", accepted: "Acceptée", rejected: "Refusée", cancelled: "Annulée", completed: "Terminée" };

async function callMarketplace(path, user, body, method = "POST") {
  let response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method: body === undefined ? "GET" : method,
      headers: { "X-Demo-User-Id": user, ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
  } catch {
    throw new Error("Impossible de joindre le serveur Flask. Vérifiez qu’il est démarré.");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 503) throw new Error("Le troc nécessite une base de données configurée et initialisée.");
    const messages = { INSUFFICIENT_STOCK: "Stock insuffisant ou déjà réservé.", FORBIDDEN: "Cette action n’est pas permise pour cet utilisateur.", INVALID_STATE: "Cette opération n’est plus possible dans l’état actuel.", VALIDATION_ERROR: "Vérifiez les quantités et les champs requis." };
    throw new Error(messages[data.error?.code] ?? `Le serveur a refusé la demande (HTTP ${response.status}).`);
  }
  return data;
}

const displayItem = (item) => `${item.name} · ${item.quantity.amount} ${item.quantity.unit === "piece" ? "pièce(s)" : item.quantity.unit}`;

export function Marketplace() {
  const [user, setUser] = useState("alice");
  const [offers, setOffers] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [pantry, setPantry] = useState([]);
  const [selectedItem, setSelectedItem] = useState("");
  const [amount, setAmount] = useState("");
  const [area, setArea] = useState("");
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState("");
  const [photoInputKey, setPhotoInputKey] = useState(0);
  const selectPhoto = async (event) => {
    const file = event.target.files?.[0];
    setPhoto("");
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 15 * 1024 * 1024) {
      setError("Choisissez une image JPG, PNG ou WebP de 15 Mo maximum.");
      event.target.value = "";
      return;
    }
    setError("");
    const url = URL.createObjectURL(file);
    try {
      const image = new Image();
      image.src = url;
      await image.decode();
      const scale = Math.min(1, 1200 / Math.max(image.naturalWidth, image.naturalHeight));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      const context = canvas.getContext("2d");
      if (!context) throw new Error("canvas unavailable");
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      let result = "";
      for (const quality of [0.85, 0.7, 0.55, 0.4]) {
        result = canvas.toDataURL("image/jpeg", quality);
        if (result.length <= 699000) break;
      }
      if (!result.startsWith("data:image/jpeg;base64,") || result.length > 699000) throw new Error("photo too large");
      setPhoto(result);
    } catch {
      setError("Impossible de lire ou de réduire cette photo. Essayez une autre image.");
      event.target.value = "";
    } finally { URL.revokeObjectURL(url); }
  };
  const [targetId, setTargetId] = useState("");
  const [ownId, setOwnId] = useState("");
  const [targetAmount, setTargetAmount] = useState("");
  const [ownAmount, setOwnAmount] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [stockIngredient, setStockIngredient] = useState("ing_egg");
  const [stockAmount, setStockAmount] = useState("");
  const [stockUnit, setStockUnit] = useState("piece");

  const refresh = useCallback(async (identity, active = () => true) => {
    const [offerData, proposalData, pantryData] = await Promise.all([
      callMarketplace("/marketplace/offers", identity),
      callMarketplace("/marketplace/proposals", identity),
      callMarketplace("/pantry", identity),
    ]);
    if (active()) { setOffers(offerData.offers); setProposals(proposalData.proposals); setPantry(pantryData.items); }
  }, []);

  useEffect(() => {
    let active = true;
    setOffers([]); setProposals([]); setPantry([]); setSelectedItem(""); setTargetId(""); setOwnId(""); setError(""); setNotice("");
    refresh(user, () => active).catch((err) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [user, refresh]);

  const run = async (action, success) => {
    setBusy(true); setError(""); setNotice("");
    try { await action(); await refresh(user); setNotice(success); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const eligible = pantry.filter((item) => item.quantity?.amount > 0 && item.quantity.unit !== "unknown" && (item.remaining_fraction == null || item.remaining_fraction === 1));
  const item = selectedItem === "" ? null : eligible[Number(selectedItem)];
  const myOffers = offers.filter((offer) => offer.owner_id === user);
  const otherOffers = offers.filter((offer) => offer.owner_id !== user);
  const target = otherOffers.find((offer) => offer.offer_id === targetId);
  const own = myOffers.find((offer) => offer.offer_id === ownId);

  return <section className="marketplace">
    <div className="marketplace-intro"><div><h2>Échanger des ingrédients</h2><p>Proposez un ingrédient de votre garde-manger contre une autre offre.</p></div><label>Utilisateur de démo <select value={user} onChange={(event) => setUser(event.target.value)} disabled={busy}>{Object.entries(names).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label></div>
    <p className="marketplace-note">Identités de démonstration : elles ne constituent pas une connexion sécurisée. Les repas préparés ne sont pas encore pris en charge. Après acceptation, les deux participants recevront chacun l’adresse courriel de l’autre pour organiser la rencontre ; en mode local, les adresses sont fictives et aucun courriel réel n’est envoyé.</p>
    {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError("")} aria-label="Fermer">×</button></div>}
    {notice && <p className="marketplace-success" role="status">{notice}</p>}
    <section className="panel marketplace-section"><h3>Garde-manger de {names[user]}</h3><p>Ajoutez un stock connu avant de publier une offre. La quantité est ajoutée à votre liste existante.</p>
      {pantry.length > 0 && <p>{pantry.map((entry, index) => <span key={`${entry.ingredient_id}-${index}`}>{index > 0 ? " · " : ""}{entry.name} ({entry.quantity?.amount ?? "quantité inconnue"} {entry.quantity?.unit === "unknown" ? "" : entry.quantity?.unit})</span>)}</p>}
      <form className="marketplace-form" onSubmit={(event) => { event.preventDefault(); const known = { ing_egg: "egg", ing_tomato: "tomato", ing_avocado: "avocado", ing_milk: "milk", ing_pasta: "pasta", ing_rice: "rice" }; run(async () => { const current = await callMarketplace("/pantry", user); await callMarketplace("/pantry", user, { items: [...current.items, { ingredient_id: stockIngredient, name: known[stockIngredient], quantity: { amount: Number(stockAmount), unit: stockUnit }, remaining_fraction: null }] }, "PUT"); setStockAmount(""); }, "Stock ajouté au garde-manger."); }}>
        <label>Aliment<select value={stockIngredient} onChange={(event) => setStockIngredient(event.target.value)}><option value="ing_egg">Œuf</option><option value="ing_tomato">Tomate</option><option value="ing_avocado">Avocat</option><option value="ing_milk">Lait</option><option value="ing_pasta">Pâtes</option><option value="ing_rice">Riz</option></select></label>
        <label>Quantité<input type="number" min="0.001" step="any" value={stockAmount} onChange={(event) => setStockAmount(event.target.value)} required /></label>
        <label>Unité<select value={stockUnit} onChange={(event) => setStockUnit(event.target.value)}><option value="piece">Pièce(s)</option><option value="g">g</option><option value="kg">kg</option><option value="ml">ml</option><option value="l">L</option></select></label>
        <button className="button secondary" disabled={busy}>Ajouter au garde-manger</button>
      </form>
    </section>
    <div className="marketplace-grid">
      <section className="panel"><h3>Publier une offre</h3><p>Choisissez un ingrédient avec une quantité connue dans le garde-manger de {names[user]}.</p>
        <form className="marketplace-form" onSubmit={(event) => { event.preventDefault(); if (!item) return; run(async () => { await callMarketplace("/marketplace/offers", user, { item: { ingredient_id: item.ingredient_id, name: item.name, quantity: { amount: Number(amount), unit: item.quantity.unit } }, description: description.trim(), meeting_area: area.trim(), photo_data_url: photo }); setAmount(""); setArea(""); setDescription(""); setPhoto(""); setPhotoInputKey((key) => key + 1); }, "Offre publiée."); }}>
          <label>Ingrédient<select value={selectedItem} onChange={(event) => setSelectedItem(event.target.value)} required><option value="">Choisir…</option>{eligible.map((entry, index) => <option value={index} key={`${entry.ingredient_id}-${index}`}>{displayItem(entry)}</option>)}</select></label>
          {!eligible.length && <small>Aucun ingrédient admissible. Ajoutez d’abord un stock avec quantité et unité connues dans le garde-manger de cet utilisateur.</small>}
          <label>Quantité à offrir {item && `(${item.quantity.unit})`}<input type="number" min="0.001" step="any" max={item?.quantity.amount} value={amount} onChange={(event) => setAmount(event.target.value)} required /></label>
          <label>Secteur de rencontre<input value={area} onChange={(event) => setArea(event.target.value)} maxLength={200} placeholder="Ex. quartier Rosemont" required /></label>
          <label>Description<textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={1000} required placeholder="Décrivez votre aliment et son état" /></label>
          <label>Photo de l’aliment<input key={photoInputKey} type="file" accept="image/jpeg,image/png,image/webp" onChange={selectPhoto} required /></label>
          <small>JPG, PNG ou WebP · 15 Mo maximum. La photo est réduite avant l’envoi. Sur mobile, vous pouvez utiliser votre appareil photo.</small>
          {photo && <img className="marketplace-photo" src={photo} alt="Aperçu de l’offre" />}
          <button className="button primary" disabled={busy || !item || !photo || !description.trim()}>Publier l’offre</button>
        </form>
      </section>
      <section className="panel"><h3>Offres disponibles</h3><p>Choisissez une offre et proposez l’une des vôtres en échange.</p>
        {otherOffers.length === 0 ? <p>Aucune autre offre disponible.</p> : <div className="marketplace-offers">{otherOffers.map((offer) => <button type="button" className={`marketplace-offer ${targetId === offer.offer_id ? "selected" : ""}`} key={offer.offer_id} onClick={() => { setTargetId(offer.offer_id); setTargetAmount(String(offer.item.quantity.amount)); }}>{offer.photo_data_url && <img className="marketplace-photo" src={offer.photo_data_url} alt={`Photo de ${offer.item.name}`} />}<strong>{displayItem(offer.item)}</strong><span>{names[offer.owner_id] ?? offer.owner_id} · {offer.meeting_area}</span>{offer.description && <small>{offer.description}</small>}</button>)}</div>}
        {target && <form className="marketplace-form" onSubmit={(event) => { event.preventDefault(); if (!own) return; run(() => callMarketplace("/marketplace/proposals", user, { target_offer_id: target.offer_id, proposer_offer_id: own.offer_id, target_quantity: { amount: Number(targetAmount), unit: target.item.quantity.unit }, proposer_quantity: { amount: Number(ownAmount), unit: own.item.quantity.unit } }), "Proposition envoyée."); }}>
          <label>Votre offre<select value={ownId} onChange={(event) => { const id = event.target.value; setOwnId(id); setOwnAmount(String(myOffers.find((offer) => offer.offer_id === id)?.item.quantity.amount ?? "")); }} required><option value="">Choisir…</option>{myOffers.map((offer) => <option key={offer.offer_id} value={offer.offer_id}>{displayItem(offer.item)}</option>)}</select></label>
          {!myOffers.length && <small>Publiez d’abord votre propre offre pour proposer un échange.</small>}
          <label>Quantité demandée ({target.item.quantity.unit})<input type="number" min="0.001" step="any" max={target.item.quantity.amount} value={targetAmount} onChange={(event) => setTargetAmount(event.target.value)} required /></label>
          <label>Quantité proposée {own && `(${own.item.quantity.unit})`}<input type="number" min="0.001" step="any" max={own?.item.quantity.amount} value={ownAmount} onChange={(event) => setOwnAmount(event.target.value)} required /></label>
          <button className="button primary" disabled={busy || !own}>Proposer l’échange</button>
        </form>}
      </section>
    </div>
    <section className="panel marketplace-section"><h3>Mes offres ouvertes</h3>{myOffers.length ? myOffers.map((offer) => <div className="marketplace-row" key={offer.offer_id}><span>{offer.photo_data_url && <img className="marketplace-photo" src={offer.photo_data_url} alt={`Photo de ${offer.item.name}`} />}{displayItem(offer.item)} · {offer.meeting_area}{offer.description && <small> · {offer.description}</small>}</span><button className="text-button" disabled={busy} onClick={() => run(() => callMarketplace(`/marketplace/offers/${encodeURIComponent(offer.offer_id)}/close`, user, {}), "Offre fermée.")}>Fermer l’offre</button></div>) : <p>Aucune offre ouverte.</p>}</section>
    <section className="panel marketplace-section"><h3>Mes propositions</h3>{proposals.length ? proposals.map((proposal) => <div className="marketplace-proposal" key={proposal.proposal_id}><strong>{displayItem(proposal.proposer_item)} ⇄ {displayItem(proposal.target_item)}</strong><p>{statusNames[proposal.status] ?? proposal.status} · {names[proposal.proposer_id] ?? proposal.proposer_id} → {names[proposal.target_owner_id] ?? proposal.target_owner_id}</p>{proposal.status === "accepted" && <small>{proposal.confirmed_by.includes(user) ? "Vous avez confirmé. " : ""}{proposal.confirmed_by.length}/2 confirmations</small>}<div className="marketplace-actions">{proposal.status === "pending" && proposal.target_owner_id === user && <><button className="button primary" disabled={busy} onClick={() => run(() => callMarketplace(`/marketplace/proposals/${proposal.proposal_id}/accept`, user, {}), "Proposition acceptée.")}>Accepter</button><button className="button secondary" disabled={busy} onClick={() => run(() => callMarketplace(`/marketplace/proposals/${proposal.proposal_id}/reject`, user, {}), "Proposition refusée.")}>Refuser</button></>}{["pending", "accepted"].includes(proposal.status) && <button className="button secondary" disabled={busy} onClick={() => run(() => callMarketplace(`/marketplace/proposals/${proposal.proposal_id}/cancel`, user, {}), "Proposition annulée.")}>Annuler</button>}{proposal.status === "accepted" && !proposal.confirmed_by.includes(user) && <button className="button primary" disabled={busy} onClick={() => run(() => callMarketplace(`/marketplace/proposals/${proposal.proposal_id}/confirm`, user, {}), "Confirmation enregistrée.")}>Confirmer l’échange</button>}</div></div>) : <p>Aucune proposition pour le moment.</p>}</section>
  </section>;
}
