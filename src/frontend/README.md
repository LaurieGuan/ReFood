# REFOOD frontend

React + Vite application written in JavaScript. This frontend lives separately from the Python backend in `src/backend` and the existing prototype in `local-work`.

## Start the development server

```bash
cd src/frontend
npm install
npm run dev
```

Tailwind CSS is loaded in the browser from its CDN script in `index.html`; there is no Tailwind build or PostCSS step. The CDN is suitable for prototyping and requires an internet connection in the browser.

## Source layout

The React source is organized by responsibility:

- `src/app/` composes the application and its navigation.
- `src/features/` contains UI specific to scanning and recipes.
- `src/components/` is reserved for reusable layout and UI components.
- `src/services/api/` isolates the API contract and demo implementation.
- `src/hooks/` holds shared application state: scan session, favorites, and preferences.
- `src/utils/` and `src/styles/` hold shared helpers and global styles.

`App.jsx` coordinates the current multi-step flow. Keep the scan session, favorites, and preferences in their focused hooks as additional screens are introduced; promote other state only when it is reused across screens.

## Flask et mode démo

Par défaut, le frontend utilise Flask sur `http://127.0.0.1:5000` via le proxy Vite `/api/v1`. Démarrez le backend suivant `src/backend/README.md`, puis lancez `npm run dev` dans ce dossier. Le scan nécessite `VISION_API_KEY` et `VISION_MODEL` dans l’environnement du backend. La recherche de produits nécessite l’accès HTTPS à Épiceries.ca et un magasin de certificats Python valide. Les résultats de recherche de produits sont des propositions à vérifier auprès du détaillant.

Pour activer explicitement les données fictives du parcours, démarrez Vite avec `VITE_REFOOD_DEMO=true npm run dev` (ou définissez `localStorage.setItem('refood-demo-mode', 'true')` dans le navigateur et rechargez). Pour revenir à Flask, retirez cette clé et démarrez Vite sans la variable. La connexion démo, les préférences, les recettes personnelles et les favoris restent locaux au navigateur; ils ne sont pas persistés par Flask. Le garde-manger est envoyé à Flask, dont le stockage peut être en mémoire si aucune base de données n’est configurée. Les préférences sont appliquées localement aux résultats et les champs inconnus ne satisfont pas les filtres actifs.

Les noms manuels sont normalisés côté frontend selon `services/normalizer.py`, car aucune route de normalisation n’est exposée; ces deux règles doivent rester synchronisées. Les instructions, ingrédients manquants, quantités et prix sont adaptés depuis les schémas Pydantic existants. Sans `DATABASE_URL`, les recettes renvoyées par le backend sont son catalogue de démonstration.
