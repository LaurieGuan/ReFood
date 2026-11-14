import { inventoryLocations } from "../../data/inventoryLocations.js";
import { icon, label } from "../../utils/ingredients.js";
import { FractionControl } from "../pantry/FractionControl.jsx";

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
      <span className="food-icon">{icon(item.name)}</span>
      <input
        className="ingredient-name"
        aria-label="Nom de l’aliment"
        value={item.editedName}
        onChange={(event) => update({ editedName: event.target.value })}
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
      <input
        className="quantity-input"
        type="number"
        min="0"
        step="any"
        placeholder="Qté"
        aria-label={`Quantité initiale de ${label(item.name)}`}
        value={item.quantityText}
        onChange={(event) => update({ quantityText: event.target.value })}
      />
      <select
        className="unit-select"
        aria-label="Unité"
        value={item.unitChoice}
        onChange={(event) => update({ unitChoice: event.target.value })}
      >
        <option value="unknown">unité ?</option>
        <option value="unit">unités</option>
        <option value="g">g</option>
        <option value="ml">ml</option>
      </select>
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
      <FractionControl
        name={label(item.editedName)}
        value={item.remaining_fraction}
        disabled={!item.approved || loading}
        onChange={(remaining_fraction) => update({ remaining_fraction })}
      />
    </div>
  );
}
