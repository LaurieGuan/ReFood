import { useCallback, useEffect, useState } from 'react';
import { mockApi } from '../services/api/mockApi.js';
export function useFavorites() {
  const [saved, setSaved] = useState([]);
  useEffect(() => { mockApi.getFavorites().then(({ items }) => setSaved(items)).catch(() => {}); }, []);
  const toggleSaved = useCallback(async (recipe) => {
    if (saved.some((item) => item.id === recipe.id)) await mockApi.unfavoriteRecipe(recipe.id);
    else await mockApi.favoriteRecipe(recipe.id, recipe);
    setSaved((await mockApi.getFavorites()).items);
  }, [saved]);
  return { saved, setSaved, toggleSaved };
}
