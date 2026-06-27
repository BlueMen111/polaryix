"use client";

import Link from "next/link";
import { useState } from "react";
import styles from "./Header.module.css";

const conversionGroups = [
  { title: "Imagens", items: ["PNG para DDS", "JPG para PNG", "WEBP para PNG", "TIFF para JPG"] },
  { title: "Vídeos", items: ["MP4 para WEBM", "MOV para MP4", "AVI para MP4", "MKV para MP4"] },
  { title: "Áudios", items: ["MP3 para WAV", "WAV para MP3", "AAC para MP3", "OGG para MP3"] },
  { title: "Documentos", items: ["PDF para DOCX", "DOCX para PDF", "XLSX para CSV", "PPTX para PDF"] },
  { title: "Arquivos", items: ["ZIP", "RAR", "7Z", "TAR"] },
  { title: "Outros", items: ["SVG", "ICO", "JSON", "XML"] },
];

export function Header() {
  const [isConversionsOpen, setIsConversionsOpen] = useState(false);

  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <Link href="/" className={styles.logo} aria-label="Polaryix">
          <img
            src="/assets/polaryix-logo.png"
            alt="Polaryix"
            className={styles.logoImage}
            onError={(event) => {
              event.currentTarget.src = "/assets/logos/logo-sem-fundo.png";
            }}
          />
        </Link>

        <nav className={styles.nav} aria-label="Navegação principal">
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
              Conversões
            </button>

            <div className={styles.conversionsDropdown}>
              {conversionGroups.map((group) => (
                <section key={group.title}>
                  <h3>{group.title}</h3>
                  <div>
                    {group.items.map((item) => (
                      <a href="/#converter" key={item}>
                        {item}
                      </a>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </div>

          <Link href="/files" className={styles.navLink}>
            Meus arquivos
          </Link>
          <Link href="/login" className={styles.loginButton}>
            Login
          </Link>
          <Link href="/signup" className={styles.signupButton}>
            Premium
          </Link>
        </nav>
      </div>
    </header>
  );
}
