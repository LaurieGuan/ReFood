// Mirrors services/normalizer.py until the backend exposes normalization over HTTP.
const groups = {
  egg: 'egg|eggs|oeuf|oeufs', milk: 'milk|lait', tomato: 'tomato|tomatoes|tomate|tomates',
  onion: 'onion|onions|oignon|oignons', garlic: 'garlic|ail',
  potato: 'potato|potatoes|pomme de terre|pommes de terre', spinach: 'spinach|epinards',
  kale: 'kale|chou frise', rice: 'rice|riz', flour: 'flour|farine', salt: 'salt|sel',
  butter: 'butter|beurre', olive_oil: 'olive oil|huile d olive', chicken: 'chicken|poulet',
  chicken_breast: 'chicken breast|chicken breasts|poitrine de poulet',
  green_onion: 'green onion|green onions|scallion|scallions|oignon vert|oignons verts',
  chickpea: 'chickpea|chickpeas|pois chiche|pois chiches', zucchini: 'zucchini|courgette|courgettes',
  cilantro: 'cilantro|coriander leaves|coriandre fraiche', cornstarch: 'cornstarch|corn starch|fecule de mais',
  plain_yogurt: 'plain yogurt|yogourt nature|yaourt nature', sour_cream: 'sour cream|creme sure',
};
const key = (value) => value.toLowerCase().replaceAll('œ', 'oe').normalize('NFKD')
  .replace(/\p{M}/gu, '').replace(/[^\p{L}\p{N}_]+/gu, ' ').trim().replace(/\s+/g, ' ');
const aliases = Object.fromEntries(Object.entries(groups).flatMap(([id, names]) => names.split('|').map((name) => [key(name), id])));

export function canonicalIngredient(name) {
  const cleaned = String(name ?? '').trim();
  const normalized = key(cleaned);
  if (!normalized) return null;
  const canonical = aliases[normalized];
  return {
    ingredient_id: `ing_${canonical ?? normalized.replaceAll(' ', '_')}`,
    name: canonical ? canonical.replaceAll('_', ' ') : cleaned.toLowerCase(),
  };
}
