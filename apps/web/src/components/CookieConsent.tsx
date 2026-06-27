"use client";

import { useEffect, useState } from "react";
import styles from "./CookieConsent.module.css";

type CookiePreferences = {
  essential: true;
  analytics: boolean;
  preferences: boolean;
  marketing: boolean;
};

const STORAGE_KEY = "polaryix:cookie-consent";
const DEFAULT_PREFERENCES: CookiePreferences = {
  essential: true,
  analytics: false,
  preferences: false,
  marketing: false,
};

function savePreferences(preferences: CookiePreferences) {
  const payload = {
    ...preferences,
    acceptedAt: new Date().toISOString(),
    version: 1,
  };

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  document.cookie = `polaryix_cookie_consent=${encodeURIComponent(JSON.stringify(payload))}; Max-Age=31536000; Path=/; SameSite=Lax`;
  window.dispatchEvent(new CustomEvent("polaryix-cookie-consent", { detail: payload }));
}

export function CookieConsent() {
  const [isVisible, setIsVisible] = useState(false);
  const [isCustomizing, setIsCustomizing] = useState(false);
  const [preferences, setPreferences] = useState<CookiePreferences>(DEFAULT_PREFERENCES);

  useEffect(() => {
    setIsVisible(!window.localStorage.getItem(STORAGE_KEY));
  }, []);

  function acceptAll() {
    savePreferences({
      essential: true,
      analytics: true,
      preferences: true,
      marketing: true,
    });
    setIsVisible(false);
  }

  function rejectOptional() {
    savePreferences(DEFAULT_PREFERENCES);
    setIsVisible(false);
  }

  function saveCustom() {
    savePreferences(preferences);
    setIsVisible(false);
  }

  if (!isVisible) {
    return null;
  }

  return (
    <div className={styles.backdrop} role="dialog" aria-modal="true" aria-labelledby="cookie-title">
      <section className={styles.panel}>
        <div className={styles.copy}>
          <p>Privacidade e cookies</p>
          <h2 id="cookie-title">Permissão de cookies do Polaryix</h2>
          <span>
            Usamos cookies essenciais para o site funcionar e cookies opcionais para lembrar preferências, medir conversões,
            downloads e melhorar recursos como histórico, limites grátis e experiência premium.
          </span>
        </div>

        {isCustomizing ? (
          <div className={styles.options}>
            <label>
              <input type="checkbox" checked disabled />
              <span>
                <strong>Essenciais</strong>
                Login, segurança, limites diários e funcionamento básico.
              </span>
            </label>
            <label>
              <input
                type="checkbox"
                checked={preferences.preferences}
                onChange={(event) => setPreferences((current) => ({ ...current, preferences: event.target.checked }))}
              />
              <span>
                <strong>Preferências</strong>
                Idioma, formatos favoritos e ajustes da interface.
              </span>
            </label>
            <label>
              <input
                type="checkbox"
                checked={preferences.analytics}
                onChange={(event) => setPreferences((current) => ({ ...current, analytics: event.target.checked }))}
              />
              <span>
                <strong>Analytics</strong>
                Páginas acessadas, botões clicados e formatos mais usados.
              </span>
            </label>
            <label>
              <input
                type="checkbox"
                checked={preferences.marketing}
                onChange={(event) => setPreferences((current) => ({ ...current, marketing: event.target.checked }))}
              />
              <span>
                <strong>Marketing</strong>
                Medição de campanhas, origem do usuário e ofertas premium.
              </span>
            </label>
          </div>
        ) : null}

        <div className={styles.actions}>
          {isCustomizing ? (
            <button type="button" className={styles.primary} onClick={saveCustom}>
              Salvar escolhas
            </button>
          ) : (
            <button type="button" className={styles.primary} onClick={acceptAll}>
              Aceitar todos
            </button>
          )}
          <button type="button" onClick={rejectOptional}>
            Recusar opcionais
          </button>
          <button type="button" onClick={() => setIsCustomizing((current) => !current)}>
            {isCustomizing ? "Voltar" : "Personalizar"}
          </button>
        </div>
      </section>
    </div>
  );
}
