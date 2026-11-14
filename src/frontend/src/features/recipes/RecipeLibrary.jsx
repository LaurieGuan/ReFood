import { useEffect, useState } from 'react';
import { mockApi } from '../../services/api/mockApi.js';
import { RecipeGrid } from './RecipeGrid.jsx';
import './recipeLibrary.css';

const blank = () => ({ title: '', instructions: '', minutes: '', servings: '', ingredients: [{ ingredient_id: '', quantity: '', unit: 'unit', essential: true }], dietary_tags: [], allergens: null, intolerances: null, nutrition: {}, estimated_cost_cad: '' });

export function RecipeLibrary({ saved, onOpen, onToggle, onChanged }) {
  const [items, setItems] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [options, setOptions] = useState(null);
  const [editor, setEditor] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [onlyFavorites, setOnlyFavorites] = useState(false);
  const refresh = async () => { const response = await mockApi.listRecipes(); setItems(response.items); await onChanged?.(); };
  useEffect(() => {
    let alive = true;
    Promise.all([mockApi.listRecipes(), mockApi.getIngredientCatalog(), mockApi.getPreferenceOptions()]).then(([recipes, ingredients, preferences]) => {
      if (alive) { setItems(recipes.items); setCatalog(ingredients.items ?? ingredients); setOptions(preferences); }
    }).catch((e) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, []);
  const edit = (recipe) => setEditor(recipe ? { ...recipe, minutes: recipe.minutes ?? '', servings: recipe.servings ?? '', estimated_cost_cad: recipe.estimated_cost_cad ?? '', dietary_tags: recipe.dietary_tags ?? [], allergens: recipe.allergens ?? null, intolerances: recipe.intolerances ?? null, nutrition: recipe.nutrition ?? {}, ingredients: recipe.ingredients.map((item) => ({ ...item, quantity: item.quantity ?? '' })) } : blank());
  const submit = async (event) => {
    event.preventDefault(); setError('');
    if (editor.ingredients.some((item) => !item.ingredient_id)) { setError('Choisissez un ingrédient pour chaque ligne.'); return; }
    const value = { ...editor, title: editor.title.trim(), instructions: editor.instructions.trim(), minutes: editor.minutes === '' ? null : Number(editor.minutes), servings: editor.servings === '' ? null : Number(editor.servings), estimated_cost_cad: editor.estimated_cost_cad === '' ? null : Number(editor.estimated_cost_cad), nutrition: Object.fromEntries(Object.entries(editor.nutrition).filter(([, value]) => value !== '').map(([key, value]) => [key, Number(value)])), ingredients: editor.ingredients.map((item) => ({ ...item, name: catalog.find((entry) => entry.id === item.ingredient_id)?.name ?? item.name, quantity: item.quantity === '' ? null : Number(item.quantity) })) };
    setBusy(true);
    try { if (editor.id) await mockApi.updateRecipe(editor.id, value); else await mockApi.createRecipe(value); setEditor(null); await refresh(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const addIngredient = async () => {
    const name = window.prompt('Nom du nouvel ingrédient');
    if (!name?.trim()) return;
    try {
      const item = await mockApi.createIngredient(name);
      setCatalog((current) => current.some ( (entry) => entry.id === item.id) ? current : [...current, item]);
      setEditor((current) => ({ ...current, ingredients: [...current.ingredients, { ingredient_id: item.id, quantity: '', unit: 'unit', essential: true }] }));
    } catch (e) { setError(e.message); }
  };
  const remove = async (recipe) => {
    if (!window.confirm(`Supprimer « ${recipe.title} » ?`)) return;
    setBusy(true); setError('');
    try { await mockApi.deleteRecipe(recipe.id); await refresh(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const visible = onlyFavorites ? items.filter((item) => saved.some((favorite) => favorite.id === item.id)) : items;
  const changeIngredient = (index, patch) => setEditor({ ...editor, ingredients: editor.ingredients.map((item, i) => i === index ? { ...item, ...patch } : item) });
  return <div className="recipe-library">
    {error && <div className="error-banner" role="alert">{error}<button type="button" onClick={() => setError('')}>×</button></div>}
    <div className="results-bar"><span>{visible.length} recette{visible.length === 1 ? '' : 's'}</span><div className="library-actions"><label><input type="checkbox" checked={onlyFavorites} onChange={(e) => setOnlyFavorites(e.target.checked)}/> Favoris seulement</label><button className="button primary" onClick={() => edit(null)}>＋ Créer une recette</button></div></div>
    {visible.length ? <div className="library-list">{visible.map((recipe) => <div key={recipe.id}><RecipeGrid recipes={[recipe]} saved={saved} onOpen={onOpen} onToggle={onToggle}/><div className="library-card-actions"><button className="text-button" onClick={() => edit(recipe)}>Modifier</button><button className="text-button" disabled={busy} onClick={() => remove(recipe)}>Supprimer</button></div></div>)}</div> : <div className="panel empty-saved"><h2>Aucune recette à afficher</h2><p>Créez une recette ou modifiez votre sélection.</p></div>}
    {editor && <div className="modal-backdrop" onClick={() => setEditor(null)}><section className="recipe-modal recipe-editor" role="dialog" aria-modal="true" aria-label={editor.id ? 'Modifier la recette' : 'Créer une recette'} onClick={(event) => event.stopPropagation()}><button className="modal-close" type="button" onClick={() => setEditor(null)} aria-label="Fermer">×</button><h2>{editor.id ? 'Modifier la recette' : 'Créer une recette'}</h2><form onSubmit={submit}>
      <label>Nom<input required value={editor.title} onChange={(e) => setEditor({ ...editor, title: e.target.value })}/></label>
      <label>Préparation<textarea required rows="4" value={editor.instructions} onChange={(e) => setEditor({ ...editor, instructions: e.target.value })}/></label>
      <div className="editor-row"><label>Durée (minutes)<input type="number" min="0" value={editor.minutes} onChange={(e) => setEditor({ ...editor, minutes: e.target.value })}/></label><label>Portions<input type="number" min="1" value={editor.servings} onChange={(e) => setEditor({ ...editor, servings: e.target.value })}/></label><label>Coût estimé ($ CAD)<input type="number" min="0" step="0.01" value={editor.estimated_cost_cad} onChange={(e) => setEditor({ ...editor, estimated_cost_cad: e.target.value })}/></label></div>
      <fieldset><legend>Ingrédients</legend>{editor.ingredients.map((item, index) => <div className="editor-ingredient" key={index}><select aria-label={`Ingrédient ${index + 1}`} required value={item.ingredient_id ?? ''} onChange={(e) => changeIngredient(index, { ingredient_id: e.target.value })}><option value="">Choisir un ingrédient</option>{catalog.map((entry) => <option key={entry.id} value={entry.id}>{entry.display_name ?? entry.name}</option>)}</select><input aria-label="Quantité" type="number" min="0" step="any" placeholder="Quantité" value={item.quantity} onChange={(e) => changeIngredient(index, { quantity: e.target.value })}/><input aria-label="Unité" placeholder="Unité" value={item.unit} onChange={(e) => changeIngredient(index, { unit: e.target.value })}/><label><input type="checkbox" checked={item.essential} onChange={(e) => changeIngredient(index, { essential: e.target.checked })}/> Essentiel</label><button type="button" className="text-button" disabled={editor.ingredients.length === 1} onClick={() => setEditor({ ...editor, ingredients: editor.ingredients.filter((_, i) => i !== index) })}>Retirer</button></div>)}<button type="button" className="text-button" onClick={() => setEditor({ ...editor, ingredients: [...editor.ingredients, { ingredient_id: '', quantity: '', unit: 'unit', essential: true }] })}>＋ Ajouter une ligne</button> <button type="button" className="text-button" onClick={addIngredient}>＋ Créer un ingrédient</button></fieldset>
      {options && [['diets', 'dietary_tags', 'Régimes compatibles'], ['allergens', 'allergens', 'Allergènes présents'], ['intolerances', 'intolerances', 'Intolérances concernées']].map(([key, field, title]) => <fieldset key={key}><legend>{title}</legend><>{field !== 'dietary_tags' && <label><input type="checkbox" checked={editor[field] !== null} onChange={(e) => setEditor({ ...editor, [field]: e.target.checked ? [] : null })}/> Liste connue et complète</label>}{editor[field] !== null && <div className="editor-options">{options[key].map((option) => <label key={option.id}><input type="checkbox" checked={editor[field].includes(option.id)} onChange={(e) => setEditor({ ...editor, [field]: e.target.checked ? [...editor[field], option.id] : editor[field].filter((id) => id !== option.id) })}/>{option.label}</label>)}</div>}</></fieldset>)}
      {options && <fieldset><legend>Valeurs nutritionnelles</legend><div className="editor-row">{options.nutrients.map((option) => <label key={option.id}>{option.label} ({option.unit})<input type="number" min="0" step="any" value={editor.nutrition[option.id] ?? ''} onChange={(e) => setEditor({ ...editor, nutrition: { ...editor.nutrition, [option.id]: e.target.value } })}/></label>)}</div></fieldset>}
      <div className="detail-actions"><button className="button primary" disabled={busy}>{busy ? 'Enregistrement…' : 'Enregistrer'}</button><button type="button" className="button secondary" onClick={() => setEditor(null)}>Annuler</button></div>
    </form></section></div>}
  </div>;
}
