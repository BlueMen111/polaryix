"use client";

import { useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implementar login
    console.log("Login:", { email, password });
  };

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.card}>
          <div className={styles.header}>
            <h1>Bem-vindo de volta</h1>
            <p>Entre na sua conta para continuar</p>
          </div>

          <form onSubmit={handleSubmit} className={styles.form}>
            <div className={styles.inputGroup}>
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                className={styles.input}
              />
            </div>

            <div className={styles.inputGroup}>
              <label htmlFor="password">Senha</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className={styles.input}
              />
            </div>

            <div className={styles.options}>
              <label className={styles.checkbox}>
                <input type="checkbox" />
                <span>Lembrar de mim</span>
              </label>
              <Link href="/forgot-password" className={styles.forgotPassword}>
                Esqueceu a senha?
              </Link>
            </div>

            <button type="submit" className={styles.submitButton}>
              Entrar
            </button>
          </form>

          <div className={styles.footer}>
            <p>
              Não tem uma conta? <Link href="/signup">Cadastre-se</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}