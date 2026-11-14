export function NutritionInputs({ nutrients, values, onChange }) {
  return (
    <div className="editor-row">
      {nutrients.map((nutrient) => (
        <label key={nutrient.id}>
          {nutrient.label} ({nutrient.unit})
          <input
            type="number"
            min="0"
            step="any"
            value={values[nutrient.id] ?? ""}
            onChange={(event) => onChange(nutrient.id, event.target.value)}
          />
        </label>
      ))}
    </div>
  );
}
