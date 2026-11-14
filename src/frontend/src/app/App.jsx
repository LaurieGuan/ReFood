import { PreferencesPanel } from "../features/preferences/PreferencesPanel.jsx";
import { CandidateEditor } from "../features/scan/CandidateEditor.jsx";
import { RecipeGrid } from "../features/recipes/RecipeGrid.jsx";
import { RecipeDetails } from "../features/recipes/RecipeDetails.jsx";
import { RecipeLibrary } from "../features/recipes/RecipeLibrary.jsx";
import { destinations } from "./navigation.js";
import { useAppController } from "./useAppController.js";
import { AppNavigation } from "./AppNavigation.jsx";
import { AlertBanner } from "../components/AlertBanner.jsx";
import { StoreScreen, ExportScreen } from "../features/stores/StoreScreens.jsx";
import { Login } from "../features/auth/Login.jsx";
import { PhotoPicker } from "../features/scan/PhotoPicker.jsx";
import { mockApi } from "../services/api/mockApi.js";
import { isDemoMode } from "../services/api/flaskApi.js";
import "../styles/global.css";
import "../styles/flow.css";
import "../styles/login.css";

export function App() {
  const {
    showLogin,
    setShowLogin,
    screen,
    setScreen,
    origin,
    setOrigin,
    stage,
    setStage,
    photos,
    addPhotos,
    removePhoto,
    scan,
    suggestions,
    priceData,
    selectedRecipe,
    selectedStore,
    setSelectedStore,
    saved,
    setSaved,
    preferences,
    preferencesSaved,
    loading,
    error,
    setError,
    toast,
    ingredientIds,
    runScan,
    getRecipes,
    openRecipe,
    chooseRecipe,
    exportList,
    toggleSaved,
    savePreferences,
    resetScan,
    goToPreviousStep,
    activeRecipe,
    setActiveRecipe,
    title,
    subtitle,
    locateStores,
  } = useAppController();

  if (showLogin) return <Login onDemo={() => setShowLogin(false)} />;

  return (
    <div className="app-shell">
      <AppNavigation
        screen={screen}
        savedCount={saved.length}
        apiUrl={mockApi.baseUrl}
        onNavigate={(nextScreen) => {
          setScreen(nextScreen);
          setError("");
        }}
      />
      <main className="main-area">
        <header className="topbar">
          <span>
            REFOOD <i>/</i>{" "}
            {destinations.find((item) => item.id === screen)?.label}
          </span>
          <span className="api-state">
            <i /> {isDemoMode ? "Démo interactive" : "API Flask"}
          </span>
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">
                REFOOD <span>·</span> MA CUISINE
              </p>
              <h1>{title}</h1>
              <p className="subtitle">{subtitle}</p>
            </div>
          </div>
          {error && (
            <AlertBanner onDismiss={() => setError("")}>{error}</AlertBanner>
          )}
          {screen === "scan" && (
            <>
              <div className="stepper">
                {["Scan", "Ingrédients", "Recettes", "Magasins", "Export"].map(
                  (item, i) => (
                    <div
                      key={item}
                      className={`step ${i === stage ? "current" : ""} ${i < stage ? "done" : ""}`}
                    >
                      <span>{i < stage ? "✓" : i + 1}</span>
                      {item}
                    </div>
                  ),
                )}
              </div>
              {stage > 0 && (
                <button
                  className="text-button previous-step"
                  onClick={goToPreviousStep}
                >
                  ← Étape précédente
                </button>
              )}
              {stage === 0 &&
                (loading ? (
                  <WaitPanel
                    title="Analyse de votre photo"
                    detail="Repérage des aliments visibles…"
                  />
                ) : (
                  <div className="scan-start">
                    <section className="panel upload-panel">
                      <div className="upload-heading">
                        <span className="camera-mark">▧</span>
                        <div>
                          <h2>Ajoutez des photos de vos aliments</h2>
                          <p>
                            Choisissez une image et vérifiez les aliments détectés.
                          </p>
                        </div>
                      </div>
                      <PhotoPicker
                        photos={photos}
                        onAdd={addPhotos}
                        onRemove={removePhoto}
                        disabled={loading}
                      />
                      <button
                        className="button primary full"
                        disabled={!photos.length || loading}
                        onClick={runScan}
                      >
                        Analyser la photo →
                      </button>
                    </section>
                    <aside className="scan-help">
                      <h3>Comment ça marche ?</h3>
                      <ol>
                        <li>
                          <span>1</span>Ajoutez une ou plusieurs photos des
                          aliments visibles.
                        </li>
                        <li>
                          <span>2</span>Vérifiez et corrigez les suggestions.
                        </li>
                        <li>
                          <span>3</span>Choisissez une recette et un magasin.
                        </li>
                      </ol>
                      <p>
                        Les quantités exactes ne sont pas déduites d’une image.
                        Vous pourrez les modifier avant de confirmer.
                      </p>
                    </aside>
                  </div>
                ))}
              {stage === 1 && scan && (
                <>
                  <section className="panel candidate-panel">
                    <div className="section-heading">
                      <div>
                        <h2>Aliments repérés</h2>
                        <p>
                          Cochez ceux à garder. Vous pouvez corriger le nom ou
                          la quantité.
                        </p>
                      </div>
                    </div>
                    {scan.warnings.map((warning) => (
                      <div className="warning" key={warning}>
                        ⓘ &nbsp;{warning}
                      </div>
                    ))}
                    <CandidateEditor
                      key={scan.scan_id}
                      scan={scan}
                      onConfirm={getRecipes}
                      loading={loading}
                    />
                  </section>
                </>
              )}
              {stage === 2 && (
                <>
                  <div className="results-bar">
                    <span>
                      {suggestions.length} idées de recettes{" "}
                      <small>· ingrédients confirmés seulement</small>
                    </span>
                  </div>
                  <RecipeGrid
                    recipes={suggestions}
                    saved={saved}
                    onOpen={openRecipe}
                    onToggle={toggleSaved}
                  />
                  <div className="results-footnote">
                    Les préférences sont appliquées localement. Les données inconnues ne satisfont pas les filtres actifs. Vérifiez les quantités et les informations alimentaires avant de cuisiner.
                  </div>
                </>
              )}
              {stage === 3 &&
                (loading ? (
                  <WaitPanel
                    title="Comparaison des magasins"
                    detail="Recherche des offres…"
                  />
                ) : !priceData ? (
                  <section className="panel">
                    <p>La comparaison est indisponible.</p>
                    <button
                      className="button secondary"
                      onClick={() => {
                        if (scan?.candidates) setStage(2);
                        else setScreen("saved");
                      }}
                    >
                      Retour aux recettes
                    </button>
                  </section>
                ) : (
                  <StoreScreen
                    recipe={selectedRecipe}
                    ingredientIds={ingredientIds}
                    priceData={priceData}
                    selectedStore={selectedStore}
                    setSelectedStore={setSelectedStore}
                    onLocate={locateStores}
                    onContinue={() => setStage(4)}
                  />
                ))}
              {stage === 4 && (
                <ExportScreen
                  recipe={selectedRecipe}
                  ingredientIds={ingredientIds}
                  priceData={priceData}
                  selectedStore={selectedStore}
                  origin={origin}
                  setOrigin={setOrigin}
                  onDownload={exportList}
                  onRestart={resetScan}
                />
              )}
            </>
          )}
          {screen === "saved" && (
            <RecipeLibrary
              saved={saved}
              onOpen={openRecipe}
              onToggle={toggleSaved}
              onChanged={async () =>
                setSaved((await mockApi.getFavorites()).items)
              }
            />
          )}
          {screen === "preferences" && preferences && (
            <PreferencesPanel
              preferences={preferences}
              onSave={savePreferences}
              loading={loading}
              saved={preferencesSaved}
            />
          )}
        </div>
      </main>
      {activeRecipe && (
        <RecipeDetails
          recipe={activeRecipe}
          onClose={() => setActiveRecipe(null)}
          onChoose={() => chooseRecipe(activeRecipe)}
          saved={saved.some((item) => item.id === activeRecipe.id)}
          onToggle={() => toggleSaved(activeRecipe)}
        />
      )}
      {toast && (
        <div className="toast" role="status">
          ✓ &nbsp;{toast}
        </div>
      )}
    </div>
  );
}

function WaitPanel({ title, detail }) {
  return (
    <section className="panel wait-panel" aria-live="polite">
      <div
        className="wait-wheel"
        role="status"
        aria-label="Traitement en cours"
      />
      <h2>{title}</h2>
      <p>{detail}</p>
      {isDemoMode && <small>Cette démo utilise un délai simulé.</small>}
    </section>
  );
}
