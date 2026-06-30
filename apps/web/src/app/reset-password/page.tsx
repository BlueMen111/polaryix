"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { resetPassword } from "@/lib/api";
import styles from "../login/page.module.css";

export default function ResetPasswordPage() {
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setToken(new URLSearchParams(window.location.search).get("token") || "");
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      setStatus("Link de redefinicao ausente. Solicite um novo link.");
      return;
    }
    if (password !== confirmPassword) {
      setStatus("As senhas nao coincidem.");
      return;
    }

    setIsSubmitting(true);
    setStatus("Redefinindo senha...");
    try {
      const data = await resetPassword({ token, password });
      setStatus(data.message);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel redefinir a senha.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <div className={styles.header}>
          <p>PolarYix Account</p>
          <h1>Nova senha</h1>
          <span>Crie uma nova senha com pelo menos 8 caracteres.</span>
        </div>
        <form onSubmit={handleSubmit} className={styles.form}>
          <label>
            Nova senha
            <span className={styles.passwordField}>
              <input type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} />
              <button type="button" onClick={() => setShowPassword((current) => !current)}>
                {showPassword ? "Ocultar" : "Exibir"}
              </button>
            </span>
          </label>
          <label>
            Confirmar senha
            <input type={showPassword ? "text" : "password"} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required minLength={8} />
          </label>
          <button type="submit" className={styles.submitButton} disabled={isSubmitting}>
            {isSubmitting ? "Salvando..." : "Redefinir senha"}
          </button>
        </form>
        {status ? <p className={styles.status}>{status}</p> : null}
        <p className={styles.footerText}>
          <Link href="/login">Entrar</Link>
        </p>
      </section>
    </main>
  );
}
