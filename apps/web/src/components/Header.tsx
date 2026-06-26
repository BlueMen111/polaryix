"use client";

import Link from "next/link";
import styles from "./Header.module.css";

export function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <Link href="/" className={styles.logo}>
          <img 
            src="/assets/logos/logo-sem-fundo.png" 
            alt="Polaryix" 
            className={styles.logoImage}
          />
        </Link>

        <nav className={styles.nav}>
          <Link href="/upload" className={styles.navLink}>
            Nova Análise
          </Link>
          <Link href="/datasets" className={styles.navLink}>
            Meus Dashboards
          </Link>
          <button className={styles.loginButton}>Login</button>
          <button className={styles.signupButton}>Cadastrar</button>
        </nav>
      </div>
    </header>
  );
}
