// Illustrative store and product data returned by the mock price service.
export const stores = [
  { id: 'marche_quartier', name: 'Marché du quartier', address: '100 Rue Sainte-Catherine O, Montréal, QC', latitude: 45.5067, longitude: -73.5673 },
  { id: 'coop_coin', name: 'Coop du coin', address: '200 Avenue du Mont-Royal E, Montréal, QC', latitude: 45.5232, longitude: -73.5855 },
  { id: 'epicerie_centrale', name: 'Épicerie Centrale', address: '300 Rue Saint-Paul O, Montréal, QC', latitude: 45.5012, longitude: -73.5550 },
];
export const products = [
  { ingredient_id: 'ing_pasta', store_id: 'marche_quartier', product_name: 'Pâtes 500 g', package_quantity: 500, package_unit: 'g', price_cad: '2.29' },
  { ingredient_id: 'ing_pasta', store_id: 'coop_coin', product_name: 'Pâtes 900 g', package_quantity: 900, package_unit: 'g', price_cad: '3.49' },
  { ingredient_id: 'ing_pasta', store_id: 'epicerie_centrale', product_name: 'Pâtes 450 g', package_quantity: 450, package_unit: 'g', price_cad: '2.59' },
  { ingredient_id: 'ing_milk', store_id: 'marche_quartier', product_name: 'Lait 2 L', package_quantity: 2, package_unit: 'L', price_cad: '4.79' },
  { ingredient_id: 'ing_milk', store_id: 'coop_coin', product_name: 'Lait 1 L', package_quantity: 1, package_unit: 'L', price_cad: '2.89' },
  { ingredient_id: 'ing_milk', store_id: 'epicerie_centrale', product_name: 'Lait 2 L', package_quantity: 2, package_unit: 'L', price_cad: '5.09' },
  { ingredient_id: 'ing_cheese', store_id: 'marche_quartier', product_name: 'Fromage râpé 200 g', package_quantity: 200, package_unit: 'g', price_cad: '4.49' },
  { ingredient_id: 'ing_cheese', store_id: 'coop_coin', product_name: 'Fromage 250 g', package_quantity: 250, package_unit: 'g', price_cad: '5.29' },
  { ingredient_id: 'ing_cheese', store_id: 'epicerie_centrale', product_name: 'Fromage râpé 200 g', package_quantity: 200, package_unit: 'g', price_cad: '4.99' },
];
