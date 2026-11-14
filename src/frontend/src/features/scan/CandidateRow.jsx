import { inventoryLocations } from "../../data/inventoryLocations.js";
import { icon, label } from "../../utils/ingredients.js";
import { FractionControl } from "../pantry/FractionControl.jsx";
import { quantityMode } from "./useCandidateEditor.js";
import { mockApi } from "../../services/api/mockApi.js";

export function CandidateRow({ item, loading, onUpdate }) {
  const update = (patch) => onUpdate(item.candidate_id, patch);

  return (
    <div
      className={`candidate-row ${!item.approved ? "rejected" : ""}`}
      key={item.candidate_id}
    >
      <label className="approve-choice">
        <input
          type="checkbox"
          checked={item.approved}
          onChange={(event) => update({ approved: event.target.checked })}
        />
        <span>{item.approved ? "Garder" : "Écarter"}</span>
      </label>
      <span className="food-icon" aria-hidden="true">{icon(mockApi.ingredient(item.editedName)?.name ?? item.editedName)}</span>
      <input
        className="ingredient-name"
        aria-label="Nom de l’aliment"
        value={item.editedName}
        onChange={(event) => update({ editedName: event.target.value, quantityMode: quantityMode(event.target.value), quantityText: "", unitChoice: "unknown", remaining_fraction: null })}
      />
      <span className={`certainty ${item.certainty}`}>
        {item.certainty === "high"
          ? "Confiance élevée"
          : item.certainty === "medium"
            ? "À vérifier"
            : item.certainty === "low"
              ? "Confiance faible"
              : "Ajout manuel"}
      </span>
      <select
        className="quantity-mode"
        aria-label={`Type de quantité de ${label(item.editedName)}`}
        value={item.quantityMode}
        onChange={(event) => update({ quantityMode: event.target.value, quantityText: "", unitChoice: "unknown", remaining_fraction: null })}
      >
        <option value="unknown">Type à préciser</option>
        <option value="pieces">À la pièce</option>
        <option value="container">Dans un contenant</option>
      </select>
      {item.quantityMode !== "unknown" && <input
        className="quantity-input"
        type="number"
        min="0"
        step="any"
        placeholder={item.quantityMode === "pieces" ? "Nombre" : "Capacité"}
        aria-label={`${item.quantityMode === "pieces" ? "Nombre restant" : "Capacité du contenant"} de ${label(item.editedName)}`}
        value={item.quantityText}
        onChange={(event) => update({ quantityText: event.target.value })}
      />}
      {item.quantityMode === "pieces" && <span className="quantity-unit">pièce(s)</span>}
      {item.quantityMode === "container" && <select
        className="unit-select"
        aria-label="Unité"
        value={item.unitChoice}
        onChange={(event) => update({ unitChoice: event.target.value })}
      >
        <option value="unknown">unité ?</option>
        <option value="g">g</option>
        <option value="kg">kg</option>
        <option value="ml">ml</option>
        <option value="l">L</option>
      </select>}
      <select
        className="candidate-location"
        aria-label={`Emplacement de ${label(item.name)}`}
        value={item.location ?? ""}
        onChange={(event) => update({ location: event.target.value || null })}
      >
        <option value="">Non précisé</option>
        {inventoryLocations.map((location) => (
          <option key={location.value} value={location.value}>
            {location.label}
          </option>
        ))}
      </select>
      {item.quantityMode === "container" && <FractionControl
        name={label(item.editedName)}
        value={item.remaining_fraction}
        disabled={!item.approved || loading}
        onChange={(remaining_fraction) => update({ remaining_fraction })}
      />}
    </div>
  );
}
