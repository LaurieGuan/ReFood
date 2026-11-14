import React, { useState } from 'react';
import { mockAuth } from '../../services/api/mockAuth.js';

export function Account({ user, onChange }) {
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true); setError('');
    try {
      const credentials = { name: String(form.get('name') || ''), email: String(form.get('email') || ''), password: String(form.get('password') || '') };
      onChange(await (registering ? mockAuth.register(credentials) : mockAuth.login(credentials)));
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  if (user) return <section className="panel account-panel"><h2>Votre compte</h2><p>{user.name} · {user.email}</p><button className="button secondary" onClick={async () => { await mockAuth.logout(); onChange(null); }}>Se déconnecter</button><p className="contract-note">Compte de démonstration conservé dans ce navigateur.</p></section>;
  return <section className="panel account-panel"><h2>{registering ? 'Créer un compte' : 'Connexion'}</h2><p>Utilisez un compte de démonstration pour cette session.</p>{error && <p className="error-banner" role="alert">{error}</p>}<form onSubmit={submit} className="account-form">{registering && <label>Nom<input name="name" autoComplete="name" required /></label>}<label>Courriel<input type="email" name="email" autoComplete="email" required /></label><label>Mot de passe<input type="password" name="password" minLength="8" autoComplete={registering ? 'new-password' : 'current-password'} required /></label><button className="button primary" disabled={busy}>{busy ? 'Chargement…' : registering ? 'Créer le compte' : 'Se connecter'}</button></form><button className="text-button" onClick={() => { setRegistering(!registering); setError(''); }}>{registering ? 'Vous avez déjà un compte ? Se connecter' : 'Créer un compte'}</button><p className="contract-note">La connexion est simulée et les comptes sont enregistrés uniquement sur cet appareil.</p></section>;
}
