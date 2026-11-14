import React, { useEffect, useRef, useState } from 'react';

// Google's public test key always passes; replace it with a real v2 site key.
const TEST_SITE_KEY = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI';
const siteKey = import.meta.env.VITE_RECAPTCHA_SITE_KEY || TEST_SITE_KEY;
let scriptPromise;

function loadRecaptcha() {
  if (window.grecaptcha?.render) return Promise.resolve(window.grecaptcha);
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      window.refoodRecaptchaReady = () => resolve(window.grecaptcha);
      const script = document.createElement('script');
      script.src = 'https://www.google.com/recaptcha/api.js?onload=refoodRecaptchaReady&render=explicit';
      script.async = true;
      script.defer = true;
      script.onerror = () => reject(new Error('Chargement impossible'));
      document.head.appendChild(script);
    });
  }
  return scriptPromise;
}

export function Recaptcha({ onChange }) {
  const container = useRef(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    let widget;
    loadRecaptcha().then((captcha) => {
      if (!active || !container.current) return;
      widget = captcha.render(container.current, {
        sitekey: siteKey,
        callback: (token) => onChange(token),
        'expired-callback': () => onChange(''),
        'error-callback': () => { onChange(''); setFailed(true); },
      });
    }).catch(() => { if (active) setFailed(true); });
    return () => {
      active = false;
      if (widget !== undefined && window.grecaptcha?.reset) window.grecaptcha.reset(widget);
    };
  }, [onChange]);

  return <div className="login-captcha">
    <div ref={container} />
    {!import.meta.env.VITE_RECAPTCHA_SITE_KEY && <small>reCAPTCHA de test — non destiné à la production.</small>}
    {failed && <p className="login-message" role="alert">Impossible de charger reCAPTCHA. Vérifiez votre connexion et réessayez.</p>}
  </div>;
}
