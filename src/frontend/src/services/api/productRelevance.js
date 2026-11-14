// Deterministic, inspectable ingredient-to-product classifier for grocery search.
// It is a conservative filter, not proof that a product is the correct SKU.
// Category IDs come from the Épiceries.ca categories capture (2026-11-14).
const NON_FOOD = new Set([65, 66, 67, 68, 69, 70, 71]);
const CATEGORY_BY_INGREDIENT = {
  ing_milk: [7, 15], ing_egg: [9], ing_plain_yogurt: [12],
  ing_sour_cream: [14], ing_butter: [10], ing_rice: [26],
  ing_pasta: [25], ing_chicken: [16, 54], ing_chicken_breast: [16, 54],
  ing_tomato: [1, 5, 29, 53], ing_potato: [1, 5, 53],
  ing_onion: [1, 5, 53], ing_garlic: [1, 4, 35],
  ing_spinach: [1, 3, 5, 53], ing_kale: [1, 3, 5, 53],
  ing_flour: [30], ing_olive_oil: [33],
};
const ALIASES = {
  ing_milk: ['lait', 'milk'], ing_egg: ['oeuf', 'oeufs', 'egg', 'eggs'],
  ing_plain_yogurt: ['yogourt', 'yaourt', 'yogurt'],
  ing_sour_cream: ['creme sure', 'sour cream'],
  ing_butter: ['beurre', 'butter'], ing_rice: ['riz', 'rice'],
  ing_pasta: ['pates', 'pasta', 'spaghetti', 'macaroni'],
  ing_chicken: ['poulet', 'chicken', 'dinde'], ing_chicken_breast: ['poitrine de poulet', 'chicken breast'],
  ing_tomato: ['tomate', 'tomates', 'tomato', 'tomatoes'],
  ing_potato: ['pomme de terre', 'pommes de terre', 'potato', 'potatoes', 'patate'],
  ing_onion: ['oignon', 'oignons', 'onion', 'onions'],
  ing_garlic: ['ail', 'garlic'],
  ing_spinach: ['epinard', 'epinards', 'spinach'],
  ing_kale: ['kale', 'chou frise'],
  ing_flour: ['farine', 'flour'],
  ing_olive_oil: ['huile d olive', 'olive oil'],
};
const clean = (text) => String(text ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
const containsPhrase = (name, alias) => (' ' + name + ' ').includes(' ' + clean(alias) + ' ');

export function classifyGroceryProduct(ingredient, product) {
  const category = Number(product.category_id);
  const id = ingredient.ingredient_id;
  const name = clean(product.name);
  if (!name || NON_FOOD.has(category)) return { eligible: false, score: 0, reason: 'non-food or unknown product' };

  const aliases = ALIASES[id] ?? [ingredient.name];
  const nameMatch = aliases.some((alias) => containsPhrase(name, alias));
  const allowed = CATEGORY_BY_INGREDIENT[id];
  const knownCategory = Number.isInteger(category) && category > 0;
  if (allowed && knownCategory && !allowed.includes(category)) {
    return { eligible: false, score: 0, reason: 'incompatible food category' };
  }
  if (!nameMatch) return { eligible: false, score: 0, reason: 'ingredient not matched in product label' };
  const categoryMatch = !!(allowed && allowed.includes(category));
  return {
    eligible: true, score: categoryMatch ? 0.95 : 0.65,
    reason: categoryMatch ? 'name and category match' : 'name matches, category needs review',
  };
}
