import { label } from "../../utils/ingredients.js";
import { mockApi } from "../../services/api/mockApi.js";

export function RecipeGrid({ recipes, saved, onOpen, onToggle }) {
  if (!recipes.length)
    return (
      <div className="panel empty-saved">
        <span>🍲</span>
        <h2>Aucune recette trouvée</h2>
        <p>Essayez de garder quelques ingrédients supplémentaires.</p>
      </div>
    );
  return (
    <div className="recipe-grid">
      {recipes.map((recipe) => {
        const isSaved = saved.some((item) => item.id === recipe.id);
        return (
          <article className="recipe-card" key={recipe.id}>
            <button className="recipe-open" onClick={() => onOpen(recipe.id)}>
              <div className="recipe-art">
                {recipe.image_url ? (
                  <img src={recipe.image_url} alt="" />
                ) : (
                  <span>🍽</span>
                )}
                <small>
                  {recipe.minutes == null
                    ? "Durée inconnue"
                    : `${recipe.minutes} min`}
                </small>
              </div>
              <div className="recipe-copy">
                <h3>{recipe.title}</h3>
                <p>
                  {recipe.match?.missing_ingredient_ids?.length
                    ? `À prévoir : ${(recipe.match.missing_ingredients ?? recipe.match.missing_ingredient_ids.map((id) => ({ name: mockApi.ingredientName(id) }))).map((item) => label(item.name)).join(", ")}`
                    : recipe.match
                      ? "Ingrédients essentiels présents"
                      : "Votre favori, gardé pour plus tard."}
                </p>
                {recipe.match && (
                  <div className="match-row">
                    <span>
                      {Math.round(recipe.match.coverage * 100)}% présents
                    </span>
                    <span>
                      {recipe.match.quantity_verified
                        ? "Quantités vérifiées"
                        : "Quantités à vérifier"}
                    </span>
                  </div>
                )}
                <small className="unknown-price">
                  {recipe.estimated_missing_cost_cad == null
                    ? "Coût des ingrédients manquants inconnu"
                    : `${recipe.estimated_missing_cost_cad} $ CAD`}
                </small>
              </div>
            </button>
            <button
              className={`save-button ${isSaved ? "saved" : ""}`}
              aria-label={
                isSaved
                  ? "Retirer des recettes enregistrées"
                  : "Enregistrer la recette"
              }
              aria-pressed={isSaved}
              onClick={() => onToggle(recipe)}
            >
              {isSaved ? "♥ Enregistrée" : "♡ Enregistrer"}
            </button>
          </article>
        );
      })}
    </div>
  );
}
