import { useState } from 'react';
import { mockApi } from '../../services/api/mockApi.js';
import { icon, label } from '../../utils/ingredients.js';

export function CandidateEditor({ scan, onConfirm, loading }) {
  const [items, setItems] = useState(scan.candidates.map((item) => ({ ...item, approved: true, editedName: item.name, quantityText: '', unitChoice: item.unit || 'unknown', source: 'scan_confirmed' })));
  const [manualName, setManualName] = useState('');
  const approved = items.filter((item) => item.approved && item.editedName.trim());
  const update = (id, patch) => setItems((current) => current.map((item) => item.candidate_id === id ? { ...item, ...patch } : item));
  const addManual = () => {
    if (!manualName.trim()) return;
    setItems((current) => [...current, { candidate_id: `manual_${Date.now()}`, ingredient_id: null, name: manualName, editedName: manualName, certainty: 'manual', quantityText: '', unitChoice: 'unknown', source: 'manual', approved: true }]);
    setManualName('');
  };
  const confirm = () => onConfirm(approved.map((item) => {
    const known = mockApi.ingredient(item.editedName);
    const quantity = item.quantityText === '' ? null : Number(item.quantityText);
    return { ingredient_id: known?.id ?? item.ingredient_id ?? null, name: known?.name ?? item.editedName.trim().toLowerCase(), quantity, unit: quantity == null ? 'unknown' : item.unitChoice, remaining_fraction: null, source: item.source };
  }));
  return <>
    <div className="candidate-list">{items.map((item) => <div className={`candidate-row ${!item.approved ? 'rejected' : ''}`} key={item.candidate_id}>
      <label className="approve-choice"><input type="checkbox" checked={item.approved} onChange={(e) => update(item.candidate_id, { approved: e.target.checked })}/><span>{item.approved ? 'Garder' : 'Écarter'}</span></label>
      <span className="food-icon">{icon(item.name)}</span><input className="ingredient-name" aria-label="Nom de l’aliment" value={item.editedName} onChange={(e) => update(item.candidate_id, { editedName: e.target.value})}/>
      <span className={`certainty ${item.certainty}`}>{item.certainty === 'high' ? 'Confiance élevée' : item.certainty === 'medium' ? 'À vérifier' : item.certainty === 'low' ? 'Confiance faible' : 'Ajout manuel'}</span>
      <input className="quantity-input" type="number" min="0" step="any" placeholder="Qté" aria-label={`Quantité de ${label(item.name)}`} value={item.quantityText} onChange={(e) => update(item.candidate_id, { quantityText: e.target.value })}/>
      <select className="unit-select" aria-label="Unité" value={item.unitChoice} onChange={(e) => update(item.candidate_id, { unitChoice: e.target.value })}><option value="unknown">unité ?</option><option value="unit">unités</option><option value="g">g</option><option value="ml">ml</option></select>
    </div>)}</div>
    <div className="manual-add"><input value={manualName} onChange={(e) => setManualName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addManual())} placeholder="Un ingrédient oublié ? Ajoutez-le ici"/><button className="button secondary" onClick={addManual}>＋ Ajouter</button></div>
    <div className="confirm-footer"><span>{approved.length} ingrédient{approved.length === 1 ? '' : 's'} à confirmer <small>· {items.length - approved.length} écarté{items.length - approved.length === 1 ? '' : 's'}</small></span><button className="button primary" disabled={loading || approved.length === 0} onClick={confirm}>{loading ? 'Recherche en cours…' : 'Confirmer et trouver des recettes →'}</button></div>
    <p className="contract-note">Les propositions ne sont pas enregistrées avant votre confirmation. Une quantité vide reste « inconnue ».</p>
  </>;
}
