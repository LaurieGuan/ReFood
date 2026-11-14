import { mockApi } from './mockApi.js';
import { mockPrices } from './mockPrices.js';

const baseUrl = '/api/v1';
async function request(path, options = {}) {
  let response;
  try { response = await fetch(`${baseUrl}${path}`, options); }
  catch { throw new Error('Impossible de joindre le serveur Flask. Vérifiez qu’il est démarré sur le port 5000.'); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const context = path === '/scans' ? 'L’analyse de la photo' : path.startsWith('/grocery/') ? 'La recherche de produits' : path === '/pantry' ? 'La sauvegarde des ingrédients' : 'La recherche de recettes';
    throw new Error(`${context} a échoué (HTTP ${response.status}) : ${body.error?.message ?? 'erreur du serveur'}.`);
  }
  return body;
}
const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const ingredient = (item) => ({
  ...item, quantity: item.quantity?.amount ?? null, unit: item.quantity?.unit ?? 'unknown',
});
const backendIngredient = (item, useRemaining = false) => ({
  ingredient_id: item.ingredient_id,
  name: item.name,
  quantity: {
    amount: item.quantity == null ? null : item.quantity * (useRemaining ? (item.remaining_fraction ?? 1) : 1),
    unit: item.unit === 'unit' ? 'piece' : (item.unit ?? 'unknown'),
  },
});
const recipeCache = new Map();
function normalizeRecipe(recipe, result) {
  return {
    ...recipe, id: recipe.recipe_id, minutes: recipe.preparation_minutes,
    ingredients: recipe.ingredients.map((item) => ({ ...ingredient(item), essential: true })),
    instructions: recipe.instructions,
    match: {
      coverage: result.match_score, quantity_verified: !result.quantity_uncertain,
      missing_ingredients: result.missing_ingredients.map((item) => ({ ...ingredient(item), essential: true })),
      missing_ingredient_ids: result.missing_ingredients.map((item) => item.ingredient_id),
    },
  };
}
export const flaskApi = {
  baseUrl,
  async scanImage(file) {
    const form = new FormData();
    form.append('image', file);
    const response = await request('/scans', { method: 'POST', body: form });
    return { ...response, candidates: response.candidates.map(ingredient), warnings: [] };
  },
  async savePantry(items) {
    return request('/pantry', json('PUT', { items: items.map((item) => ({
      ...backendIngredient(item), remaining_fraction: item.remaining_fraction ?? null,
    })) }));
  },
  async searchRecipes(items, limit = 100) {
    const response = await request('/recipes/search', json('POST', { ingredients: items.map((item) => backendIngredient(item, true)), limit }));
    const recipes = response.results.map((result) => {
      const value = normalizeRecipe(result.recipe, result);
      recipeCache.set(value.id, value);
      return value;
    });
    return { recipes, total: recipes.length };
  },
  async getRecipe(id) {
    return recipeCache.get(id) ?? (await mockApi.getFavorites()).items.find((item) => item.id === id) ?? mockApi.getRecipe(id);
  },
  async searchGroceryItems(query) {
    return request(`/grocery/products/search?q=${encodeURIComponent(query)}&limit=10`);
  },
  async groceryPrices(ingredients) {
    const responses = await Promise.all(ingredients.map(async (item) => ({ item, data: await this.searchGroceryItems(item.name) })));
    const candidates = responses.flatMap(({ item, data }) => data.results.flatMap((product) => {
      const prices = product.store_prices?.length ? product.store_prices : [{ store: product.cheapest_store, price_cents: product.cheapest_price_cents, size: product.size, retailer_link: product.retailer_link, observed_at: product.updated_at }];
      return prices.filter((price) => price.store && price.price_cents != null).map((price) => ({
        ingredient_id: item.ingredient_id, ingredient_name: item.name, store_id: price.store,
        product_id: product.provider_product_id, product_name: product.name, brand: product.brand,
        package_quantity: price.size ?? product.size, price_cad: price.price_cents / 100,
        currency: 'CAD', merchant: price.store, retailer_link: price.retailer_link ?? product.retailer_link ?? product.provider_url,
        observed_at: price.observed_at ?? product.updated_at, source: data.source,
      }));
    }));
    // Select one observed product per ingredient and retailer for the indicative total.
    const byStoreAndIngredient = new Map();
    for (const offer of candidates) {
      const key = JSON.stringify([offer.store_id, offer.ingredient_id]);
      if (!byStoreAndIngredient.has(key) || offer.price_cad < byStoreAndIngredient.get(key).price_cad) byStoreAndIngredient.set(key, offer);
    }
    const offers = [...byStoreAndIngredient.values()];
    return {
      stores: [...new Set(offers.map((offer) => offer.store_id))].map((name) => ({ id: name, name, address: null, distance_km: null })),
      offers, unpriced_ingredient_ids: ingredients.filter((item) => !offers.some((offer) => offer.ingredient_id === item.ingredient_id)).map((item) => item.ingredient_id),
      missing_ingredients: ingredients, source: 'epiceries.ca', demo: false,
    };
  },
};
const demoApi = {
  ...mockApi,
  async savePantry() {},
  async searchRecipes(items, limit, preferences) { return mockApi.searchRecipes({ ingredient_ids: items.map((item) => item.ingredient_id), limit, preferences }); },
  async groceryPrices(items, location) {
    return { ...await mockPrices.comparePrices({ ingredient_ids: items.map((item) => item.ingredient_id), location }), missing_ingredients: items, demo: true };
  },
};
let storedDemo = false;
try { storedDemo = localStorage.getItem('refood-demo-mode') === 'true'; } catch { /* Storage is optional. */ }
export const isDemoMode = import.meta.env.VITE_REFOOD_DEMO === 'true' || storedDemo;
export const api = isDemoMode ? demoApi : flaskApi;
