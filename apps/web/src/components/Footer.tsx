"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useLanguage } from "@/i18n/LanguageProvider";
import { getPublicStats, type PublicStats } from "@/lib/api";
import styles from "./Footer.module.css";

export function Footer() {
  const { language } = useLanguage();
  const [stats, setStats] = useState<PublicStats | null>(null);

  useEffect(() => {
    let active = true;
    getPublicStats()
      .then((data) => {
        if (active) setStats(data);
      })
      .catch(() => {
        if (active) setStats(null);
      });
    return () => {
      active = false;
    };
  }, []);

  const total = useMemo(() => {
    if (!stats) return null;
    return stats.total_conversions + stats.total_image_tools + stats.total_downloads;
  }, [stats]);

  const formattedTotal = total === null ? "" : new Intl.NumberFormat(language).format(total);
  const isPortuguese = language.startsWith("pt");

  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.brand}>
          <strong>PolarYix</strong>
          <p>
            {isPortuguese
              ? "Conversoes e ferramentas de imagem com privacidade: estatisticas publicas nunca expõem arquivos ou usuarios."
              : "Conversions and image tools with privacy: public stats never expose files or users."}
          </p>
          {total !== null ? (
            <p className={styles.stats}>
              {isPortuguese ? "Mais de " : "More than "}
              <strong>{formattedTotal}</strong>
              {isPortuguese ? " conversoes realizadas no PolarYix." : " conversions completed on PolarYix."}
            </p>
          ) : null}
        </div>

        <nav className={styles.links} aria-label={isPortuguese ? "Links do rodape" : "Footer links"}>
          <Link href="/premium">Premium</Link>
          <Link href="/credits">{isPortuguese ? "Creditos" : "Credits"}</Link>
          <Link href="/donate">{isPortuguese ? "Doar" : "Donate"}</Link>
          <Link href="/terms">{isPortuguese ? "Termos" : "Terms"}</Link>
        </nav>
      </div>
    </footer>
  );
}
