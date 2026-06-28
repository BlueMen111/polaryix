"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { persistAuthSession, signupWithEmail, startGoogleLogin } from "@/lib/api";
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

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (password !== confirmPassword) {
      setStatus("As senhas nao coincidem.");
      return;
    }

    if (!termsAccepted) {
      setStatus("Aceite os termos de uso para criar sua conta.");
      return;
    }

    setIsSubmitting(true);
    setStatus("Criando sua conta...");

    try {
      const session = await signupWithEmail({ name, email, password, termsAccepted });
      persistAuthSession(session);
      setStatus("Conta criada. Redirecionando...");
      window.location.href = "/";
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel criar a conta.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.card} aria-labelledby="signup-title">
        <div className={styles.header}>
          <p>Comece gratis</p>
          <h1 id="signup-title">Crie sua conta Polaryix</h1>
          <span>Guarde preferencias, acompanhe historico e libere o caminho para o Premium.</span>
        </div>

        <div className={styles.socialRow} aria-label="Opcoes de cadastro social">
          <button type="button" className={styles.googleButton} aria-label="Cadastrar com Google" onClick={startGoogleLogin}>
            <GoogleIcon />
          </button>
        </div>

        <div className={styles.divider}>
          <span>ou cadastre com e-mail</span>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <label>
            Nome
            <input type="text" value={name} onChange={(event) => setName(event.target.value)} placeholder="Seu nome" required minLength={2} />
          </label>

          <label>
            E-mail
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="seu@email.com" required />
          </label>

          <label>
            Senha
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Minimo de 8 caracteres" required minLength={8} />
          </label>

          <label>
            Confirmar senha
            <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Repita sua senha" required />
          </label>

          <label className={styles.terms}>
            <input type="checkbox" required checked={termsAccepted} onChange={(event) => setTermsAccepted(event.target.checked)} />
            <span>
              Aceito os termos de uso e a politica de privacidade. <Link href="/terms">Saiba mais</Link>
            </span>
          </label>

          <button type="submit" className={styles.submitButton} disabled={isSubmitting}>
            {isSubmitting ? "Criando..." : "Criar conta gratuita"}
          </button>
        </form>

        {status ? <p className={styles.status}>{status}</p> : null}

        <p className={styles.footerText}>
          Ja tem conta? <Link href="/login">Entrar agora</Link>
        </p>
      </section>
    </main>
  );
}
