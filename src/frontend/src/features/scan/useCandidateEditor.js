import { useState } from 'react';
import { canonicalIngredient } from '../../utils/canonicalIngredient.js';
import { confirmedItems } from './confirmation.js';
import { mockApi } from '../../services/api/mockApi.js';
const pieceIds = new Set(['ing_egg', 'ing_tomato', 'ing_avocado', 'ing_onion']);
const containerIds = new Set(['ing_milk', 'ing_pasta', 'ing_rice', 'ing_oil']);
export function quantityMode(name) {
  const id = mockApi.ingredient(name)?.id;
  return pieceIds.has(id) ? 'pieces' : containerIds.has(id) ? 'container' : 'unknown';
}

function normalizeCandidates(scan) {
  return (scan.confirmedItems ?? scan.candidates).map((item, index) => ({
    ...item, candidate_id: item.candidate_id ?? item.id ?? `candidate_${index}`, approved: true,
    editedName: item.name, quantityText: item.quantity == null ? '' : String(item.quantity),
    unitChoice: item.unit === 'unit' ? 'piece' : (item.unit || 'unknown'),
    quantityMode: item.quantityMode ?? (item.unit === 'piece' || item.unit === 'unit' ? 'pieces' : quantityMode(item.name)),
    remaining_fraction: item.remaining_fraction ?? null, location: item.location ?? 'fridge', source: item.source ?? 'scan_confirmed',
  }));
}
export function useCandidateEditor({ scan, onConfirm }) {
  const [items, setItems] = useState(() => normalizeCandidates(scan));
  const [manualName, setManualName] = useState('');
  const approved = items.filter((item) => item.approved && item.editedName.trim());
  const invalidQuantity = approved.some((item) => item.quantityText !== '' && (!Number.isFinite(Number(item.quantityText)) || Number(item.quantityText) < 0));
  const invalidCanonical = approved.some((item) => !(item.ingredient_id && item.editedName.trim() === item.name.trim()) && !canonicalIngredient(item.editedName));
  const update = (id, patch) => setItems((current) => current.map((item) => item.candidate_id === id ? { ...item, ...patch } : item));
  const addManual = () => {
    if (!manualName.trim()) return;
    setItems((current) => [...current, { candidate_id: `manual_${Date.now()}_${current.length}`, name: manualName, editedName: manualName, certainty: 'manual', quantityText: '', unitChoice: 'unknown', quantityMode: quantityMode(manualName), remaining_fraction: null, location: 'fridge', source: 'manual', approved: true }]);
    setManualName('');
  };
  let duplicateError = '';
  try { confirmedItems(items); } catch (e) { duplicateError = e.message; }
  const confirm = () => onConfirm(confirmedItems(items));
  return { items, approved, manualName, setManualName, invalidQuantity, invalidCanonical, duplicateError, update, addManual, confirm };

}
