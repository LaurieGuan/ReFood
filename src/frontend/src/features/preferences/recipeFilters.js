import { recipeFilterData } from '../../data/recipeFilterData.js';

// Filters are conservative: unknown metadata cannot satisfy an active constraint.
export function matchesPreferences(recipe, preferences = {}) {
  const fixture = recipe.source === 'demo' ? (recipeFilterData[recipe.id] ?? {}) : {};
  const data = { ...fixture, ...recipe, nutrition: recipe.nutrition ?? fixture.nutrition, intolerances: recipe.intolerances ?? fixture.intolerances, estimated_cost_cad: recipe.estimated_cost_cad ?? fixture.estimated_cost_cad };
  const diets = preferences.dietary_restrictions ?? [];
  if (diets.length && (!Array.isArray(data.dietary_tags) || !diets.every((id) => data.dietary_tags.includes(id)))) return false;
  const allergens = preferences.allergens ?? [];
  if (allergens.length && (!Array.isArray(data.allergens) || allergens.some((id) => data.allergens.includes(id)))) return false;
  const intolerances = preferences.intolerances ?? [];
  if (intolerances.length && (!Array.isArray(data.intolerances) || intolerances.some((id) => data.intolerances.includes(id)))) return false;
  const excluded = preferences.excluded_ingredient_ids ?? [];
  if (excluded.length && (!Array.isArray(data.ingredients) || data.ingredients.some((item) => excluded.includes(item.ingredient_id)))) return false;
  if (preferences.max_minutes != null && preferences.max_minutes !== '' && (data.minutes == null || data.minutes > Number(preferences.max_minutes))) return false;
  if (preferences.max_budget_cad != null && preferences.max_budget_cad !== '' && (data.estimated_cost_cad == null || Number(data.estimated_cost_cad) > Number(preferences.max_budget_cad))) return false;
  for (const [id, range] of Object.entries(preferences.nutrition_limits ?? {})) {
    for (const bound of ['min', 'max']) {
      const limit = range?.[bound];
      if (limit == null || limit === '') continue;
      const value = data.nutrition?.[id];
      if (value == null || (bound === 'min' ? value < Number(limit) : value > Number(limit))) return false;
    }
  }
  return true;
}
