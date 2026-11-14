import { preferenceOptions } from '../../data/preferenceOptions.js';
import { matchesPreferences } from '../../features/preferences/recipeFilters.js';
// In-memory mock of the /api/v1 contract. Swap this module for fetch calls when Flask is ready.
const wait = (value, delay = 350) => new Promise((resolve) => setTimeout(() => resolve(structuredClone(value)), delay));
const catalog = [
  { id: 'ing_egg', name: 'egg', display_name: 'Œuf', aliases: ['eggs', 'œufs'] },
  { id: 'ing_tomato', name: 'tomato', display_name: 'Tomate', aliases: ['tomatoes', 'tomates'] },
  { id: 'ing_milk', name: 'milk', display_name: 'Lait', aliases: ['lait'] },
  { id: 'ing_avocado', name: 'avocado', display_name: 'Avocat', aliases: ['avocados', 'avocats'] },
  { id: 'ing_pasta', name: 'pasta', display_name: 'Pâtes', aliases: ['pasta'] },
  { id: 'ing_bread', name: 'bread', display_name: 'Pain', aliases: ['pain'] },
  { id: 'ing_onion', name: 'onion', display_name: 'Oignon', aliases: ['onions', 'oignons'] },
  { id: 'ing_cheese', name: 'cheese', display_name: 'Fromage', aliases: ['cheese', 'fromage'] },
];
try {
  const customIngredients = JSON.parse(localStorage.getItem('refood-ingredients') || '[]');
  if (Array.isArray(customIngredients)) catalog.push(...customIngredients);
} catch { /* Storage is optional. */ }
const byId = Object.fromEntries(catalog.map((item) => [item.id, item]));
let recipes = [
  { id: 'recipe_omelette', title: 'Omelette aux tomates', source: 'demo', source_url: null, ingredients: [{ ingredient_id: 'ing_egg', name: 'egg', quantity: 2, unit: 'unit', essential: true }, { ingredient_id: 'ing_tomato', name: 'tomato', quantity: 1, unit: 'unit', essential: true }, { ingredient_id: 'ing_cheese', name: 'cheese', quantity: 30, unit: 'g', essential: false }], instructions: 'Battez les œufs. Faites revenir les tomates, ajoutez les œufs puis le fromage et laissez cuire doucement.', minutes: 15, servings: 2, dietary_tags: ['vegetarian'], allergens: ['egg', 'milk'], nutrition: null },
  { id: 'recipe_pasta', title: 'Pâtes crémeuses', source: 'demo', source_url: null, ingredients: [{ ingredient_id: 'ing_pasta', name: 'pasta', quantity: 180, unit: 'g', essential: true }, { ingredient_id: 'ing_milk', name: 'milk', quantity: 100, unit: 'ml', essential: true }, { ingredient_id: 'ing_tomato', name: 'tomato', quantity: 1, unit: 'unit', essential: true }], instructions: 'Faites cuire les pâtes. Chauffez le lait avec les tomates coupées et mélangez avec les pâtes.', minutes: 20, servings: 2, dietary_tags: ['vegetarian'], allergens: ['milk', 'wheat'], nutrition: null },
  { id: 'recipe_avocado_toast', title: 'Tartines avocat & œuf', source: 'demo', source_url: null, ingredients: [{ ingredient_id: 'ing_bread', name: 'bread', quantity: 2, unit: 'unit', essential: true }, { ingredient_id: 'ing_avocado', name: 'avocado', quantity: 1, unit: 'unit', essential: true }, { ingredient_id: 'ing_egg', name: 'egg', quantity: 1, unit: 'unit', essential: true }, { ingredient_id: 'ing_cheese', name: 'cheese', quantity: 20, unit: 'g', essential: false }], instructions: 'Écrasez l’avocat sur du pain grillé. Ajoutez un œuf cuit et un peu de fromage.', minutes: 10, servings: 1, dietary_tags: ['vegetarian'], allergens: ['egg', 'milk', 'wheat'], nutrition: null },
];
let preferences = { dietary_restrictions: [], excluded_ingredient_ids: [], allergens: [], intolerances: [], nutrition_limits: {}, max_budget_cad: null, max_minutes: null, servings: 2 };
try { preferences = { ...preferences, ...JSON.parse(localStorage.getItem('refood-preferences') || '{}') }; } catch { /* Storage is optional. */ }
let favorites = [];
// Persist user-created recipes and saved selections in the mock service.
try {
  const stored = JSON.parse(localStorage.getItem('refood-recipes') || 'null');
  if (Array.isArray(stored?.recipes)) recipes = stored.recipes;
  if (Array.isArray(stored?.favorites)) favorites = stored.favorites;
} catch { /* Storage is optional in the mock environment. */ }
function persistRecipes() {
  try { localStorage.setItem('refood-recipes', JSON.stringify({ recipes, favorites })); } catch { /* Keep the in-memory session usable. */ }
}


