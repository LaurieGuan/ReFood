import React, { useState } from 'react';

export function Login({ onDemo }) {
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState('');
  const [view, setView] = useState('login');

  function changeView(next) {
    setView(next);
    setMessage('');
    setShowPassword(false);
  }

  function handleSubmit(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    if (view === 'register' && data.get('password') !== data.get('confirm_password')) {
      setMessage('Les mots de passe ne correspondent pas.');
      return;
    }
    setMessage(view === 'forgot'
      ? 'La réinitialisation du mot de passe n’est pas encore disponible. Aucun courriel n’a été envoyé.'
      : view === 'register'
        ? 'La création de compte n’est pas encore disponible. Aucun compte n’a été créé.'
        : 'La connexion sera disponible lorsque le service de comptes sera prêt.');
  }

  return <main className="login-page">
    <section className="login-intro" aria-label="Présentation de Refood">
      <div className="login-brand"><span className="login-brand-mark">r.</span> refood<span>.</span></div>
      <div className="login-intro-copy">
        <p className="login-kicker">MOINS DE GASPILLAGE, PLUS D’IDÉES</p>
        <h1>Bien manger commence dans votre frigo<span>.</span></h1>
        <p>Transformez les ingrédients que vous avez déjà en repas que vous aimerez.</p>
        <div className="login-illustration" aria-hidden="true"><span>🥬</span><span>🍅</span><span>🥕</span></div>
      </div>
      <p className="login-intro-footer">Une petite action pour votre cuisine et pour la planète.</p>
    </section>
    <section className="login-main">
      <div className="login-card">
        <p className="login-kicker">BIENVENUE CHEZ REFOOD</p>
        <h2>{view === 'login' ? 'Heureux de vous revoir.' : view === 'register' ? 'Bienvenue chez Refood.' : 'Mot de passe oublié ?'}</h2>
        <p className="login-subtitle">{view === 'login' ? 'Connectez-vous pour retrouver votre cuisine.' : view === 'register' ? 'Créez votre compte pour retrouver votre cuisine.' : 'Indiquez votre adresse courriel pour réinitialiser votre mot de passe.'}</p>
        <form key={view} className="login-form" onSubmit={handleSubmit}>
          {view === 'register' && <><label htmlFor="login-name">Nom</label><input id="login-name" name="name" type="text" autoComplete="name" placeholder="Votre nom" required /></>}
          <label htmlFor="login-email">Adresse courriel</label>
          <input id="login-email" name="email" type="email" placeholder="vous@exemple.com" autoComplete="email" required />
          {view !== 'forgot' && <><label htmlFor="login-password">Mot de passe</label>
          <div className="login-password"><input id="login-password" name="password" type={showPassword ? 'text' : 'password'} placeholder="Votre mot de passe" autoComplete={view === 'register' ? 'new-password' : 'current-password'} minLength={view === 'register' ? 8 : undefined} required /><button type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}>{showPassword ? 'Masquer' : 'Afficher'}</button></div></>}
          {view === 'register' && <><label htmlFor="confirm-password">Confirmer le mot de passe</label><input id="confirm-password" name="confirm_password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" minLength={8} required /><small className="login-hint">Au moins 8 caractères.</small></>}
          {view === 'login' && <button className="login-link login-forgot" type="button" onClick={() => changeView('forgot')}>Mot de passe oublié ?</button>}
          {message && <p className="login-message" role="status">{message}</p>}
          <button className="login-submit" type="submit">{view === 'login' ? 'Se connecter' : view === 'register' ? 'Créer mon compte' : 'Réinitialiser le mot de passe'} <span>→</span></button>
        </form>
        <p className="login-account">{view === 'login' ? 'Pas encore de compte ? ' : 'Vous avez déjà un compte ? '}<button className="login-link" type="button" onClick={() => changeView(view === 'login' ? 'register' : 'login')}>{view === 'login' ? 'Créer un compte' : 'Se connecter'}</button></p>
        <div className="login-divider"><span>ou</span></div>
        <button className="login-demo" type="button" onClick={onDemo}>Découvrir la démo <span>→</span></button>
        <p className="login-footnote">La démo est accessible sans compte.</p>
      </div>
      <p className="login-bottom">REFOOD · POUR UNE CUISINE PLUS MALIGNE</p>
    </section>
  </main>;
}
