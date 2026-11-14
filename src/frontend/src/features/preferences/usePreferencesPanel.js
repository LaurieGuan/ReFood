import { useEffect, useState } from "react";
import { mockApi } from "../../services/api/mockApi.js";
import { preferencesFromForm } from "./preferencesForm.js";

export function usePreferencesPanel({ preferences, onSave }) {
  const [options, setOptions] = useState(null);
  const [ingredients, setIngredients] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([
      mockApi.getPreferenceOptions(),
      mockApi.getIngredientCatalog(),
    ])
      .then(([choices, catalog]) => {
        if (active) {
          setOptions(choices);
          setIngredients(catalog.items);
        }
      })
      .catch(() => {
        if (active) setError("Impossible de charger les options alimentaires.");
      });
    return () => {
      active = false;
    };
  }, []);

  const submit = (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onSave(preferencesFromForm(form, preferences, options.nutrients));
  };

  return { options, ingredients, error, submit };
}
