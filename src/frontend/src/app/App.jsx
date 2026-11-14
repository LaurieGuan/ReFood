import React, { useMemo, useState } from 'react';
import { CandidateEditor } from '../features/scan/CandidateEditor.jsx';
import { RecipeGrid } from '../features/recipes/RecipeGrid.jsx';
import { RecipeDetails } from '../features/recipes/RecipeDetails.jsx';
import { useScanSession } from '../hooks/useScanSession.js';
import { useFavorites } from '../hooks/useFavorites.js';
import { usePreferences } from '../hooks/usePreferences.js';
import { mockApi } from '../services/api/mockApi.js';
import { label } from '../utils/ingredients.js';
import { destinations } from './navigation.js';
import { Login } from '../features/auth/Login.jsx';
import '../styles/global.css';
import '../styles/flow.css';
import '../styles/login.css';


export function App() {
  const [showLogin, setShowLogin] = useState(true);
  const [screen, setScreen] = useState('scan');
  const { stage, setStage, photo, setPhoto, scan, setScan, suggestions, setSuggestions, priceData, setPriceData, selectedRecipe, setSelectedRecipe, selectedStore, setSelectedStore } = useScanSession();
  const { saved, toggleSaved: toggleFavorite } = useFavorites();
  const { preferences, setPreferences, preferencesSaved, setPreferencesSaved } = usePreferences();
  const [activeRecipe, setActiveRecipe] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

  const ingredientIds = useMemo(() => scan?.confirmedItems?.map((item) => item.ingredient_id).filter(Boolean) ?? [], [scan]);

  const say = (text) => { setToast(text); window.setTimeout(() => setToast(''), 2300); };
  const runScan = async (event) => {
    event.preventDefault(); if (!photo) { setError('Choisissez une photo pour démarrer le scan.'); return; }
    setLoading(true); setError('');
    try { const response = await mockApi.scanImage(photo); setScan(response); setStage(1); }
    catch (e) { setError(e.message); } finally { setLoading(false); }
  };
  const getRecipes = async (confirmedItems) => {
    setLoading(true); setError('');
    try {
      const savedPantry = await mockApi.replacePantry({ items: confirmedItems });
      const response = await mockApi.searchRecipes({ ingredient_ids: savedPantry.items.map((item) => item.ingredient_id).filter(Boolean), preferences: preferences ?? {}, limit: 10 });
      const updatedScan = { ...scan, confirmedItems: savedPantry.items };
      setScan(updatedScan); setSuggestions(response.recipes); setStage(2);
    } catch (e) { setError(e.message); } finally { setLoading(false); }
  };
  const openRecipe = async (id) => { setLoading(true); setError(''); try { setActiveRecipe(await mockApi.getRecipe(id)); } catch (e) { setError(e.message); } finally { setLoading(false); } };
  const chooseRecipe = async (recipe) => {
    setActiveRecipe(null); setSelectedRecipe(recipe); setPriceData(null); setSelectedStore(''); setStage(3); setLoading(true); setError('');
    try {
      const missingIds = recipe.ingredients.filter((item) => item.essential && !ingredientIds.includes(item.ingredient_id)).map((item) => item.ingredient_id);
      const response = await mockApi.comparePrices({ ingredient_ids: missingIds, region: 'Montreal, QC' });
      setPriceData(response);
      const merchant = response.offers[0]?.merchant;
      if (merchant) setSelectedStore(merchant);
    } catch (e) { setError(e.message); } finally { setLoading(false); }
  };
  const exportList = () => {
    if (!selectedRecipe) return;
    const missing = selectedRecipe.ingredients.filter((item) => item.essential && !ingredientIds.includes(item.ingredient_id));
    const offers = priceData?.offers.filter((offer) => offer.merchant === selectedStore) ?? [];
    const lines = [`REFOOD — Liste de courses`, `Recette : ${selectedRecipe.title}`, `Magasin : ${selectedStore || 'Non sélectionné'}`, 'Données de démonstration — prix non actuels', '', 'À acheter:', ...missing.map((item) => { const offer = offers.find((x) => x.ingredient_id === item.ingredient_id); return `- ${label(item.name)}${offer ? ` — ${offer.product_name} (${offer.price_cad} $ ${offer.currency})` : ' — prix inconnu'}`; })];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = 'refood-liste-de-courses.txt'; link.click(); URL.revokeObjectURL(url); say('Votre liste de courses a été exportée.');
  };
  const toggleSaved = async (recipe) => {
    setLoading(true); setError('');
    try {
      const wasSaved = saved.some((item) => item.id === recipe.id);
      await toggleFavorite(recipe);
      say(wasSaved ? 'Recette retirée des favoris.' : 'Recette enregistrée.');
    } catch (e) { setError(e.message); } finally { setLoading(false); }
  };
  const savePreferences = async (event) => {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const next = { ...preferences, dietary_restrictions: form.get('vegetarian') ? ['vegetarian'] : [], allergens: form.getAll('allergens'), max_budget_cad: form.get('max_budget_cad') || null, max_minutes: form.get('max_minutes') ? Number(form.get('max_minutes')) : null, servings: Number(form.get('servings')) };
    setLoading(true); setError('');
    try { setPreferences(await mockApi.putPreferences(next)); setPreferencesSaved(true); say('Préférences enregistrées.'); }
    catch (e) { setError(e.message); } finally { setLoading(false); }
  };
  const resetScan = () => { setPhoto(null); setScan(null); setSuggestions([]); setPriceData(null); setSelectedRecipe(null); setSelectedStore(''); setStage(0); setError(''); };

  const stageTitles = ['Qu’y a-t-il dans votre frigo ?', 'Vérifiez les ingrédients', 'Vos recettes', 'Comparer les magasins', 'Votre liste à emporter'];
  const stageSubtitles = ['Ajoutez une photo, puis confirmez les propositions avant de chercher des recettes.', 'Gardez les bons ingrédients, corrigez les autres ou ajoutez ce qui manque.', 'Des idées à partir des ingrédients que vous avez confirmés.', 'Comparez les offres indicatives pour les ingrédients manquants.', 'Votre liste est prête à télécharger ou à ouvrir dans Maps.'];
  const title = screen === 'scan' ? stageTitles[stage] : screen === 'saved' ? 'Mes recettes enregistrées' : 'Préférences alimentaires';
  const subtitle = screen === 'scan' ? stageSubtitles[stage] : screen === 'saved' ? 'Retrouvez les recettes que vous souhaitez garder sous la main.' : 'Indiquez vos préférences pour guider les suggestions.';

  if (showLogin) return <Login onDemo={() => setShowLogin(false)} />;

  return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="#scan" onClick={(e) => { e.preventDefault(); setScreen('scan'); }}><span className="brand-mark">r.</span><span>refood<span className="brand-dot">.</span></span></a><p className="side-caption">VOTRE CUISINE</p><nav>{destinations.map((item) => <button key={item.id} className={`nav-link ${screen === item.id ? 'selected' : ''}`} onClick={() => { setScreen(item.id); setError(''); }}><span className="nav-icon">{item.icon}</span>{item.label}{item.id === 'saved' && saved.length > 0 && <small>{saved.length}</small>}</button>)}</nav><div className="side-note"><span>i</span><p>Une photo propose des ingrédients, elle ne modifie jamais votre liste sans votre accord.</p><code>{mockApi.baseUrl}</code></div><div className="profile"><span>CM</span><div><b>Camille Martin</b><small>Compte démo</small></div></div></aside>
    <main className="main-area"><header className="topbar"><span>REFOOD <i>/</i> {destinations.find((item) => item.id === screen)?.label}</span><span className="api-state"><i/> Démo interactive</span></header><div className="content">
      <div className="page-heading"><div><p className="eyebrow">REFOOD <span>·</span> MONTRÉAL</p><h1>{title}</h1><p className="subtitle">{subtitle}</p></div></div>
      {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')}>×</button></div>}
      {screen === 'scan' && <>
        <div className="stepper">{['Scan', 'Ingrédients', 'Recettes', 'Magasins', 'Export'].map((item, i) => <div key={item} className={`step ${i === stage ? 'current' : ''} ${i < stage ? 'done' : ''}`}><span>{i < stage ? '✓' : i + 1}</span>{item}</div>)}</div>
        {stage === 0 && (loading ? <WaitPanel title="Analyse de votre photo" detail="Repérage des aliments visibles…"/> : <div className="scan-start"><section className="panel upload-panel"><div className="upload-heading"><span className="camera-mark">▧</span><div><h2>Ajoutez une photo du frigo</h2><p>Choisissez une image pour repérer les ingrédients visibles.</p></div></div><label className={`dropzone ${photo ? 'has-photo' : ''}`}><input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => { setPhoto(e.target.files?.[0] ?? null); setError(''); }}/>{photo ? <><img src={URL.createObjectURL(photo)} alt="Aperçu de votre photo"/><span className="change-photo">Changer la photo</span></> : <><span className="upload-symbol">＋</span><b>Choisir une photo</b><small>JPG, PNG ou WebP</small></>}</label><button className="button primary full" disabled={!photo || loading} onClick={runScan}>Analyser la photo →</button></section><aside className="scan-help"><h3>Comment ça marche ?</h3><ol><li><span>1</span>Ajoutez une photo des aliments visibles.</li><li><span>2</span>Vérifiez et corrigez les suggestions.</li><li><span>3</span>Choisissez une recette et un magasin.</li></ol><p>Les quantités exactes ne sont pas déduites d’une image. Vous pourrez les modifier avant de confirmer.</p></aside></div>)}
        {stage === 1 && scan && <><section className="panel candidate-panel"><div className="section-heading"><div><h2>Aliments repérés</h2><p>Cochez ceux à garder. Vous pouvez corriger le nom ou la quantité.</p></div><button className="text-button" onClick={resetScan}>← Changer la photo</button></div>{scan.warnings.map((warning) => <div className="warning" key={warning}>ⓘ &nbsp;{warning}</div>)}<CandidateEditor key={scan.scan_id} scan={scan} onConfirm={getRecipes} loading={loading}/></section></>}
        {stage === 2 && <><div className="results-bar"><span>{suggestions.length} idées de recettes <small>· ingrédients confirmés seulement</small></span><button className="text-button" onClick={() => setStage(1)}>← Modifier les ingrédients</button></div><RecipeGrid recipes={suggestions} saved={saved} onOpen={openRecipe} onToggle={toggleSaved}/><div className="results-footnote">Les ingrédients manquants sont à prévoir. Prix non disponibles dans cette démo; quantités et adéquation alimentaire non vérifiées.</div></>}
        {stage === 3 && (loading || !priceData ? <WaitPanel title="Comparaison des magasins" detail="Recherche des offres de démonstration…"/> : <StoreScreen recipe={selectedRecipe} ingredientIds={ingredientIds} priceData={priceData} selectedStore={selectedStore} setSelectedStore={setSelectedStore} onBack={() => setStage(2)} onContinue={() => setStage(4)}/>)}
        {stage === 4 && <ExportScreen recipe={selectedRecipe} ingredientIds={ingredientIds} priceData={priceData} selectedStore={selectedStore} onDownload={exportList} onRestart={resetScan}/>}
      </>}
      {screen === 'saved' && <><div className="results-bar"><span>{saved.length} recette{saved.length === 1 ? '' : 's'}</span></div>{saved.length ? <RecipeGrid recipes={saved.map((item) => ({ ...item, minutes: null, estimated_missing_cost_cad: null, dietary_verification: 'unknown' }))} saved={saved} onOpen={openRecipe} onToggle={toggleSaved}/> : <div className="panel empty-saved"><span>♡</span><h2>Vos recettes gardées apparaîtront ici</h2><p>Lancez un scan et touchez le cœur d’une recette pour l’enregistrer.</p><button className="button primary" onClick={() => { setScreen('scan'); resetScan(); }}>Commencer un scan</button></div>}</>}
      {screen === 'preferences' && preferences && <section className="panel preferences-panel"><div className="section-heading"><div><h2>Ce qui vous convient</h2><p>Ces préférences seront envoyées avec votre prochaine recherche.</p></div></div><form onSubmit={savePreferences} className="preferences-form"><fieldset><legend>Régime alimentaire</legend><label className="choice"><input type="checkbox" name="vegetarian" value="vegetarian" defaultChecked={preferences.dietary_restrictions.includes('vegetarian')}/><span><b>Végétarien</b><small>Exclure viande et poisson des préférences de recherche.</small></span></label></fieldset><fieldset><legend>Allergènes à éviter</legend><div className="allergen-grid">{[['peanut','Arachide'],['milk','Lait'],['egg','Œuf'],['wheat','Blé / gluten'],['soy','Soja'],['tree_nut','Noix']].map(([value, text]) => <label className="allergen" key={value}><input type="checkbox" name="allergens" value={value} defaultChecked={preferences.allergens.includes(value)}/>{text}</label>)}</div></fieldset><div className="optional-fields"><label>Temps maximal<div className="input-suffix"><input type="number" name="max_minutes" min="1" placeholder="Sans limite" defaultValue={preferences.max_minutes ?? ''}/><span>minutes</span></div></label><label>Budget maximal<div className="input-suffix"><input type="number" name="max_budget_cad" min="0" step="0.01" placeholder="Sans limite" defaultValue={preferences.max_budget_cad ?? ''}/><span>$ CAD</span></div></label><label>Portions<div className="input-suffix"><input type="number" name="servings" min="1" max="20" defaultValue={preferences.servings}/><span>personnes</span></div></label></div><p className="safety-note">Les recettes de démonstration ne contiennent pas de données allergènes vérifiées. Refood ne peut pas garantir qu’une recette convient à vos restrictions.</p><div className="form-actions"><span>{preferencesSaved ? 'Préférences enregistrées' : 'Vous pourrez les modifier à tout moment.'}</span><button className="button primary" disabled={loading}>{loading ? 'Enregistrement…' : 'Enregistrer les préférences'}</button></div></form></section>}
    </div></main>
    {activeRecipe && <RecipeDetails recipe={activeRecipe} onClose={() => setActiveRecipe(null)} onChoose={() => chooseRecipe(activeRecipe)} saved={saved.some((item) => item.id === activeRecipe.id)} onToggle={() => toggleSaved(activeRecipe)}/ >}{toast && <div className="toast" role="status">✓ &nbsp;{toast}</div>}
    <nav className="mobile-nav">{destinations.map((item) => <button key={item.id} className={screen === item.id ? 'active' : ''} onClick={() => { setScreen(item.id); setError(''); }}><span>{item.icon}</span>{item.label}</button>)}</nav>
  </div>;
}

