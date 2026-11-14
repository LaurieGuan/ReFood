import { useState } from 'react';
import { canonicalIngredient } from '../../utils/canonicalIngredient.js';

function normalizeCandidates(scan) {
  return (scan.confirmedItems ?? scan.candidates).map((item, index) => ({
    ...item, candidate_id: item.candidate_id ?? `candidate_${index}`, approved: true,
    editedName: item.name, quantityText: item.quantity == null ? '' : String(item.quantity),
    unitChoice: item.unit === 'unit' ? 'piece' : (item.unit || 'unknown'),
    remaining_fraction: item.remaining_fraction ?? null, location: item.location ?? 'fridge',
    source: item.source ?? 'scan_confirmed',
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
    setItems((current) => [...current, { candidate_id: `manual_${Date.now()}_${current.length}`, name: manualName, editedName: manualName, certainty: 'manual', quantityText: '', unitChoice: 'unknown', remaining_fraction: null, location: 'fridge', source: 'manual', approved: true }]);
    setManualName('');
  };
  const confirm = () => onConfirm(approved.map((item) => {
    const original = item.editedName.trim() === item.name.trim() && item.ingredient_id;
    const identity = original ? { ingredient_id: item.ingredient_id, name: item.name } : canonicalIngredient(item.editedName);
    const quantity = item.quantityText === '' ? null : Number(item.quantityText);
    return { ...identity, quantity, unit: quantity == null ? 'unknown' : item.unitChoice, remaining_fraction: item.remaining_fraction, location: item.location, source: item.source };
  }));
  return { items, approved, manualName, setManualName, invalidQuantity, invalidCanonical, update, addManual, confirm };
}
