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
