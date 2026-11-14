import { stores, products } from '../../data/stores.js';

const distanceKm = (a, b) => {
  const rad = (degrees) => degrees * Math.PI / 180;
  const dLat = rad(b.latitude - a.latitude), dLon = rad(b.longitude - a.longitude);
  const value = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.latitude)) * Math.cos(rad(b.latitude)) * Math.sin(dLon / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(1 - value));
};
export const mockPrices = {
  async comparePrices({ ingredient_ids, location }) {
    const listedStores = stores.map((store) => ({ ...store, distance_km: location ? distanceKm(location, store) : null })).sort((a, b) => (a.distance_km ?? 0) - (b.distance_km ?? 0));
    const offers = products.filter((product) => ingredient_ids.includes(product.ingredient_id)).map((product) => ({ ...product, merchant: stores.find((store) => store.id === product.store_id).name, currency: 'CAD', source: 'demo_catalog' }));
    return { stores: listedStores, offers, unpriced_ingredient_ids: ingredient_ids.filter((id) => !offers.some((offer) => offer.ingredient_id === id)) };
  },
};
