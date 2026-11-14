import React, { useState } from 'react';

export function Login({ onDemo }) {
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState('');

  function handleSubmit(event) {
    event.preventDefault();
    setMessage('La connexion sera disponible lorsque le service de comptes sera prêt.');
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
        <h2>Heureux de vous revoir.</h2>
        <p className="login-subtitle">Connectez-vous pour retrouver votre cuisine.</p>
        <form className="login-form" onSubmit={handleSubmit}>
          <label htmlFor="login-email">Adresse courriel</label>
          <input id="login-email" name="email" type="email" placeholder="vous@exemple.com" autoComplete="email" required />
          <label htmlFor="login-password">Mot de passe</label>
          <div className="login-password"><input id="login-password" name="password" type={showPassword ? 'text' : 'password'} placeholder="Votre mot de passe" autoComplete="current-password" required /><button type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}>{showPassword ? 'Masquer' : 'Afficher'}</button></div>
          {message && <p className="login-message" role="status">{message}</p>}
          <button className="login-submit" type="submit">Se connecter <span>→</span></button>
        </form>
        <div className="login-divider"><span>ou</span></div>
        <button className="login-demo" type="button" onClick={onDemo}>Découvrir la démo <span>→</span></button>
        <p className="login-footnote">La démo est accessible sans compte.</p>
      </div>
      <p className="login-bottom">REFOOD · POUR UNE CUISINE PLUS MALIGNE</p>
    </section>
  </main>;
}