function WaitPanel({ title, detail }) {
  return <section className="panel wait-panel" aria-live="polite"><div className="wait-wheel" role="status" aria-label="Traitement en cours"/><h2>{title}</h2><p>{detail}</p><small>Cette démo utilise un délai simulé.</small></section>;
}

function StoreScreen({ recipe, ingredientIds, priceData, selectedStore, setSelectedStore, onBack, onContinue }) {
  const missing = recipe.ingredients.filter((item) => item.essential && !ingredientIds.includes(item.ingredient_id));
  const merchants = [...new Set(priceData.offers.map((offer) => offer.merchant))];
  const hasNeeds = missing.length > 0;
  const money = (value) => new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(value);
  return <section className="store-screen"><div className="store-heading"><div><h2>Pour cuisiner : {recipe.title}</h2><p>Les montants affichent les prix du paquet complet proposé, pas le coût de la quantité utilisée.</p></div><span className="demo-tag">PRIX ILLUSTRATIFS</span></div>
    {!hasNeeds && <div className="panel no-purchases"><span>✓</span><div><b>Tout est déjà dans votre liste confirmée.</b><small>Aucun achat essentiel à comparer pour cette recette.</small></div></div>}
    {hasNeeds && merchants.length === 0 && <div className="panel no-purchases"><span>i</span><div><b>Aucune offre démo pour les ingrédients manquants.</b><small>Vous pourrez tout de même exporter votre liste sans prix.</small></div></div>}
    {!!merchants.length && <div className="store-grid">{merchants.map((merchant) => { const offers = priceData.offers.filter((item) => item.merchant === merchant); const total = offers.reduce((sum, offer) => sum + Number(offer.price_cad), 0); return <label className={`store-card ${selectedStore === merchant ? 'chosen' : ''}`} key={merchant}><input type="radio" name="store" value={merchant} checked={selectedStore === merchant} onChange={() => setSelectedStore(merchant)}/><div className="store-card-head"><span className="store-icon">⌂</span><span><b>{merchant}</b><small>Montréal · magasin démo</small></span><i>{selectedStore === merchant ? '✓' : ''}</i></div><div className="offer-list">{offers.map((offer) => <div className="offer" key={offer.ingredient_id}><span>{label(mockApi.ingredientName(offer.ingredient_id))}<small>{offer.product_name} · {offer.package_quantity} {offer.package_unit}</small></span><b>{money(offer.price_cad)}</b></div>)}</div><div className="store-total"><span>Total des paquets</span><b>{money(total)}</b></div><small className="store-source">Source démo_catalog · valeurs illustratives</small></label>; })}</div>}
    {priceData.unpriced_ingredient_ids.length > 0 && <p className="unpriced-note">Prix introuvable pour : {priceData.unpriced_ingredient_ids.map((id) => label(mockApi.ingredientName(id))).join(', ')}.</p>}
    <div className="store-footer"><button className="button secondary" onClick={onBack}>← Retour aux recettes</button><button className="button primary" onClick={onContinue}>Continuer vers l’export →</button></div>
    <p className="price-disclaimer">Offres fictives fournies par l’API de démonstration. Elles ne représentent pas des prix ou stocks actuels.</p>
  </section>;
}

