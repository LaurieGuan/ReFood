import { useState } from 'react';

// Shared across the scan, recipe, store comparison, and shopping list steps.
export function useScanSession() {
  const [stage, setStage] = useState(0);
  const [photo, setPhoto] = useState(null);
  const [scan, setScan] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [priceData, setPriceData] = useState(null);
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [selectedStore, setSelectedStore] = useState('');
  return { stage, setStage, photo, setPhoto, scan, setScan, suggestions, setSuggestions, priceData, setPriceData, selectedRecipe, setSelectedRecipe, selectedStore, setSelectedStore };
}
