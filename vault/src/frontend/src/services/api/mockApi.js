// In-memory mock of the /api/v1 contract. Swap this module for fetch calls when Flask is ready.
const wait = (value, delay = 350) => new Promise((resolve) => setTimeout(() => resolve(structuredClone(value)), delay));
const catalog = [
  { id: 'ing_egg', name: 'egg', display_name: 'Œuf', aliases: ['eggs', 'œufs'] },
  { id: 'ing_tomato', name: 'tomato', display_name: 'Tomate', aliases: ['tomatoes', 'tomates'] },
  { id: 'ing_milk', name: 'milk', display_name: 'Lait', aliases: ['lait'] },
  { id: 'ing_avocado', name: 'avocado', display_name: 'Avocat', aliases: ['avocados', 'avocats'] },
  { id: 'ing_pasta', name: 'pasta', display_name: 'Pâtes', aliases: ['pasta'] },
  { id: 'ing_onion', name: 'onion', display_name: 'Oignon', aliases: ['onions', 'oignons'] },
  { id: 'ing_cheese', name: 'cheese', display_name: 'Fromage', aliases: ['cheese', 'fromage'] },
];
const byId = Object.fromEntries(catalog.map((item) => [item.id, item]));
let pantry = [
  { id: 'pantry_101', ingredient_id: 'ing_egg', name: 'egg', quantity: 6, unit: 'unit', remaining_fraction: 1, source: 'manual' },
  { id: 'pantry_102', ingredient_id: 'ing_tomato', name: 'tomato', quantity: null, unit: 'unknown', remaining_fraction: null, source: 'scan_confirmed' },
  { id: 'pantry_103', ingredient_id: 'ing_milk', name: 'milk', quantity: 1000, unit: 'ml', remaining_fraction: null, source: 'manual' },
  { id: 'pantry_104', ingredient_id: 'ing_avocado', name: 'avocado', quantity: 2, unit: 'unit', remaining_fraction: 1, source: 'manual' },
];
const recipes = [
  { id: 'recipe_omelette', title: 'Omelette aux tomates', source: 'demo', source_url: null, ingredients: [{ ingredient_id: 'ing_egg', name: 'egg', quantity: 2, unit: 'unit', essential: true }, { ingredient_id: 'ing_tomato', name: 'tomato', quantity: 1, unit: 'unit', essential: true }, { ingredient_id: 'ing_cheese', name: 'cheese', quantity: 30, unit: 'g', essential: false }], instructions: 'Battez les œufs. Faites revenir les tomates, ajoutez les œufs puis le fromage et laissez cuire doucement.', minutes: 15, servings: 2, dietary_tags: ['vegetarian'], allergens: ['egg', 'milk'], nutrition: null },
  { id: 'recipe_pasta', title: 'Pâtes crémeuses', source: 'demo', source_url: null, ingredients: [{ ingredient_id: 'ing_pasta', name: 'pasta', quantity: 180, unit: 'g', essential: true }, { ingredient_id: 'ing_milk', name: 'milk', quantity: 100, unit: 'ml', essential: true }, { ingredient_id: 'ing_tomato', name: 'tomato', quantity: 1, unit: 'unit', essential: true }], instructions: 'Faites cuire les pâtes. Chauffez le lait avec les tomates coupées et mélangez avec les pâtes.', minutes: 20, servings: 2, dietary_tags: ['vegetarian'], allergens: ['milk'], nutrition: null },
  { id: 'recipe_avocado_toast', title: 'Tartines avocat & œuf', source: 'demo', source_url: null, ingredients: [{ ingredient_id: 'ing_avocado', name: 'avocado', quantity: 1, unit: 'unit', essential: true }, { ingredient_id: 'ing_egg', name: 'egg', quantity: 1, unit: 'unit', essential: true }, { ingredient_id: 'ing_cheese', name: 'cheese', quantity: 20, unit: 'g', essential: false }], instructions: 'Écrasez l’avocat sur du pain grillé. Ajoutez un œuf cuit et un peu de fromage.', minutes: 10, servings: 1, dietary_tags: ['vegetarian'], allergens: ['egg', 'milk'], nutrition: null },
];
let preferences = { dietary_restrictions: [], excluded_ingredient_ids: [], allergens: [], max_budget_cad: '15.00', max_minutes: null, servings: 2 };
let favorites = [];

function searchMatches(recipe, ids) {
  const required = recipe.ingredients.filter((item) => item.essential);
  const matched = required.filter((item) => ids.includes(item.ingredient_id)).map((item) => item.ingredient_id);
  return { coverage: required.length ? matched.length / required.length : 0, matched_ingredient_ids: [...new Set(matched)], missing_ingredient_ids: required.filter((item) => !ids.includes(item.ingredient_id)).map((item) => item.ingredient_id), quantity_verified: false };
}

