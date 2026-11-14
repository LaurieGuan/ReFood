import { useEffect, useState } from 'react';
import { mockApi } from '../../services/api/mockApi.js';

function Choices({ title, name, options, selected }) {
  return <fieldset><legend>{title}</legend><div className="allergen-grid">{options.map(({ id, label }) => <label className="allergen" key={id}><input type="checkbox" name={name} value={id} defaultChecked={selected.includes(id)}/>{label}</label>)}</div></fieldset>;
}

export function PreferencesPanel({ preferences, onSave, loading, saved }) {
  const [options, setOptions] = useState(null);
  const [ingredients, setIngredients] = useState([]);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    Promise.all([mockApi.getPreferenceOptions(), mockApi.getIngredientCatalog()]).then(([choices, catalog]) => {
      if (active) { setOptions(choices); setIngredients(catalog.items); }
    }).catch(() => { if (active) setError('Impossible de charger les options alimentaires.'); });
    return () => { active = false; };
  }, []);
  if (error) return <div className="error-banner" role="alert">{error}</div>;
  if (!options) return <p>Chargement des options alimentaires…</p>;
  const submit = (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const nutrition_limits = Object.fromEntries(options.nutrients.map(({ id }) => [id, {
      min: form.get(`${id}_min`) === '' ? null : Number(form.get(`${id}_min`)),
      max: form.get(`${id}_max`) === '' ? null : Number(form.get(`${id}_max`)),
    }]));
    onSave({ ...preferences, dietary_restrictions: form.getAll('dietary_restrictions'), allergens: form.getAll('allergens'), intolerances: form.getAll('intolerances'), excluded_ingredient_ids: form.getAll('excluded_ingredient_ids'), nutrition_limits, max_budget_cad: form.get('max_budget_cad') || null, max_minutes: form.get('max_minutes') ? Number(form.get('max_minutes')) : null, servings: Number(form.get('servings')) });
  };
  return <section className="panel preferences-panel"><div className="section-heading"><div><h2>Ce qui vous convient</h2><p>Ces préférences filtrent votre prochaine recherche.</p></div></div><form onSubmit={submit} className="preferences-form">
    <Choices title="Régimes alimentaires" name="dietary_restrictions" options={options.diets} selected={preferences.dietary_restrictions ?? []}/>
    <Choices title="Allergènes à éviter" name="allergens" options={options.allergens} selected={preferences.allergens ?? []}/>
    <Choices title="Intolérances" name="intolerances" options={options.intolerances} selected={preferences.intolerances ?? []}/>
    <Choices title="Ingrédients à exclure" name="excluded_ingredient_ids" options={ingredients.map((item) => ({ id: item.id, label: item.display_name }))} selected={preferences.excluded_ingredient_ids ?? []}/>
    <fieldset><legend>Valeurs nutritionnelles par portion</legend><div className="nutrition-fields">{options.nutrients.map(({ id, label, unit }) => <div key={id} className="nutrition-row"><strong>{label} ({unit})</strong><label>Minimum<input type="number" name={`${id}_min`} min="0" step="any" placeholder="Sans limite" defaultValue={preferences.nutrition_limits?.[id]?.min ?? ''}/></label><label>Maximum<input type="number" name={`${id}_max`} min="0" step="any" placeholder="Sans limite" defaultValue={preferences.nutrition_limits?.[id]?.max ?? ''}/></label></div>)}</div></fieldset>
    <div className="optional-fields"><label>Temps maximal<div className="input-suffix"><input type="number" name="max_minutes" min="1" placeholder="Sans limite" defaultValue={preferences.max_minutes ?? ''}/><span>minutes</span></div></label><label>Budget maximal par recette<div className="input-suffix"><input type="number" name="max_budget_cad" min="0" step="0.01" placeholder="Sans limite" defaultValue={preferences.max_budget_cad ?? ''}/><span>$ CAD</span></div></label><label>Portions<div className="input-suffix"><input type="number" name="servings" min="1" max="20" defaultValue={preferences.servings ?? 2}/><span>personnes</span></div></label></div>
    <p className="safety-note">Les données sont illustratives et ne garantissent pas la sécurité alimentaire. Les recettes dont les données nécessaires sont inconnues sont exclues lorsqu’un filtre est actif.</p><div className="form-actions"><span>{saved ? 'Préférences enregistrées' : 'Vous pourrez les modifier à tout moment.'}</span><button className="button primary" disabled={loading}>{loading ? 'Enregistrement…' : 'Enregistrer les préférences'}</button></div>
  </form></section>;
}
