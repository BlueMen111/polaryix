"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { AuthUser } from "@/lib/api";
import { logout } from "@/lib/api";
import styles from "./Header.module.css";

const conversionGroups = [
  { title: "Imagens", items: ["PNG para DDS", "JPG para PNG", "WEBP para PNG", "TIFF para JPG"] },
  { title: "Videos", items: ["MP4 para WEBM", "MOV para MP4", "AVI para MP4", "MKV para MP4"] },
  { title: "Audios", items: ["MP3 para WAV", "WAV para MP3", "AAC para MP3", "OGG para MP3"] },
  { title: "Documentos", items: ["PDF para DOCX", "DOCX para PDF", "XLSX para CSV", "PPTX para PDF"] },
  { title: "Arquivos", items: ["ZIP", "RAR", "7Z", "TAR"] },
  { title: "Outros", items: ["SVG", "ICO", "JSON", "XML"] },
];

export function Header() {
  const [isConversionsOpen, setIsConversionsOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const rawUser = window.localStorage.getItem("polaryix:user");
    if (rawUser) {
      try {
        setUser(JSON.parse(rawUser));
      } catch {
        setUser(null);
      }
    }
  }, []);

  async function handleLogout() {
    await logout();
    setUser(null);
    setIsMobileMenuOpen(false);
    window.location.href = "/";
  }

  function closeMenus() {
    setIsConversionsOpen(false);
    setIsMobileMenuOpen(false);
  }

  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <Link href="/" className={styles.logo} aria-label="Polaryix" onClick={closeMenus}>
          <img
            src="/assets/polaryix-logo.png"
            alt="Polaryix"
            className={styles.logoImage}
            onError={(event) => {
              event.currentTarget.src = "/assets/logos/logo-sem-fundo.png";
            }}
          />
        </Link>

        <button
          type="button"
          className={`${styles.menuButton} ${isMobileMenuOpen ? styles.menuButtonOpen : ""}`}
          onClick={() => setIsMobileMenuOpen((current) => !current)}
          aria-label={isMobileMenuOpen ? "Fechar menu" : "Abrir menu"}
          aria-expanded={isMobileMenuOpen}
          aria-controls="primary-navigation"
        >
          <span />
          <span />
          <span />
        </button>

        <nav id="primary-navigation" className={`${styles.nav} ${isMobileMenuOpen ? styles.navOpen : ""}`} aria-label="Navegacao principal">
          <div
            className={`${styles.navItem} ${isConversionsOpen ? styles.open : ""}`}
            onMouseEnter={() => setIsConversionsOpen(true)}
            onMouseLeave={() => setIsConversionsOpen(false)}
          >
            <button
              type="button"
              className={styles.navLink}
              onClick={() => setIsConversionsOpen((current) => !current)}
              aria-expanded={isConversionsOpen}
            >
              Conversoes
            </button>

            <div className={styles.conversionsDropdown}>
              {conversionGroups.map((group) => (
                <section key={group.title}>
                  <h3>{group.title}</h3>
                  <div>
                    {group.items.map((item) => (
                      <a href="/#converter" key={item} onClick={closeMenus}>
                        {item}
                      </a>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </div>

          <Link href="/files" className={styles.navLink} onClick={closeMenus}>
            Meus arquivos
          </Link>
          <Link href="/image-tools" className={styles.navLink} onClick={closeMenus}>
            Ferramentas
          </Link>
          {user ? (
            <button type="button" className={styles.loginButton} onClick={handleLogout}>
              {user.avatar_url ? <img src={user.avatar_url} alt="" className={styles.avatar} /> : null}
              {user.plan === "free" ? "Sair" : `${user.plan} - Sair`}
            </button>
          ) : (
            <Link href="/login" className={styles.loginButton} onClick={closeMenus}>
              Login
            </Link>
          )}
          <Link href="/premium" className={styles.signupButton} onClick={closeMenus}>
            Premium
          </Link>
        </nav>
      </div>
    </header>
  );
}
