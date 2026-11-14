import { useMemo, useState } from "react";
import { useScanSession } from "../hooks/useScanSession.js";
import { useFavorites } from "../hooks/useFavorites.js";
import { usePreferences } from "../hooks/usePreferences.js";
import { api, isDemoMode } from "../services/api/flaskApi.js";
import { mockApi } from "../services/api/mockApi.js";
import { matchesPreferences } from "../features/preferences/recipeFilters.js";
import { label } from "../utils/ingredients.js";

export function useAppController() {
  const [showLogin, setShowLogin] = useState(true);
  const [screen, setScreen] = useState("scan");
  const [location, setLocation] = useState(null);
  const [origin, setOrigin] = useState("");
  const {
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
  } = useScanSession();
  const { saved, setSaved, toggleSaved: toggleFavorite } = useFavorites();
  const { preferences, setPreferences, preferencesSaved, setPreferencesSaved } =
    usePreferences();
  const [activeRecipe, setActiveRecipe] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  const ingredientIds = useMemo(
    () =>
      scan?.confirmedItems
        ?.filter((item) => item.remaining_fraction !== 0)
        .map((item) => item.ingredient_id)
        .filter(Boolean) ?? [],
    [scan],
  );

  const say = (text) => {
    setToast(text);
    window.setTimeout(() => setToast(""), 2300);
  };
  const runScan = async (event) => {
    event.preventDefault();
    if (!photos.length) {
      setError("Choisissez une photo pour démarrer le scan.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const responses = await Promise.all(
        photos.map((photo) => api.scanImage(photo)),
      );
      const uniqueCandidates = new Map();
      for (const candidate of responses.flatMap(
        (response) => response.candidates,
      )) {
        const key = candidate.ingredient_id ?? candidate.name.toLowerCase();
        if (!uniqueCandidates.has(key)) uniqueCandidates.set(key, candidate);
      }
      setScan({
        scan_id: responses.map((response) => response.scan_id).join("_"),
        candidates: [...uniqueCandidates.values()],
        warnings: [
          ...new Set(responses.flatMap((response) => response.warnings)),
        ],
      });
      setStage(1);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  const getRecipes = async (confirmedItems) => {
    setLoading(true);
    setError("");
    try {
      await api.savePantry(confirmedItems);
      const response = await api.searchRecipes(
        confirmedItems.filter((item) => item.remaining_fraction !== 0), 100, preferences ?? {},
      );
      setScan({ ...scan, confirmedItems });
      setSuggestions(isDemoMode ? response.recipes : response.recipes.filter((recipe) => matchesPreferences(recipe, preferences ?? {})));
      setStage(2);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  const openRecipe = async (id) => {
    setLoading(true);
    setError("");
    try {
      setActiveRecipe(await api.getRecipe(id));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  const chooseRecipe = async (recipe) => {
    setActiveRecipe(null);
    setScreen("scan");
    setPriceData(null);
    setSelectedStore("");
    setStage(3);
    setLoading(true);
    setError("");
    let selected = recipe;
    try {
      if (!isDemoMode && recipe.recipe_id && screen !== "scan") {
        const confirmed = scan?.confirmedItems?.filter((item) => item.remaining_fraction !== 0) ?? [];
        const refreshed = await api.searchRecipes(confirmed, 100);
        selected = refreshed.recipes.find((item) => item.id === recipe.id) ?? { ...recipe, match: { ...recipe.match, missing_ingredients: recipe.ingredients } };
      }
      setSelectedRecipe(selected);
      const missing = selected.match?.missing_ingredients ?? selected.ingredients.filter((item) => item.essential && !ingredientIds.includes(item.ingredient_id));
      const response = await api.groceryPrices(missing, location);
      setPriceData(response);
      const store = response.stores.find((entry) =>
        response.offers.some((offer) => offer.store_id === entry.id),
      );
      if (store) setSelectedStore(store.id);
    } catch (e) {
      setError(e.message);
      const missing = selected.match?.missing_ingredients ?? selected.ingredients.filter((item) => item.essential && !ingredientIds.includes(item.ingredient_id));
      setSelectedRecipe(selected);
      setPriceData({ stores: [], offers: [], unpriced_ingredient_ids: missing.map((item) => item.ingredient_id), missing_ingredients: missing, demo: isDemoMode });
    } finally {
      setLoading(false);
    }
  };
  const exportList = () => {
    if (!selectedRecipe) return;
    const missing = selectedRecipe.match?.missing_ingredients ?? selectedRecipe.ingredients.filter(
      (item) => item.essential && !ingredientIds.includes(item.ingredient_id),
    );
    const offers =
      priceData?.offers.filter((offer) => offer.store_id === selectedStore) ??
      [];
    const store = priceData?.stores.find((item) => item.id === selectedStore);
    const route = store?.address
      ? `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(store.address)}${origin.trim() ? `&origin=${encodeURIComponent(origin.trim())}` : ""}`
      : null;
    const lines = [
      `REFOOD — Liste de courses`,
      `Recette : ${selectedRecipe.title}`,
      `Magasin : ${priceData?.stores.find((store) => store.id === selectedStore)?.name || "Non sélectionné"}`,
      priceData?.demo ? "Données de démonstration — prix non actuels" : "Prix observés : disponibilité et correspondance à vérifier",
      "",
      "À acheter:",
      ...missing.map((item) => {
        const offer = offers.find(
          (x) => x.ingredient_id === item.ingredient_id,
        );
        return `- ${label(item.name)}${offer ? ` — ${offer.product_name} (${offer.price_cad} $ ${offer.currency})` : " — prix inconnu"}`;
      }),
      ...(route ? ["", `Itinéraire : ${route}`] : []),
    ];
    const blob = new Blob([lines.join("\n")], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "refood-liste-de-courses.txt";
    link.click();
    URL.revokeObjectURL(url);
    say("Votre liste de courses a été exportée.");
  };
  const toggleSaved = async (recipe) => {
    setLoading(true);
    setError("");
    try {
      const wasSaved = saved.some((item) => item.id === recipe.id);
      await toggleFavorite(recipe);
      say(wasSaved ? "Recette retirée des favoris." : "Recette enregistrée sur cet appareil.");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  const savePreferences = async (next) => {
    setLoading(true);
    setError("");
    try {
      setPreferences(await mockApi.putPreferences(next));
      setPreferencesSaved(true);
      say("Préférences gardées sur cet appareil.");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  const resetScan = () => {
    setPhotos([]);
    setScan(null);
    setSuggestions([]);
    setPriceData(null);
    setSelectedRecipe(null);
    setSelectedStore("");
    setStage(0);
    setError("");
  };
  const addPhotos = (files) => {
    setPhotos((current) => {
      const existing = new Set(
        current.map((file) => `${file.name}:${file.size}:${file.lastModified}`),
      );
      return [
        ...current,
        ...files.filter((file) => {
          const key = `${file.name}:${file.size}:${file.lastModified}`;
          if (existing.has(key)) return false;
          existing.add(key);
          return true;
        }),
      ];
    });
    setError("");
  };
  const removePhoto = (index) =>
    setPhotos((current) =>
      current.filter((_, itemIndex) => itemIndex !== index),
    );
  const goToPreviousStep = () => {
    if (stage === 3 && !scan?.candidates) {
      setScreen("saved");
      return;
    }
    setStage((current) => Math.max(0, current - 1));
  };

  const locateStores = async () => {
    if (!navigator.geolocation) {
      setError("La géolocalisation n’est pas disponible.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        const next = { latitude: coords.latitude, longitude: coords.longitude };
        setLocation(next);
        try {
          const missing = selectedRecipe.match?.missing_ingredients ?? selectedRecipe.ingredients.filter((item) => item.essential && !ingredientIds.includes(item.ingredient_id));
          setPriceData(await api.groceryPrices(missing, next));
        } catch (e) { setError(e.message); }
      },
      () => setError("Impossible d’obtenir votre position."),
    );
  };

  const stageTitles = [
    "Qu’y a-t-il dans votre cuisine ?",
    "Vérifiez les ingrédients",
    "Vos recettes",
    "Comparer les magasins",
    "Votre liste à emporter",
  ];
  const stageSubtitles = [
    "Ajoutez une photo, puis confirmez les propositions avant de chercher des recettes.",
    "Gardez les bons ingrédients, corrigez les autres ou ajoutez ce qui manque.",
    "Des idées à partir des ingrédients que vous avez confirmés.",
    "Comparez les offres indicatives pour les ingrédients manquants.",
    "Votre liste est prête à télécharger ou à ouvrir dans Maps.",
  ];
  const title =
    screen === "scan"
      ? stageTitles[stage]
      : { saved: "Mes recettes", preferences: "Préférences alimentaires" }[
          screen
        ];
  const subtitle =
    screen === "scan"
      ? stageSubtitles[stage]
      : {
          saved: "Créez, modifiez et retrouvez vos recettes et favoris.",
          preferences: "Indiquez vos préférences pour guider les suggestions.",
        }[screen];

  return {
    showLogin,
    setShowLogin,
    screen,
    setScreen,
    origin,
    setOrigin,
    stage,
    setStage,
    photos,
    addPhotos,
    removePhoto,
    scan,
    suggestions,
    priceData,
    selectedRecipe,
    selectedStore,
    setSelectedStore,
    saved,
    setSaved,
    preferences,
    preferencesSaved,
    loading,
    error,
    setError,
    toast,
    ingredientIds,
    runScan,
    getRecipes,
    openRecipe,
    chooseRecipe,
    exportList,
    toggleSaved,
    savePreferences,
    resetScan,
    goToPreviousStep,
    activeRecipe,
    setActiveRecipe,
    title,
    subtitle,
    locateStores,
  };
}
