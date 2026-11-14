# REFOOD frontend

React + Vite application written in JavaScript. This frontend lives separately from the Python backend in `src/backend` and the existing prototype in `local-work`.

## Start the development server

```bash
cd src/frontend
npm install
npm run dev
```

The login forms use Google reCAPTCHA v2. For local demonstration, the public
Google test key is used and always passes. Set `VITE_RECAPTCHA_SITE_KEY` to a
real v2 site key for your domain; restart Vite after changing it. Authentication
is not implemented yet: the future backend must verify the response token with
Google using a secret key stored only on the server. The test key does not
provide bot protection.

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

## Demonstration data and limitations

The React app uses local mock services in `src/services/api/`. Recipes, favorites, preferences and custom ingredients persist in browser storage. Ingredients confirmed during a scan are kept only for the current session.

Diet choices and illustrative recipe metadata are configured in `src/data/`, as are the fictional store locations and product prices. Recipe search excludes unknown values when a corresponding filter is active; dietary and price data are illustrative and must not be treated as verified. The photo scan returns predefined candidates and requires confirmation. Store distances are straight-line estimates from browser geolocation, and the export includes a Maps directions link.
