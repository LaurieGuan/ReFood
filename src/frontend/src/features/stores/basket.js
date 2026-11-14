export function basketSummary(required, offers, demo = false) {
  const needs = [...new Map(required.map((item) => [item.ingredient_id, item])).values()];
  const selected = new Map();
  for (const offer of offers) {
    if (!needs.some((item) => item.ingredient_id === offer.ingredient_id) ||
        !(demo || offer.relevance_verified === true) ||
        typeof offer.price_cad !== 'number' || !Number.isFinite(offer.price_cad) || offer.price_cad < 0) continue;
    const previous = selected.get(offer.ingredient_id);
    if (!previous || (offer.relevance_score ?? 0) > (previous.relevance_score ?? 0) ||
        ((offer.relevance_score ?? 0) === (previous.relevance_score ?? 0) && offer.price_cad < previous.price_cad)) selected.set(offer.ingredient_id, offer);
  }
  const missing = needs.filter((item) => !selected.has(item.ingredient_id));
  return { offers: [...selected.values()], missing, covered: selected.size, required: needs.length,
    complete: missing.length === 0, total: [...selected.values()].reduce((sum, offer) => sum + offer.price_cad, 0) };
}
export const basketLabel = (basket) => basket.complete ? 'Panier complet · coût indicatif' : 'Panier incomplet · sous-total non comparable à un panier complet';
