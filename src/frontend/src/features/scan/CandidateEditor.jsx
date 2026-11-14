import "../pantry/pantry.css";
import { label } from "../../utils/ingredients.js";
import { CandidateRow } from "./CandidateRow.jsx";
import { useCandidateEditor } from "./useCandidateEditor.js";

export function CandidateEditor({ scan, onConfirm, loading }) {
  const {
    items,
    approved,
    manualName,
    setManualName,
    invalidQuantity,
    update,
    addManual,
    confirm,
  } = useCandidateEditor({ scan, onConfirm });
  return (
    <>
      <div className="candidate-list">
        {items.map((item) => (
          <CandidateRow
            key={item.candidate_id}
            item={item}
            loading={loading}
            onUpdate={update}
          />
        ))}
      </div>
      <div className="manual-add">
        <input
          value={manualName}
          onChange={(e) => setManualName(e.target.value)}
          onKeyDown={(e) =>
            e.key === "Enter" && (e.preventDefault(), addManual())
          }
          placeholder="Un ingrédient oublié ? Ajoutez-le ici"
        />
        <button type="button" className="button secondary" onClick={addManual}>
          ＋ Ajouter
        </button>
      </div>
      {invalidQuantity && (
        <p className="pantry-error" role="alert">
          Les quantités doivent être des nombres positifs ou nuls.
        </p>
      )}
      <div className="confirm-footer">
        <span>
          {approved.length} ingrédient{approved.length === 1 ? "" : "s"} à
          confirmer{" "}
          <small>
            · {items.length - approved.length} écarté
            {items.length - approved.length === 1 ? "" : "s"}
          </small>
        </span>
        <button
          type="button"
          className="button primary"
          disabled={loading || approved.length === 0 || invalidQuantity}
          onClick={confirm}
        >
          {loading
            ? "Recherche en cours…"
            : "Confirmer et trouver des recettes →"}
        </button>
      </div>
      <p className="contract-note">
        Les ingrédients servent à cette recherche. Une quantité vide reste «
        inconnue ».
      </p>
    </>
  );
}
