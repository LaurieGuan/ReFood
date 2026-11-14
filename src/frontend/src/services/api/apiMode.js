// The URL records a deliberate choice for this session; legacy storage flags are ignored.
export function resolveDemoMode(search = '', configured = false) {
  const mode = new URLSearchParams(search).get('api_mode');
  return mode === 'demo' || (mode !== 'live' && configured === true);
}
export const isDemoMode = resolveDemoMode(globalThis.location?.search, import.meta.env?.VITE_REFOOD_DEMO === 'true');
export function switchApiMode(demo) {
  const url = new URL(window.location.href);
  url.searchParams.set('api_mode', demo ? 'demo' : 'live');
  window.location.assign(url.href);
}
