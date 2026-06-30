"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useLanguage } from "@/i18n/LanguageProvider";
import { getPublicStats, type PublicStats } from "@/lib/api";
import styles from "./Footer.module.css";

export function Footer() {
  const { language } = useLanguage();
  const [stats, setStats] = useState<PublicStats | null>(null);
  const isPortuguese = language.startsWith("pt");

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

  const formattedTotal = total === null ? "..." : new Intl.NumberFormat(language).format(total);

  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <section className={styles.counter} aria-label={isPortuguese ? "Conversoes realizadas" : "Completed conversions"}>
          <p>
            {isPortuguese ? "Convertemos " : "Converted "}
            <strong>{formattedTotal}</strong>
            {isPortuguese ? " arquivos" : " files"}
          </p>
        </section>

        <nav className={styles.columns} aria-label={isPortuguese ? "Links do rodape" : "Footer links"}>
          <div>
            <Link href="/premium">Premium</Link>
            <Link href="/credits">{isPortuguese ? "Creditos" : "Credits"}</Link>
            <Link href="/donate">{isPortuguese ? "Doar" : "Donate"}</Link>
          </div>
          <div>
            <Link href="/image-tools">{isPortuguese ? "Ferramentas de imagem" : "Image tools"}</Link>
            <Link href="/workspace">Workspace</Link>
            <Link href="/dashboard">Dashboard</Link>
          </div>
          <div>
            <Link href="/security">Security</Link>
            <Link href="/terms">{isPortuguese ? "Termos de uso" : "Terms of Use"}</Link>
          </div>
        </nav>

        <div className={styles.bottom}>
          <p>© 2026 PolarYix. {isPortuguese ? "Todos os direitos reservados." : "All rights reserved."}</p>
          <p>{isPortuguese ? "Pagamentos protegidos. O PolarYix nao armazena dados de cartao." : "Protected payments. PolarYix does not store card data."}</p>
        </div>
      </div>
    </footer>
  );
}
