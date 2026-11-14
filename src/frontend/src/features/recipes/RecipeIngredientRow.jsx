export function RecipeIngredientRow({
  item,
  index,
  catalog,
  canRemove,
  onChange,
  onRemove,
}) {
  return (
    <div className="editor-ingredient">
      <select
        aria-label={`Ingrédient ${index + 1}`}
        required
        value={item.ingredient_id ?? ""}
        onChange={(event) => onChange({ ingredient_id: event.target.value })}
      >
        <option value="">Choisir un ingrédient</option>
        {catalog.map((entry) => (
          <option key={entry.id} value={entry.id}>
            {entry.display_name ?? entry.name}
          </option>
        ))}
      </select>
      <input
        aria-label="Quantité"
        type="number"
        min="0"
        step="any"
        placeholder="Quantité"
        value={item.quantity}
        onChange={(event) => onChange({ quantity: event.target.value })}
      />
      <input
        aria-label="Unité"
        placeholder="Unité"
        value={item.unit}
        onChange={(event) => onChange({ unit: event.target.value })}
      />
      <label>
        <input
          type="checkbox"
          checked={item.essential}
          onChange={(event) => onChange({ essential: event.target.checked })}
        />{" "}
        Essentiel
      </label>
      <button
        type="button"
        className="text-button"
        disabled={!canRemove}
        onClick={onRemove}
      >
        Retirer
      </button>
    </div>
  );
}
