"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { requestPasswordReset } from "@/lib/api";
import styles from "../login/page.module.css";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setStatus("Enviando link de redefinicao...");
    try {
      const data = await requestPasswordReset(email);
      setStatus(data.message);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel solicitar a redefinicao.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <div className={styles.header}>
          <p>PolarYix Account</p>
          <h1>Recuperar senha</h1>
          <span>Enviaremos um link seguro para redefinir sua senha.</span>
        </div>
        <form onSubmit={handleSubmit} className={styles.form}>
          <label>
            E-mail
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="voce@email.com" required />
          </label>
          <button type="submit" className={styles.submitButton} disabled={isSubmitting}>
            {isSubmitting ? "Enviando..." : "Enviar link"}
          </button>
        </form>
        {status ? <p className={styles.status}>{status}</p> : null}
        <p className={styles.footerText}>
          <Link href="/login">Voltar para login</Link>
        </p>
      </section>
    </main>
  );
}
