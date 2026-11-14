import { useState } from "react";

// Shared across the scan, recipe, store comparison, and shopping list steps.
export function useScanSession() {
  const [stage, setStage] = useState(0);
  const [photos, setPhotos] = useState([]);
  const [scan, setScan] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [priceData, setPriceData] = useState(null);
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [selectedStore, setSelectedStore] = useState("");
  return {
    stage,
    setStage,
    photos,
    setPhotos,
    scan,
    setScan,
    suggestions,
    setSuggestions,
    priceData,
    setPriceData,
    selectedRecipe,
    setSelectedRecipe,
    selectedStore,
    setSelectedStore,
  };
}
