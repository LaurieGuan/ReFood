// The mock catalog can be replaced by the preferences API when it is available.
export const preferenceOptions = {
  diets: [
    { id: 'vegan', label: 'Végan' },
    { id: 'vegetarian', label: 'Végétarien' },
    { id: 'keto', label: 'Cétogène' },
    { id: 'halal', label: 'Halal' },
    { id: 'kosher', label: 'Casher' },
  ],
  allergens: [
    { id: 'peanut', label: 'Arachide' }, { id: 'milk', label: 'Lait' },
    { id: 'egg', label: 'Œuf' }, { id: 'wheat', label: 'Blé' },
    { id: 'soy', label: 'Soja' }, { id: 'tree_nut', label: 'Noix' },
    { id: 'fish', label: 'Poisson' }, { id: 'shellfish', label: 'Crustacés' },
    { id: 'sesame', label: 'Sésame' },
  ],
  intolerances: [
    { id: 'lactose', label: 'Lactose' }, { id: 'gluten', label: 'Gluten' },
  ],
  nutrients: [
    { id: 'calories', label: 'Calories', unit: 'kcal' },
    { id: 'carbs', label: 'Glucides', unit: 'g' },
    { id: 'fat', label: 'Lipides', unit: 'g' },
    { id: 'protein', label: 'Protéines', unit: 'g' },
  ],
};
