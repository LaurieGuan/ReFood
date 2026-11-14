import { useCallback, useEffect, useState } from 'react';
import '../marketplace/marketplace.css';

async function donationRequest(path, user, payload) {
  let response;
  try {
    response = await fetch(`/api/v1/donations${path}`, {
      method: payload === undefined ? 'GET' : 'POST',
      headers: { 'X-Demo-User-Id': user, ...(payload === undefined ? {} : { 'Content-Type': 'application/json' }) },
      ...(payload === undefined ? {} : { body: JSON.stringify(payload) }),
    });
  } catch { throw new Error('Impossible de joindre Flask. Vérifiez que le serveur est démarré.'); }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const messages = { INSUFFICIENT_STOCK: 'La quantité disponible a changé. Actualisez les offres.', PERSON_LIMIT_EXCEEDED: 'La limite par personne est dépassée.', OFFER_EXPIRED: 'Cette offre a expiré.', FORBIDDEN: 'Cette action ne vous est pas permise.' };
    throw new Error(response.status === 503 ? 'Les offres nécessitent une base de données configurée et initialisée.' : (messages[data.error?.code] ?? data.error?.message ?? `Erreur HTTP ${response.status}`));
  }
  return data;
}
const blank = { title: '', description: '', total_quantity: '1', per_person_limit: '1', unit_label: 'portion', pickup_location: '', expires_at: '' };
const statuses = { active: 'Disponible', sold_out: 'Épuisée', expired: 'Expirée', cancelled: 'Annulée', reserved: 'Réservée', collected: 'Récupérée' };
export function Donations() {
  const [user, setUser] = useState('alice');
  const [offers, setOffers] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [offerReservations, setOfferReservations] = useState({});
  const [amounts, setAmounts] = useState({});
  const [form, setForm] = useState(blank);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const business = user === 'shop_demo';
  const refresh = useCallback(async (identity, active = () => true) => {
    const shop = identity === 'shop_demo';
    const [listed, booked] = await Promise.all([
      donationRequest(`/offers${shop ? '?mine=true' : ''}`, identity),
      shop ? Promise.resolve({ reservations: [] }) : donationRequest('/reservations', identity),
    ]);
    if (active()) { setOffers(listed.offers); setReservations(booked.reservations); }
  }, []);
  useEffect(() => {
    let active = true;
    setOffers([]); setReservations([]); setOfferReservations({}); setError(''); setNotice('');
    refresh(user, () => active).catch((e) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [user, refresh]);
  const run = async (fn, message) => {
    setBusy(true); setError(''); setNotice('');
    try { await fn(); await refresh(user); setNotice(message); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const change = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  return <section className="marketplace">
    <div className="marketplace-intro"><div><h2>Offres des commerces</h2><p>Consultez les offres et réservez des unités disponibles.</p></div><label>Identité de démonstration<select value={user} disabled={busy} onChange={(e) => setUser(e.target.value)}><option value="alice">Alice — étudiante</option><option value="bob">Bob — étudiant</option><option value="shop_demo">Commerce démo</option></select></label></div>
    <p className="marketplace-note">Identités simulées, sans connexion sécurisée. Le serveur ne fournit pas encore de prix ni de coordonnées : prix et distance inconnus.</p>
    {error && <div className="error-banner" role="alert">{error}</div>}{notice && <p className="marketplace-success" role="status">{notice}</p>}
    {business && <section className="panel marketplace-section"><h3>Publier une offre</h3><form className="marketplace-form" onSubmit={(e) => { e.preventDefault(); run(async () => { await donationRequest('/offers', user, { ...form, description: form.description.trim() || null, total_quantity: Number(form.total_quantity), per_person_limit: Number(form.per_person_limit), expires_at: new Date(form.expires_at).toISOString() }); setForm(blank); }, 'Offre publiée.'); }}>
      <label>Titre<input required maxLength="200" value={form.title} onChange={(e) => change('title', e.target.value)} /></label>
      <label>Description<input value={form.description} onChange={(e) => change('description', e.target.value)} /></label>
      <label>Quantité totale<input required type="number" min="1" step="1" value={form.total_quantity} onChange={(e) => change('total_quantity', e.target.value)} /></label>
      <label>Limite par personne<input required type="number" min="1" step="1" max={form.total_quantity} value={form.per_person_limit} onChange={(e) => change('per_person_limit', e.target.value)} /></label>
      <label>Unité (ex. portion)<input required maxLength="200" value={form.unit_label} onChange={(e) => change('unit_label', e.target.value)} /></label>
      <label>Lieu de retrait<input required maxLength="200" value={form.pickup_location} onChange={(e) => change('pickup_location', e.target.value)} /></label>
      <label>Date limite de retrait<input required type="datetime-local" value={form.expires_at} onChange={(e) => change('expires_at', e.target.value)} /></label>
      <button disabled={busy} className="button primary">Publier</button></form></section>}
    <section className="panel marketplace-section"><h3>{business ? 'Mes offres' : 'Offres disponibles'}</h3><button className="button secondary" disabled={busy} onClick={() => run(async () => {}, 'Liste actualisée.')}>Actualiser</button>{offers.length === 0 && <p>Aucune offre disponible.</p>}{offers.map((offer) => <div className="marketplace-proposal" key={offer.offer_id}>
      <strong>{offer.title}</strong><p>{offer.description}</p><p>{statuses[offer.status] ?? offer.status} · {offer.available_quantity} {offer.unit_label}(s) disponibles · limite {offer.per_person_limit} par personne</p><p>Retrait : {offer.pickup_location} · avant le {new Date(offer.expires_at).toLocaleString('fr-CA')}</p><p>Prix : inconnu · Distance : inconnue</p>
      {!business && <form className="marketplace-form" onSubmit={(e) => { e.preventDefault(); run(() => donationRequest(`/offers/${encodeURIComponent(offer.offer_id)}/reservations`, user, { quantity: Number(amounts[offer.offer_id] ?? 1) }), 'Réservation confirmée.'); }}><label>Nombre d’unités<input type="number" min="1" step="1" max={Math.min(offer.available_quantity, offer.per_person_limit)} value={amounts[offer.offer_id] ?? 1} onChange={(e) => setAmounts({ ...amounts, [offer.offer_id]: e.target.value })} required /></label><button className="button primary" disabled={busy || offer.available_quantity < 1}>Réserver</button></form>}
      {business && <div className="marketplace-actions">{offer.status === 'active' && <button className="button secondary" disabled={busy} onClick={() => run(() => donationRequest(`/offers/${encodeURIComponent(offer.offer_id)}/cancel`, user, {}), 'Offre annulée.')}>Annuler l’offre</button>}<button className="button secondary" disabled={busy} onClick={() => run(async () => { const data = await donationRequest(`/offers/${encodeURIComponent(offer.offer_id)}/reservations`, user); setOfferReservations((current) => ({ ...current, [offer.offer_id]: data.reservations })); }, 'Réservations chargées.')}>Voir les réservations</button></div>}
      {business && (offerReservations[offer.offer_id] ?? []).map((reservation) => <p key={reservation.reservation_id}>{reservation.student_id} · {reservation.quantity} · {statuses[reservation.status] ?? reservation.status} {reservation.status === 'reserved' && <button className="text-button" disabled={busy} onClick={() => run(async () => { await donationRequest(`/reservations/${encodeURIComponent(reservation.reservation_id)}/collect`, user, {}); setOfferReservations((current) => ({ ...current, [offer.offer_id]: [] })); }, 'Retrait confirmé.')}>Confirmer le retrait</button>}</p>)}
    </div>)}</section>
    {!business && <section className="panel marketplace-section"><h3>Mes réservations</h3>{reservations.length === 0 && <p>Aucune réservation.</p>}{reservations.map((reservation) => <div className="marketplace-row" key={reservation.reservation_id}><span>Offre {reservation.offer_id} · {reservation.quantity} unité(s) · {statuses[reservation.status] ?? reservation.status}</span>{reservation.status === 'reserved' && <button className="button secondary" disabled={busy} onClick={() => run(() => donationRequest(`/reservations/${encodeURIComponent(reservation.reservation_id)}/cancel`, user, {}), 'Réservation annulée, quantité libérée.')}>Annuler</button>}</div>)}</section>}
  </section>;
}
