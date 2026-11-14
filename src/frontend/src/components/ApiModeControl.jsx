import { isDemoMode, switchApiMode } from '../services/api/apiMode.js';
export function ApiModeControl() {
  return <div className="api-mode-control">
    <span>Mode : {isDemoMode ? 'Demo · Sample data' : 'Flask API'}</span>{' '}
    <button className="text-button" onClick={() => switchApiMode(!isDemoMode)}>{isDemoMode ? 'Retour au mode réel' : 'Activer la démo hors ligne'}</button>
    {isDemoMode && <p role="alert">Mode démo activé : reconnaissance simulée, recettes et prix fictifs. Les résultats ne proviennent pas d’une IA ni de magasins en direct.</p>}
  </div>;
}
