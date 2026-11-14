import { useEffect, useState } from 'react';
import { mockApi } from '../services/api/mockApi.js';
export function usePreferences() {
  const [preferences, setPreferences] = useState(null);
  const [preferencesSaved, setPreferencesSaved] = useState(false);
  useEffect(() => { mockApi.getPreferences().then(setPreferences).catch(() => {}); }, []);
  return { preferences, setPreferences, preferencesSaved, setPreferencesSaved };
}
