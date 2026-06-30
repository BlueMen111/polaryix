"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { verifyEmailToken } from "@/lib/api";
import styles from "../login/page.module.css";

export default function VerifyEmailPage() {
  const [status, setStatus] = useState("Verificando seu e-mail...");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token") || "";
    if (!token) {
      setStatus("Link de verificacao ausente. Solicite um novo link.");
      return;
    }

    verifyEmailToken(token)
      .then((data) => setStatus(data.message || "E-mail verificado com sucesso."))
      .catch((error) => setStatus(error instanceof Error ? error.message : "Nao foi possivel verificar o e-mail."));
  }, []);

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <div className={styles.header}>
          <p>PolarYix Account</p>
          <h1>Verificar e-mail</h1>
          <span>{status}</span>
        </div>
        <p className={styles.footerText}>
          <Link href="/login">Entrar</Link> ou <Link href="/resend-verification">reenviar link</Link>
        </p>
      </section>
    </main>
  );
}
