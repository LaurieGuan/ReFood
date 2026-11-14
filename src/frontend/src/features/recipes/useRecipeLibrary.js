import { isDemoMode } from '../../services/api/apiMode.js';
import { useEffect, useState } from "react";
import { mockApi } from "../../services/api/mockApi.js";

const blank = () => ({
  title: "",
  instructions: "",
  minutes: "",
  servings: "",
  ingredients: [
    { ingredient_id: "", quantity: "", unit: "unit", essential: true },
  ],
  dietary_tags: [],
  allergens: null,
  intolerances: null,
  nutrition: {},
  estimated_cost_cad: "",
});

export function useRecipeLibrary({ saved, onChanged }) {
  const [items, setItems] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [options, setOptions] = useState(null);
  const [editor, setEditor] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [onlyFavorites, setOnlyFavorites] = useState(false);
  const refresh = async () => {
    const response = await mockApi.listRecipes({ includeSamples: isDemoMode });
    setItems(response.items);
    await onChanged?.();
  };
  useEffect(() => {
    let alive = true;
    Promise.all([
      mockApi.listRecipes({ includeSamples: isDemoMode }),
      mockApi.getIngredientCatalog(),
      mockApi.getPreferenceOptions(),
    ])
      .then(([recipes, ingredients, preferences]) => {
        if (alive) {
          setItems(recipes.items);
          setCatalog(ingredients.items ?? ingredients);
          setOptions(preferences);
        }
      })
      .catch((e) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, []);
  const edit = (recipe) =>
    setEditor(
      recipe
        ? {
            ...recipe,
            minutes: recipe.minutes ?? "",
            servings: recipe.servings ?? "",
            estimated_cost_cad: recipe.estimated_cost_cad ?? "",
            dietary_tags: recipe.dietary_tags ?? [],
            allergens: recipe.allergens ?? null,
            intolerances: recipe.intolerances ?? null,
            nutrition: recipe.nutrition ?? {},
            ingredients: recipe.ingredients.map((item) => ({
              ...item,
              quantity: item.quantity ?? "",
            })),
          }
        : blank(),
    );
  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (editor.ingredients.some((item) => !item.ingredient_id)) {
      setError("Choisissez un ingrédient pour chaque ligne.");
      return;
    }
    const value = {
      ...editor,
      title: editor.title.trim(),
      instructions: editor.instructions.trim(),
      minutes: editor.minutes === "" ? null : Number(editor.minutes),
      servings: editor.servings === "" ? null : Number(editor.servings),
      estimated_cost_cad:
        editor.estimated_cost_cad === ""
          ? null
          : Number(editor.estimated_cost_cad),
      nutrition: Object.fromEntries(
        Object.entries(editor.nutrition)
          .filter(([, value]) => value !== "")
          .map(([key, value]) => [key, Number(value)]),
      ),
      ingredients: editor.ingredients.map((item) => ({
        ...item,
        name:
          catalog.find((entry) => entry.id === item.ingredient_id)?.name ??
          item.name,
        quantity: item.quantity === "" ? null : Number(item.quantity),
      })),
    };
    setBusy(true);
    try {
      if (editor.id) await mockApi.updateRecipe(editor.id, value);
      else await mockApi.createRecipe(value);
      setEditor(null);
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const addIngredient = async () => {
    const name = window.prompt("Nom du nouvel ingrédient");
    if (!name?.trim()) return;
    try {
      const item = await mockApi.createIngredient(name);
      setCatalog((current) =>
        current.some((entry) => entry.id === item.id)
          ? current
          : [...current, item],
      );
      setEditor((current) => ({
        ...current,
        ingredients: [
          ...current.ingredients,
          {
            ingredient_id: item.id,
            quantity: "",
            unit: "unit",
            essential: true,
          },
        ],
      }));
    } catch (e) {
      setError(e.message);
    }
  };
  const remove = async (recipe) => {
    if (!window.confirm(`Supprimer « ${recipe.title} » ?`)) return;
    setBusy(true);
    setError("");
    try {
      await mockApi.deleteRecipe(recipe.id);
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const allItems = [...items, ...saved.filter((favorite) => !items.some((item) => item.id === favorite.id))];
  const visible = onlyFavorites ? allItems.filter((item) => saved.some((favorite) => favorite.id === item.id)) : allItems;
  const changeIngredient = (index, patch) =>
    setEditor({
      ...editor,
      ingredients: editor.ingredients.map((item, i) =>
        i === index ? { ...item, ...patch } : item,
      ),
    });
  return {
    items,
    catalog,
    options,
    editor,
    setEditor,
    error,
    setError,
    busy,
    onlyFavorites,
    setOnlyFavorites,
    edit,
    submit,
    addIngredient,
    remove,
    visible,
    changeIngredient,
  };
}
