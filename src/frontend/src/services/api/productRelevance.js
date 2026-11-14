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
  ing_cheese: [11], ing_oil: [33], ing_lean_pork_chops: [20], ing_whole_green_chilies: [1,29],
  ing_flour: [30], ing_olive_oil: [33],
};
const ALIASES = {
  ing_milk: ['lait', 'milk'], ing_egg: ['oeuf', 'oeufs', 'egg', 'eggs'],
  ing_plain_yogurt: ['yogourt', 'yaourt', 'yogurt'],
  ing_sour_cream: ['creme sure', 'sour cream'],
  ing_butter: ['beurre', 'butter'], ing_rice: ['riz', 'rice'],
  ing_pasta: ['pates', 'pasta', 'spaghetti', 'macaroni'],
  ing_chicken: ['poulet', 'chicken'], ing_chicken_breast: ['poitrine de poulet', 'chicken breast'],
  ing_tomato: ['tomate', 'tomates', 'tomato', 'tomatoes'],
  ing_potato: ['pomme de terre', 'pommes de terre', 'potato', 'potatoes', 'patate'],
  ing_onion: ['oignon', 'oignons', 'onion', 'onions'],
  ing_garlic: ['ail', 'garlic'],
  ing_spinach: ['epinard', 'epinards', 'spinach'],
  ing_kale: ['kale', 'chou frise'],
  ing_cheese: ['fromage', 'cheese'], ing_oil: ['huile', 'oil'], ing_lean_pork_chops: ['cotelettes de porc', 'pork chops'], ing_whole_green_chilies: ['piments verts', 'green chilies'],
  ing_flour: ['farine', 'flour'],
  ing_olive_oil: ['huile d olive', 'olive oil'],
};
const clean = (text) => String(text ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replaceAll('œ', 'oe').replace(/[^a-z0-9]+/g, ' ').trim();
const containsPhrase = (name, alias) => (' ' + name + ' ').includes(' ' + clean(alias) + ' ');

export function classifyGroceryProduct(ingredient, product) {
  const category = Number(product.category_id);
  const id = ingredient.ingredient_id;
  const name = clean(product.name);
  let linkText = product.retailer_link ?? product.link ?? "";
  try { linkText = decodeURIComponent(linkText); } catch { /* Provider links may be malformed. */ }
  const evidence = name + " " + clean(linkText);
  if (!name || NON_FOOD.has(category)) return { eligible: false, score: 0, reason: 'non-food or unknown product' };

  if (/\b(savon|soap|shampoo|nettoyant|detergent|lotion)\b/.test(name)) return { eligible: false, score: 0, reason: 'non-food label' };
  if (id === 'ing_milk' && /\b(chocolat|chocolate|bretzel|pretzel|amande|almond|avoine|oat|coconut|soya|evapore|evaporated|condense|condensed|poudre|powder|vanille|vanilla|fraises?|strawberry|frappe|coco|chevre|goat|aromatise|flavoured|flavored|peche|mangue|gateau|shake)\b/.test(evidence)) return { eligible: false, score: 0, reason: 'different ingredient or prepared snack' };
  if (id === 'ing_lean_pork_chops' && /\b(assaisonnees|assaisonne|marinees|marinade|seasoned|breaded|panees)\b/.test(name)) return { eligible: false, score: 0, reason: 'prepared meat needs confirmation' };
  if (id === 'ing_plain_yogurt' && /\b(vanille|vanilla|fraise|strawberry|fruits|sucre|sweetened)\b/.test(name)) return { eligible: false, score: 0, reason: 'flavored yogurt differs from plain' };
  const aliases = ALIASES[id] ?? [ingredient.name];
  const nameMatch = aliases.some((alias) => containsPhrase(name, alias));
  const allowed = CATEGORY_BY_INGREDIENT[id];
  const knownCategory = Number.isInteger(category) && category > 0;
  if (allowed && knownCategory && !allowed.includes(category)) {
    return { eligible: false, score: 0, reason: 'incompatible food category' };
  }
  if (!nameMatch) return { eligible: false, score: 0, reason: 'ingredient not matched in product label' };
  const plainMilkWords = new Set('lait milk partiellement ecreme partially skimmed skim entier whole homogenise homogenized pasteurise pasteurized microfiltre ultrafiltre filtered filtre finement sans lactose free fat low reduced biologique organic bio de vache cow frais fresh l ml litre litres liter liters m g'.split(' '));
  const ambiguous = id === "ing_milk" && !name.split(' ').every(word => /^\d+(?:ml|l)?$/.test(word) || plainMilkWords.has(word));
  const categoryMatch = !!(allowed && allowed.includes(category)) && !ambiguous;
  return {
    eligible: true, verified: categoryMatch, score: categoryMatch ? 0.95 : 0.65,
    reason: categoryMatch ? 'name and category match' : ambiguous ? 'milk label composition needs review' : 'name matches, category needs review',
  };
}

export function groceryQuery(ingredient) {
  return (ALIASES[ingredient.ingredient_id] ?? [ingredient.name])[0];
}

export const groceryCategory = (ingredient) => CATEGORY_BY_INGREDIENT[ingredient.ingredient_id]?.[0];
