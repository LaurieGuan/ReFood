import { RecipeGrid } from "./RecipeGrid.jsx";
import "./recipeLibrary.css";
import { AlertBanner } from "../../components/AlertBanner.jsx";
import { RecipeIngredientRow } from "./RecipeIngredientRow.jsx";
import { NutritionInputs } from "./NutritionInputs.jsx";
import { useRecipeLibrary } from "./useRecipeLibrary.js";

export function RecipeLibrary({ saved, onOpen, onToggle, onChanged }) {
  const {
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
  } = useRecipeLibrary({ saved, onChanged });
  return (
    <div className="recipe-library">
      {error && (
        <AlertBanner onDismiss={() => setError("")}>{error}</AlertBanner>
      )}
      <div className="results-bar">
        <span>
          {visible.length} recette{visible.length === 1 ? "" : "s"}
        </span>
        <div className="library-actions">
          <label>
            <input
              type="checkbox"
              checked={onlyFavorites}
              onChange={(e) => setOnlyFavorites(e.target.checked)}
            />{" "}
            Favoris seulement
          </label>
          <button className="button primary" onClick={() => edit(null)}>
            ＋ Créer une recette
          </button>
        </div>
      </div>
      {visible.length ? (
        <div className="library-list">
          {visible.map((recipe) => (
            <div key={recipe.id}>
              <RecipeGrid
                recipes={[recipe]}
                saved={saved}
                onOpen={onOpen}
                onToggle={onToggle}
              />
              <div className="library-card-actions">
                <button className="text-button" onClick={() => edit(recipe)}>
                  Modifier
                </button>
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => remove(recipe)}
                >
                  Supprimer
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="panel empty-saved">
          <h2>Aucune recette à afficher</h2>
          <p>Créez une recette ou modifiez votre sélection.</p>
        </div>
      )}
      {editor && (
        <div className="modal-backdrop" onClick={() => setEditor(null)}>
          <section
            className="recipe-modal recipe-editor"
            role="dialog"
            aria-modal="true"
            aria-label={editor.id ? "Modifier la recette" : "Créer une recette"}
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="modal-close"
              type="button"
              onClick={() => setEditor(null)}
              aria-label="Fermer"
            >
              ×
            </button>
            <h2>{editor.id ? "Modifier la recette" : "Créer une recette"}</h2>
            <form onSubmit={submit}>
              <label>
                Nom
                <input
                  required
                  value={editor.title}
                  onChange={(e) =>
                    setEditor({ ...editor, title: e.target.value })
                  }
                />
              </label>
              <label>
                Préparation
                <textarea
                  required
                  rows="4"
                  value={editor.instructions}
                  onChange={(e) =>
                    setEditor({ ...editor, instructions: e.target.value })
                  }
                />
              </label>
              <div className="editor-row">
                <label>
                  Durée (minutes)
                  <input
                    type="number"
                    min="0"
                    value={editor.minutes}
                    onChange={(e) =>
                      setEditor({ ...editor, minutes: e.target.value })
                    }
                  />
                </label>
                <label>
                  Portions
                  <input
                    type="number"
                    min="1"
                    value={editor.servings}
                    onChange={(e) =>
                      setEditor({ ...editor, servings: e.target.value })
                    }
                  />
                </label>
                <label>
                  Coût estimé ($ CAD)
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={editor.estimated_cost_cad}
                    onChange={(e) =>
                      setEditor({
                        ...editor,
                        estimated_cost_cad: e.target.value,
                      })
                    }
                  />
                </label>
              </div>
              <fieldset>
                <legend>Ingrédients</legend>
                {editor.ingredients.map((item, index) => (
                  <RecipeIngredientRow
                    key={index}
                    item={item}
                    index={index}
                    catalog={catalog}
                    canRemove={editor.ingredients.length > 1}
                    onChange={(patch) => changeIngredient(index, patch)}
                    onRemove={() =>
                      setEditor({
                        ...editor,
                        ingredients: editor.ingredients.filter(
                          (_, i) => i !== index,
                        ),
                      })
                    }
                  />
                ))}
                <button
                  type="button"
                  className="text-button"
                  onClick={() =>
                    setEditor({
                      ...editor,
                      ingredients: [
                        ...editor.ingredients,
                        {
                          ingredient_id: "",
                          quantity: "",
                          unit: "unit",
                          essential: true,
                        },
                      ],
                    })
                  }
                >
                  ＋ Ajouter une ligne
                </button>{" "}
                <button
                  type="button"
                  className="text-button"
                  onClick={addIngredient}
                >
                  ＋ Créer un ingrédient
                </button>
              </fieldset>
              {options &&
                [
                  ["diets", "dietary_tags", "Régimes compatibles"],
                  ["allergens", "allergens", "Allergènes présents"],
                  ["intolerances", "intolerances", "Intolérances concernées"],
                ].map(([key, field, title]) => (
                  <fieldset key={key}>
                    <legend>{title}</legend>
                    <>
                      {field !== "dietary_tags" && (
                        <label>
                          <input
                            type="checkbox"
                            checked={editor[field] !== null}
                            onChange={(e) =>
                              setEditor({
                                ...editor,
                                [field]: e.target.checked ? [] : null,
                              })
                            }
                          />{" "}
                          Liste connue et complète
                        </label>
                      )}
                      {editor[field] !== null && (
                        <div className="editor-options">
                          {options[key].map((option) => (
                            <label key={option.id}>
                              <input
                                type="checkbox"
                                checked={editor[field].includes(option.id)}
                                onChange={(e) =>
                                  setEditor({
                                    ...editor,
                                    [field]: e.target.checked
                                      ? [...editor[field], option.id]
                                      : editor[field].filter(
                                          (id) => id !== option.id,
                                        ),
                                  })
                                }
                              />
                              {option.label}
                            </label>
                          ))}
                        </div>
                      )}
                    </>
                  </fieldset>
                ))}
              {options && (
                <fieldset>
                  <legend>Valeurs nutritionnelles</legend>
                  <NutritionInputs
                    nutrients={options.nutrients}
                    values={editor.nutrition}
                    onChange={(id, value) =>
                      setEditor({
                        ...editor,
                        nutrition: { ...editor.nutrition, [id]: value },
                      })
                    }
                  />
                </fieldset>
              )}
              <div className="detail-actions">
                <button className="button primary" disabled={busy}>
                  {busy ? "Enregistrement…" : "Enregistrer"}
                </button>
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setEditor(null)}
                >
                  Annuler
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
