import { isDemoMode } from './apiMode.js';
export { isDemoMode } from './apiMode.js';
import { mockApi } from './mockApi.js';
import { mockPrices } from './mockPrices.js';
import { classifyGroceryProduct, groceryQuery, groceryCategory } from './productRelevance.js';

const baseUrl = '/api/v1';
async function request(path, options = {}) {
  let response;
  try { response = await fetch(`${baseUrl}${path}`, options); }
  catch { throw new Error('Impossible de joindre le serveur Flask. Vérifiez qu’il est démarré sur le port 5000.'); }
  let body;
  try { body = await response.json(); } catch { throw new Error('Réponse Flask invalide : JSON attendu.'); }
  if (!response.ok) {
    const context = path === '/scans' ? 'L’analyse de la photo' : path.startsWith('/grocery/') ? 'La recherche de produits' : path === '/pantry' ? 'La sauvegarde des ingrédients' : 'La recherche de recettes';
    throw new Error(`${context} a échoué (HTTP ${response.status}) : ${body.error?.message ?? 'erreur du serveur'}.`);
  }
  const source = response.headers?.get('X-Refood-Source');
  if ((source && /mock|demo|fixture|sample/i.test(source)) || body.demo === true || /mock|demo|fixture|sample/i.test(body.source ?? '')) {
    throw new Error('Unavailable · Flask a renvoyé des données de démonstration en mode réel.');
  }
  return { ...body, data_source: source ? 'live' : 'unknown', persistence: response.headers?.get('X-Refood-Persistence') ?? null };
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
    ...recipe, data_source: /mock|demo|fixture|sample/i.test(recipe.source ?? '') ? 'demo' : 'live', preferences_evaluated: true, preference_warnings: result.preference_warnings ?? [], id: recipe.recipe_id, minutes: recipe.preparation_minutes,
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
  async searchRecipes(items, limit = 100, preferences = {}) {
    const response = await request('/recipes/search', json('POST', { ingredients: items.map((item) => backendIngredient(item, true)), limit, preferences }));
    const recipes = response.results.map((result) => {
      const value = normalizeRecipe(result.recipe, result);
      if (value.data_source === 'demo') throw new Error('Unavailable · Recette de démonstration reçue en mode réel.');
      value.data_source = response.data_source;
      recipeCache.set(value.id, value);
      return value;
    });
    return { recipes, total: recipes.length };
  },
  async getRecipe(id) {
    const recipe = recipeCache.get(id);
    if (!recipe) throw new Error('Recette absente de la session; relancez la recherche.');
    return recipe;
  },
  async searchGroceryItems(query, category) {
    return request(`/grocery/products/search?q=${encodeURIComponent(query)}&limit=100${category ? `&category=${category}` : ''}`);
  },
  async groceryPrices(ingredients) {
    const responses = [];
    const unverified = [];
    for (const item of ingredients) {
      const data = await this.searchGroceryItems(groceryQuery(item), groceryCategory(item));
      const ranked = data.results.map((product) => ({ product, relevance: classifyGroceryProduct(item, product) }))
        .filter(({ relevance }) => relevance.eligible).sort((a,b) => b.relevance.score - a.relevance.score || (a.product.cheapest_price_cents ?? Infinity) - (b.product.cheapest_price_cents ?? Infinity));
      unverified.push(...ranked.filter(({relevance}) => !relevance.verified).map(({product,relevance}) => ({ingredient_name:item.name, product_name:product.name, reason:relevance.reason})));
      const verified = ranked.filter(({relevance}) => relevance.verified).slice(0, 3);
      const products = [];
      for (const { product, relevance } of verified) {
        const detail = await request(`/grocery/products/${encodeURIComponent(product.provider_product_id)}`);
        if (classifyGroceryProduct(item, detail).verified) products.push({...detail, relevance_score:relevance.score});
      }
      responses.push({item, data:{...data, results:products}});
    }
    const candidates = responses.flatMap(({ item, data }) => data.results.filter((product) => classifyGroceryProduct(item, product).eligible).flatMap((product) => {
      const prices = product.store_prices?.length ? product.store_prices : [{ store: product.cheapest_store, price_cents: product.cheapest_price_cents, size: product.size, retailer_link: product.retailer_link, observed_at: product.updated_at }];
      return prices.filter((price) => price.store && price.price_cents != null && classifyGroceryProduct(item, {...product, retailer_link:price.retailer_link ?? product.retailer_link}).verified).map((price) => ({
        relevance_verified: true, relevance_score: product.relevance_score, ingredient_id: item.ingredient_id, ingredient_name: item.name, store_id: price.store,
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
      if (!byStoreAndIngredient.has(key) || offer.relevance_score > byStoreAndIngredient.get(key).relevance_score || (offer.relevance_score === byStoreAndIngredient.get(key).relevance_score && offer.price_cad < byStoreAndIngredient.get(key).price_cad)) byStoreAndIngredient.set(key, offer);
    }
    const offers = [...byStoreAndIngredient.values()];
    return {
      stores: [...new Set(offers.map((offer) => offer.store_id))].map((name) => ({ id: name, name, address: null, distance_km: null })),
      offers, unpriced_ingredient_ids: ingredients.filter((item) => !offers.some((offer) => offer.ingredient_id === item.ingredient_id)).map((item) => item.ingredient_id),
      missing_ingredients: ingredients, unverified, source: responses[0]?.data.source ?? null, data_source: responses.length && responses.every(({data}) => data.data_source === 'live') ? 'live' : 'unknown', demo: false,
    };
  },
};
const demoApi = {
  ...mockApi,
  async savePantry() { return { data_source: 'demo', persistence: 'session' }; },
  async scanImage(file) { return { ...await mockApi.scanImage(file), data_source: 'demo' }; },
  async getRecipe(id) { return { ...await mockApi.getRecipe(id), data_source: 'demo' }; },
  async searchRecipes(items, limit, preferences) { const response = await mockApi.searchRecipes({ ingredient_ids: items.map((item) => item.ingredient_id), limit, preferences }); return { ...response, data_source: 'demo', recipes: response.recipes.map((recipe) => ({ ...recipe, data_source: 'demo' })) }; },
  async groceryPrices(items, location) {
    return { ...await mockPrices.comparePrices({ ingredient_ids: items.map((item) => item.ingredient_id), location }), missing_ingredients: items, demo: true, data_source: 'demo' };
  },
};
export const api = isDemoMode ? demoApi : flaskApi;