function searchMatches(recipe, ids) {
  const required = recipe.ingredients.filter((item) => item.essential);
  const matched = required.filter((item) => ids.includes(item.ingredient_id)).map((item) => item.ingredient_id);
  return { coverage: required.length ? matched.length / required.length : 0, matched_ingredient_ids: [...new Set(matched)], missing_ingredient_ids: required.filter((item) => !ids.includes(item.ingredient_id)).map((item) => item.ingredient_id), quantity_verified: false };
}

export const mockApi = {
  baseUrl: '/api/v1',
  async health() { return wait({ status: 'ok', api_version: 'v1' }); },
  async scanImage(file) {
    if (!file) throw new Error('Choisissez une photo avant le scan.');
    // Mirrors multipart/form-data POST /scans; suggestions remain in the current scan session.
    return wait({ scan_id: `scan_demo_${Date.now()}`, candidates: [
      { candidate_id: 'cand_1', ingredient_id: 'ing_egg', name: 'egg', certainty: 'high', quantity: null, unit: 'unknown' },
      { candidate_id: 'cand_2', ingredient_id: 'ing_tomato', name: 'tomato', certainty: 'medium', quantity: null, unit: 'unknown' },
      { candidate_id: 'cand_3', ingredient_id: 'ing_avocado', name: 'avocado', certainty: 'low', quantity: null, unit: 'unknown' },
    ], warnings: ['Les quantités ne peuvent pas être déduites de la photo. Confirmez chaque aliment.'] }, 1800);
  },
  async searchRecipes(body) {
    const selected = recipes.filter((recipe) => matchesPreferences(recipe, body.preferences)).map((recipe) => ({ id: recipe.id, title: recipe.title, match: searchMatches(recipe, body.ingredient_ids), estimated_missing_cost_cad: null, dietary_verification: 'unknown', minutes: recipe.minutes, image_url: null })).sort((a, b) => b.match.coverage - a.match.coverage).slice(0, body.limit ?? 10);
    return wait({ recipes: selected, total: selected.length });
  },
  async getRecipe(id) { const recipe = recipes.find((item) => item.id === id); if (!recipe) throw new Error('Recette introuvable.'); return wait(recipe); },
  async listRecipes() { return wait({ items: recipes }); },
  async createRecipe(value) {
    const recipe = { ...value, id: `recipe_${crypto.randomUUID()}`, source: 'personal', source_url: null };
    recipes.push(recipe); persistRecipes(); return wait(recipe);
  },
  async updateRecipe(id, value) {
    const index = recipes.findIndex((item) => item.id === id);
    if (index < 0) throw new Error('Recette introuvable.');
    recipes[index] = { ...recipes[index], ...value, id, source: 'personal' }; persistRecipes(); return wait(recipes[index]);
  },
  async deleteRecipe(id) {
    if (!recipes.some((item) => item.id === id)) throw new Error('Recette introuvable.');
    recipes = recipes.filter((item) => item.id !== id); favorites = favorites.filter((item) => item !== id);
    persistRecipes(); return wait({ deleted: true });
  },
  async getFavorites() { return wait({ items: favorites.map((id) => recipes.find((item) => item.id === id)).filter(Boolean) }); },
  async favoriteRecipe(id) { if (!recipes.some((item) => item.id === id)) throw new Error('Recette introuvable.'); if (!favorites.includes(id)) favorites.push(id); persistRecipes(); return wait({ recipe_id: id, favorite: true }); },
  async unfavoriteRecipe(id) { favorites = favorites.filter((favoriteId) => favoriteId !== id); persistRecipes(); return wait({ recipe_id: id, favorite: false }); },
  async getPreferenceOptions() { return wait(preferenceOptions); },
  async getIngredientCatalog() { return wait({ items: catalog }); },
  async createIngredient(name) {
    const clean = String(name).trim();
    if (!clean) throw new Error('Saisissez un nom d’ingrédient.');
    const existing = catalog.find((item) => [item.name, item.display_name, ...item.aliases].some((value) => value.toLocaleLowerCase() === clean.toLocaleLowerCase()));
    if (existing) return wait(existing);
    const item = { id: `ing_${crypto.randomUUID()}`, name: clean, display_name: clean, aliases: [], custom: true };
    catalog.push(item); byId[item.id] = item;
    try { localStorage.setItem('refood-ingredients', JSON.stringify(catalog.filter((entry) => entry.custom))); } catch { /* Keep the in-memory session usable. */ }
    return wait(item);
  },
  async getPreferences() { return wait(preferences); },
  async putPreferences(value) { preferences = value; try { localStorage.setItem('refood-preferences', JSON.stringify(value)); } catch { /* Keep the in-memory session usable. */ } return wait(preferences); },
  ingredientName(id) { return byId[id]?.display_name ?? 'Ingrédient'; },
  ingredient(value) {
    const query = String(value ?? '').trim().toLocaleLowerCase();
    return byId[query] ?? catalog.find((item) => [item.name, item.display_name, ...item.aliases].some((label) => label.toLocaleLowerCase() === query)) ?? null;
  },
};
