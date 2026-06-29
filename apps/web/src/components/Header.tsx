"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLanguage } from "@/i18n/LanguageProvider";
import { languages, type Language } from "@/i18n/translations";
import type { AuthUser } from "@/lib/api";
import { logout } from "@/lib/api";
import { useTheme, type ThemePreference } from "@/theme/ThemeProvider";
import styles from "./Header.module.css";

const conversionGroups = [
  { titleKey: "nav.images", items: ["PNG para DDS", "JPG para PNG", "WEBP para PNG", "TIFF para JPG"] },
  { titleKey: "nav.videos", items: ["MP4 para WEBM", "MOV para MP4", "AVI para MP4", "MKV para MP4"] },
  { titleKey: "nav.audios", items: ["MP3 para WAV", "WAV para MP3", "AAC para MP3", "OGG para MP3"] },
  { titleKey: "nav.documents", items: ["PDF para DOCX", "DOCX para PDF", "XLSX para CSV", "PPTX para PDF"] },
  { titleKey: "nav.archives", items: ["ZIP", "RAR", "7Z", "TAR"] },
  { titleKey: "nav.others", items: ["SVG", "ICO", "JSON", "XML"] },
];

const imageTools = [
  { href: "/image/remove-background", titleKey: "image.removeBackground.title", descriptionKey: "nav.transparentPng" },
  { href: "/image/optimize", titleKey: "image.optimize.title", descriptionKey: "nav.smallerFile" },
  { href: "/image/upscale", titleKey: "image.upscale.title", descriptionKey: "nav.moreResolution" },
];

export function Header() {
  const { language, setLanguage, t } = useLanguage();
  const { theme, appliedTheme, setTheme } = useTheme();
  const [isConversionsOpen, setIsConversionsOpen] = useState(false);
  const [isImageToolsOpen, setIsImageToolsOpen] = useState(false);
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
    setIsImageToolsOpen(false);
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
          aria-label={isMobileMenuOpen ? t("nav.closeMenu") : t("nav.openMenu")}
          aria-expanded={isMobileMenuOpen}
          aria-controls="primary-navigation"
        >
          <span />
          <span />
          <span />
        </button>

        <nav id="primary-navigation" className={`${styles.nav} ${isMobileMenuOpen ? styles.navOpen : ""}`} aria-label={t("nav.mainNavigation")}>
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
              {t("nav.conversions")}
            </button>

            <div className={styles.conversionsDropdown}>
              {conversionGroups.map((group) => (
                <section key={group.titleKey}>
                  <h3>{t(group.titleKey)}</h3>
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

          {user ? (
            <>
              <Link href="/files" className={styles.navLink} onClick={closeMenus}>
                {t("nav.files")}
              </Link>
              <Link href="/dashboard" className={styles.navLink} onClick={closeMenus}>
                {t("nav.dashboard")}
              </Link>
              <Link href="/workspace" className={styles.navLink} onClick={closeMenus}>
                {t("nav.workspace")}
              </Link>
            </>
          ) : null}

          <div
            className={`${styles.navItem} ${isImageToolsOpen ? styles.open : ""}`}
            onMouseEnter={() => setIsImageToolsOpen(true)}
            onMouseLeave={() => setIsImageToolsOpen(false)}
          >
            <button
              type="button"
              className={styles.navLink}
              onClick={() => setIsImageToolsOpen((current) => !current)}
              aria-expanded={isImageToolsOpen}
            >
              {t("nav.imageEditing")}
            </button>
            <div className={styles.imageDropdown}>
              {imageTools.map((tool) => (
                <Link href={tool.href} key={tool.href} onClick={closeMenus}>
                  <span aria-hidden="true">▣</span>
                  <strong>{t(tool.titleKey)}</strong>
                  <small>{t(tool.descriptionKey)}</small>
                </Link>
              ))}
            </div>
          </div>

          <div className={styles.compactControls}>
            <label>
              <span>{appliedTheme === "dark" ? "☾" : "☀"} {t("nav.theme")}</span>
              <select value={theme} onChange={(event) => setTheme(event.target.value as ThemePreference)} aria-label={t("nav.theme")}>
                <option value="light">{t("nav.light")}</option>
                <option value="dark">{t("nav.dark")}</option>
                <option value="system">{t("nav.system")}</option>
              </select>
            </label>
            <label>
              <span>{t("nav.language")}</span>
              <select value={language} onChange={(event) => setLanguage(event.target.value as Language)} aria-label={t("nav.language")}>
                {Object.entries(languages).map(([key, value]) => (
                  <option key={key} value={key}>
                    {value.shortLabel}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {user ? (
            <button type="button" className={styles.loginButton} onClick={handleLogout}>
              {user.avatar_url ? <img src={user.avatar_url} alt="" className={styles.avatar} /> : null}
              {user.plan === "free" ? t("nav.logout") : `${user.plan} - ${t("nav.logout")}`}
            </button>
          ) : (
            <Link href="/login" className={styles.loginButton} onClick={closeMenus}>
              {t("nav.login")}
            </Link>
          )}
          <Link href="/premium" className={styles.signupButton} onClick={closeMenus}>
            {t("nav.premium")}
          </Link>
        </nav>
      </div>
    </header>
  );
}
