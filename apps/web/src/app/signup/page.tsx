"use client";

import { useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      alert("As senhas não coincidem");
      return;
    }
    // TODO: Implementar cadastro
    console.log("Cadastro:", { name, email, password });
  };

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.card}>
          <div className={styles.header}>
            <h1>Crie sua conta</h1>
            <p>Comece a transformar seus dados hoje</p>
          </div>

          <form onSubmit={handleSubmit} className={styles.form}>
            <div className={styles.inputGroup}>
              <label htmlFor="name">Nome completo</label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="João Silva"
                required
                className={styles.input}
              />
            </div>

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
                minLength={8}
                className={styles.input}
              />
              <span className={styles.hint}>Mínimo de 8 caracteres</span>
            </div>

            <div className={styles.inputGroup}>
              <label htmlFor="confirmPassword">Confirmar senha</label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                required
                className={styles.input}
              />
            </div>

            <div className={styles.terms}>
              <label className={styles.checkbox}>
                <input type="checkbox" required />
                <span>
                  Aceito os <a href="/terms">Termos de Uso</a> e{" "}
                  <a href="/privacy">Política de Privacidade</a>
                </span>
              </label>
            </div>

            <button type="submit" className={styles.submitButton}>
              Criar Conta Gratuita
            </button>
          </form>

          <div className={styles.footer}>
            <p>
              Já tem uma conta? <Link href="/login">Faça login</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}