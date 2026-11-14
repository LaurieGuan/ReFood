const fractions = new Map([[0, 'Vide'], [0.25, '¼'], [0.5, '½'], [0.75, '¾'], [1, 'Plein']]);

export function FractionControl({ name, value, onChange, disabled = false }) {
  const text = value == null ? 'Inconnue' : fractions.get(value) ?? `${Math.round(value * 100)} %`;
  return <div className="fraction-control">
    <label>
      <span>Quantité restante : <strong>{text}</strong></span>
      <input type="range" min="0" max="1" step="0.25" value={value ?? 1} disabled={disabled} aria-label={`Quantité restante de ${name}`} aria-valuetext={text} onChange={(event) => onChange(Number(event.target.value))}/>
    </label>
    <div className="fraction-scale" aria-hidden="true"><span>Vide</span><span>¼</span><span>½</span><span>¾</span><span>Plein</span></div>
    <button type="button" className="text-button" disabled={disabled} onClick={() => onChange(value == null ? 1 : null)}>{value == null ? "Préciser la quantité (plein)" : "Quantité inconnue"}</button>
  </div>;
}
