"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/i18n/LanguageProvider";
import { getCurrentUser, loginWithEmail, persistAuthSession, startGoogleLogin } from "@/lib/api";
import styles from "./page.module.css";

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l3.66-2.84z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06L5.84 9.9C6.71 7.3 9.14 5.38 12 5.38z" />
    </svg>
  );
}

export default function LoginPage() {
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const authError = params.get("auth_error");

    if (authError) {
      const messages: Record<string, string> = {
        google_config: t("auth.googleConfig"),
        missing_code: t("auth.googleMissingCode"),
        google: t("auth.googleError"),
      };
      setStatus(messages[authError] ?? t("auth.googleError"));
      return;
    }
    if (!token) {
      return;
    }

    window.localStorage.setItem("polaryix:auth-token", token);
    getCurrentUser()
      .then(({ user }) => {
        persistAuthSession({ token, user });
        window.location.href = "/";
      })
      .catch(() => setStatus(t("auth.googleExpired")));
  }, [t]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setIsSubmitting(true);
    setStatus(t("auth.loggingIn"));

    try {
      const session = await loginWithEmail({ email, password });
      persistAuthSession(session);
      setStatus(t("auth.loginDone"));
      window.location.href = "/";
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("auth.loginError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.card} aria-labelledby="login-title">
        <div className={styles.header}>
          <p>{t("auth.loginEyebrow")}</p>
          <h1 id="login-title">{t("auth.loginHeading")}</h1>
          <span>{t("auth.loginSubtitle")}</span>
        </div>

        <div className={styles.socialRow} aria-label={t("auth.socialLogin")}>
          <button type="button" className={styles.googleButton} aria-label={t("auth.loginWithGoogle")} onClick={startGoogleLogin}>
            <GoogleIcon />
          </button>
        </div>

        <div className={styles.divider}>
          <span>{t("auth.emailDivider")}</span>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <label>
            E-mail
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="seu@email.com" required />
          </label>

          <label>
            {t("auth.password")}
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder={t("auth.passwordPlaceholder")} required />
          </label>

          <div className={styles.formFooter}>
            <Link href="/signup">{t("auth.createAccount")}</Link>
          </div>

          <button type="submit" className={styles.submitButton} disabled={isSubmitting}>
            {isSubmitting ? t("auth.loggingIn") : t("auth.login")}
          </button>
        </form>

        {status ? <p className={styles.status}>{status}</p> : null}

        <p className={styles.footerText}>
          {t("auth.noAccount")} <Link href="/signup">{t("auth.signupFree")}</Link>
        </p>
      </section>
    </main>
  );
}
