import { canonicalIngredient } from '../../utils/canonicalIngredient.js';

export function confirmedItems(items) {
  const result = new Map();
  for (const item of items.filter(i => i.approved)) {
    const identity = canonicalIngredient(item.editedName);
    if (!identity) throw new Error('Nom invalide');
    const quantity = item.quantityText === '' ? null : Number(item.quantityText);
    if (quantity != null && (!Number.isFinite(quantity) || quantity < 0)) throw new Error('Quantité invalide');
    const next = {...identity, quantity, unit:quantity == null ? 'unknown' : item.unitChoice,
      remaining_fraction:item.remaining_fraction, location:item.location, source:item.source};
    const previous = result.get(identity.ingredient_id);
    if (previous && (previous.quantity !== next.quantity || previous.unit !== next.unit || previous.remaining_fraction !== next.remaining_fraction)) throw new Error('Un ingrédient apparaît plusieurs fois avec des quantités différentes. Corrigez les doublons.');
    result.set(identity.ingredient_id,next);
  }
  return [...result.values()];
}