export const mockApi = {
  baseUrl: '/api/v1',
  async health() { return wait({ status: 'ok', api_version: 'v1' }); },
  async getPantry() { return wait({ items: pantry }); },
  async replacePantry(body) {
    pantry = body.items.map((item, index) => ({ ...item, id: `pantry_${201 + index}`, ingredient_id: item.ingredient_id ?? catalog.find((known) => known.name === item.name.toLowerCase())?.id ?? null }));
    return wait({ items: pantry });
  },
  async scanImage(file) {
    if (!file) throw new Error('Choisissez une photo avant le scan.');
    // Mirrors multipart/form-data POST /scans; suggestions are deliberately not saved to pantry.
    return wait({ scan_id: `scan_demo_${Date.now()}`, candidates: [
      { candidate_id: 'cand_1', ingredient_id: 'ing_egg', name: 'egg', certainty: 'high', quantity: null, unit: 'unknown' },
      { candidate_id: 'cand_2', ingredient_id: 'ing_tomato', name: 'tomato', certainty: 'medium', quantity: null, unit: 'unknown' },
      { candidate_id: 'cand_3', ingredient_id: 'ing_avocado', name: 'avocado', certainty: 'low', quantity: null, unit: 'unknown' },
    ], warnings: ['Les quantités ne peuvent pas être déduites de la photo. Confirmez chaque aliment.'] }, 1800);
  },
  async searchRecipes(body) {
    const selected = recipes.map((recipe) => ({ id: recipe.id, title: recipe.title, match: searchMatches(recipe, body.ingredient_ids), estimated_missing_cost_cad: null, dietary_verification: 'unknown', minutes: recipe.minutes, image_url: null })).sort((a, b) => b.match.coverage - a.match.coverage).slice(0, body.limit ?? 10);
    return wait({ recipes: selected, total: selected.length });
  },
  async getRecipe(id) { const recipe = recipes.find((item) => item.id === id); if (!recipe) throw new Error('Recette introuvable.'); return wait(recipe); },
  async comparePrices(body) {
    const timestamp = '2026-11-14T15:00:00Z';
    const sampleOffers = {
      ing_pasta: [
        { ingredient_id: 'ing_pasta', product_name: 'Pâtes 500 g', package_quantity: 500, package_unit: 'g', price_cad: '2.29' },
        { ingredient_id: 'ing_pasta', product_name: 'Pâtes 900 g', package_quantity: 900, package_unit: 'g', price_cad: '3.49' },
        { ingredient_id: 'ing_pasta', product_name: 'Pâtes 450 g', package_quantity: 450, package_unit: 'g', price_cad: '2.59' },
      ],
      ing_milk: [
        { ingredient_id: 'ing_milk', product_name: 'Lait 2 L', package_quantity: 2, package_unit: 'L', price_cad: '4.79' },
        { ingredient_id: 'ing_milk', product_name: 'Lait 1 L', package_quantity: 1, package_unit: 'L', price_cad: '2.89' },
        { ingredient_id: 'ing_milk', product_name: 'Lait 2 L', package_quantity: 2, package_unit: 'L', price_cad: '5.09' },
      ],
      ing_cheese: [
        { ingredient_id: 'ing_cheese', product_name: 'Fromage râpé 200 g', package_quantity: 200, package_unit: 'g', price_cad: '4.49' },
        { ingredient_id: 'ing_cheese', product_name: 'Fromage 250 g', package_quantity: 250, package_unit: 'g', price_cad: '5.29' },
        { ingredient_id: 'ing_cheese', product_name: 'Fromage râpé 200 g', package_quantity: 200, package_unit: 'g', price_cad: '4.99' },
      ],
    };
    const merchants = ['Marché du quartier', 'Coop du coin', 'Épicerie Centrale'];
    const offers = body.ingredient_ids.flatMap((id) => (sampleOffers[id] ?? []).map((offer, index) => ({ ...offer, merchant: merchants[index], currency: 'CAD', retrieved_at: timestamp, source: 'demo_catalog', product_url: null })));
    const unpriced_ingredient_ids = body.ingredient_ids.filter((id) => !sampleOffers[id]);
    // Illustrative API response only; the prices are not live store offers.
    return wait({ offers, unpriced_ingredient_ids }, 900);
  },
  async getFavorites() { return wait({ items: favorites.map((id) => { const recipe = recipes.find((item) => item.id === id); return { id: recipe.id, title: recipe.title }; }) }); },
  async favoriteRecipe(id) { if (!recipes.some((item) => item.id === id)) throw new Error('Recette introuvable.'); if (!favorites.includes(id)) favorites.push(id); return wait({ recipe_id: id, favorite: true }); },
  async unfavoriteRecipe(id) { favorites = favorites.filter((favoriteId) => favoriteId !== id); return wait({ recipe_id: id, favorite: false }); },
  async getPreferences() { return wait(preferences); },
  async putPreferences(value) { preferences = value; return wait(preferences); },
  ingredientName(id) { return byId[id]?.display_name ?? 'Ingrédient'; },
  ingredient(value) {
    const query = String(value ?? '').trim().toLocaleLowerCase();
    return byId[query] ?? catalog.find((item) => [item.name, item.display_name, ...item.aliases].some((label) => label.toLocaleLowerCase() === query)) ?? null;
  },
};
