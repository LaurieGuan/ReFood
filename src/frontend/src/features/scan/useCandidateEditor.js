import { useState } from "react";
import { mockApi } from "../../services/api/mockApi.js";

function normalizeCandidates(scan) {
  return (scan.confirmedItems ?? scan.candidates).map((item, index) => ({
    ...item,
    candidate_id: item.candidate_id ?? item.id ?? `candidate_${index}`,
    approved: true,
    editedName: item.name,
    quantityText: item.quantity == null ? "" : String(item.quantity),
    unitChoice: item.unit || "unknown",
    remaining_fraction: item.remaining_fraction ?? null,
    location: item.location ?? "fridge",
    source: item.source ?? "scan_confirmed",
  }));
}

function toConfirmedItems(approved) {
  return approved.map((item) => {
    const known = mockApi.ingredient(item.editedName);
    const quantity =
      item.quantityText === "" ? null : Number(item.quantityText);
    const originalName =
      item.editedName.trim().toLocaleLowerCase() ===
      item.name.trim().toLocaleLowerCase();

    return {
      ingredient_id:
        known?.id ?? (originalName ? item.ingredient_id : null) ?? null,
      name: known?.name ?? item.editedName.trim(),
      quantity,
      unit: quantity == null ? "unknown" : item.unitChoice,
      remaining_fraction: item.remaining_fraction,
      location: item.location,
      source: item.source,
    };
  });
}

export function useCandidateEditor({ scan, onConfirm }) {
  const [items, setItems] = useState(() => normalizeCandidates(scan));
  const [manualName, setManualName] = useState("");
  const approved = items.filter(
    (item) => item.approved && item.editedName.trim(),
  );
  const invalidQuantity = approved.some(
    (item) =>
      item.quantityText !== "" &&
      (!Number.isFinite(Number(item.quantityText)) ||
        Number(item.quantityText) < 0),
  );

  const update = (id, patch) =>
    setItems((current) =>
      current.map((item) =>
        item.candidate_id === id ? { ...item, ...patch } : item,
      ),
    );

  const addManual = () => {
    if (!manualName.trim()) return;
    setItems((current) => [
      ...current,
      {
        candidate_id: `manual_${Date.now()}_${current.length}`,
        ingredient_id: null,
        name: manualName,
        editedName: manualName,
        certainty: "manual",
        quantityText: "",
        unitChoice: "unknown",
        remaining_fraction: null,
        location: "fridge",
        source: "manual",
        approved: true,
      },
    ]);
    setManualName("");
  };

  const confirm = () => onConfirm(toConfirmedItems(approved));

  return {
    items,
    approved,
    manualName,
    setManualName,
    invalidQuantity,
    update,
    addManual,
    confirm,
  };
}
