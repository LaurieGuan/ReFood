// Illustrative per-serving nutrition and estimated recipe cost for the mock catalog.
// Missing records remain unknown and are excluded when the corresponding filter is active.
export const recipeFilterData = {
  recipe_omelette: { intolerances: ['lactose'], nutrition: { calories: 210, carbs: 5, fat: 14, protein: 16 }, estimated_cost_cad: 4.20 },
  recipe_pasta: { intolerances: ['lactose', 'gluten'], nutrition: { calories: 390, carbs: 69, fat: 6, protein: 15 }, estimated_cost_cad: 5.50 },
  recipe_avocado_toast: { intolerances: ['lactose', 'gluten'], nutrition: { calories: 430, carbs: 30, fat: 29, protein: 15 }, estimated_cost_cad: 5.00 },
};
