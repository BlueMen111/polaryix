"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { resendVerificationEmail } from "@/lib/api";
import styles from "../login/page.module.css";

export default function ResendVerificationPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setStatus("Enviando novo link...");
    try {
      const data = await resendVerificationEmail(email);
      setStatus(data.message);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel reenviar o link.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <div className={styles.header}>
          <p>PolarYix Account</p>
          <h1>Reenviar verificacao</h1>
          <span>Informe seu e-mail para receber um novo link de verificacao.</span>
        </div>
        <form onSubmit={handleSubmit} className={styles.form}>
          <label>
            E-mail
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="voce@email.com" required />
          </label>
          <button type="submit" className={styles.submitButton} disabled={isSubmitting}>
            {isSubmitting ? "Enviando..." : "Reenviar link"}
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