function ExportScreen({ recipe, ingredientIds, priceData, selectedStore, onDownload, onRestart }) {
  const missing = recipe.ingredients.filter((item) => item.essential && !ingredientIds.includes(item.ingredient_id));
  const offers = priceData?.offers.filter((offer) => offer.merchant === selectedStore) ?? [];
  const mapUrl = selectedStore ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${selectedStore}, Montréal, QC`)}` : null;
  return <section className="export-screen"><div className="export-top"><span className="export-check">✓</span><div><h2>Votre liste est prête</h2><p>{recipe.title}{selectedStore ? ` · ${selectedStore}` : ''}</p></div></div><div className="panel export-list"><div className="export-list-head"><h3>À acheter</h3><span>{missing.length} article{missing.length === 1 ? '' : 's'}</span></div>{missing.length ? missing.map((item) => { const offer = offers.find((entry) => entry.ingredient_id === item.ingredient_id); return <div className="export-item" key={item.ingredient_id}><span className="export-checkbox"/><span className="export-name">{label(item.name)}<small>{item.quantity == null ? 'Quantité inconnue' : `${item.quantity} ${item.unit}`}{offer ? ` · ${offer.product_name}` : ''}</small></span><b>{offer ? `${offer.price_cad} $` : 'Prix inconnu'}</b></div>; }) : <div className="all-set">Vous avez confirmé tous les ingrédients essentiels pour cette recette.</div>}{selectedStore && offers.length > 0 && <div className="export-total"><span>Coût indicatif des paquets</span><b>{offers.reduce((sum, offer) => sum + Number(offer.price_cad), 0).toFixed(2)} $ CAD</b></div>}</div><div className="export-actions"><button className="button primary" onClick={onDownload}>↓ &nbsp; Télécharger la liste (.txt)</button>{mapUrl && <a className="button secondary" href={mapUrl} target="_blank" rel="noreferrer">Ouvrir le magasin dans Maps ↗</a>}<button className="button text-only" onClick={onRestart}>Nouveau scan</button></div><p className="price-disclaimer">La liste est créée sur votre appareil. Les prix affichés sont fictifs et servent uniquement à prévisualiser le parcours.</p></section>;
}
