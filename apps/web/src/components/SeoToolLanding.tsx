"use client";

import { useEffect, useState } from "react";
import { HomeTool } from "@/components/HomeTool";
import styles from "@/app/seo-page.module.css";
import { useLanguage } from "@/i18n/LanguageProvider";
import { getCurrentUser, getUsage, persistAuthSession, type UsageInfo } from "@/lib/api";
import type { ConversionSeoPage, DownloadSeoPage } from "@/lib/toolSeoPages";

function SeoCreditsBadge() {
  const { language } = useLanguage();
  const [usage, setUsage] = useState<UsageInfo | null>(null);

  useEffect(() => {
    let active = true;
    const token = window.localStorage.getItem("polaryix:auth-token");
    const localPremium = window.localStorage.getItem("polaryix:isPremium") === "true";
    const localPlan = window.localStorage.getItem("polaryix:premiumPlan") ?? "basic";

    async function loadUsage() {
      let isPremium = localPremium;
      let premiumPlan = localPlan;

      if (token) {
        try {
          const { user } = await getCurrentUser();
          persistAuthSession({ token, user });
          isPremium = user.is_premium;
          premiumPlan = user.plan;
        } catch {
          // Keep the anonymous/free usage fallback.
        }
      }

      try {
        const currentUsage = await getUsage({ isPremium, premiumPlan });
        if (active) setUsage(currentUsage);
      } catch {
        if (active) setUsage(null);
      }
    }

    loadUsage();

    return () => {
      active = false;
    };
  }, []);

  if (!usage) {
    return null;
  }

  const formatted = new Intl.NumberFormat(language).format(usage.remaining);
  const label = language.startsWith("pt") ? `${formatted} creditos restantes` : `${formatted} credits remaining`;

  return <span className={styles.creditBadge}>{label}</span>;
}

export function ConversionSeoLanding({ page }: { page: ConversionSeoPage }) {
  const { language } = useLanguage();
  const isPortuguese = language.startsWith("pt");
  const title = isPortuguese ? `Conversor ${page.source} para ${page.target}` : `${page.source} to ${page.target} Converter`;
  const description = isPortuguese
    ? `Converta arquivos ${page.source} para ${page.target} online com o PolarYix. A ferramenta abaixo usa o conversor seguro existente com ${page.source} para ${page.target} ja selecionado.`
    : page.description;

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.heroTop}>
          <p className={styles.eyebrow}>{isPortuguese ? "Conversor de arquivos" : page.eyebrow}</p>
          <SeoCreditsBadge />
        </div>
        <h1>{title}</h1>
        <p>{description}</p>
      </section>

      <HomeTool toolMode="converter" initialFromFormat={page.source} initialToFormat={page.target} />

      <section className={styles.details} aria-label="FAQ">
        <h2>FAQ</h2>
        {isPortuguese ? (
          <>
            <p><strong>Como converter {page.source} para {page.target}?</strong> Selecione o arquivo no conversor acima. O PolarYix mantem as mesmas validacoes, regras de creditos e fluxo seguro do conversor principal.</p>
            <p><strong>Essa pagina cria uma ferramenta nova?</strong> Nao. Ela usa a ferramenta existente com os formatos ja selecionados.</p>
          </>
        ) : (
          <>
            <p><strong>How do I convert {page.source} to {page.target}?</strong> Select your file in the converter above. PolarYix keeps the same validation, credit rules and secure backend flow used by the main converter.</p>
            <p><strong>Is this a separate tool?</strong> No. This page uses the existing converter with the formats already selected.</p>
          </>
        )}
      </section>
    </div>
  );
}

export function DownloadSeoLanding({ page }: { page: DownloadSeoPage }) {
  const { language } = useLanguage();
  const isPortuguese = language.startsWith("pt");
  const providerLabel = page.provider === "youtube" ? "YouTube" : "TikTok";
  const formatLabel = page.format.toUpperCase();
  const title = isPortuguese ? `${providerLabel} para ${formatLabel}` : `${providerLabel} to ${formatLabel} Downloader`;
  const description = isPortuguese
    ? `Cole um link publico do ${providerLabel} e prepare ${formatLabel} com a ferramenta de download por link existente do PolarYix.`
    : page.description;

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.heroTop}>
          <p className={styles.eyebrow}>{isPortuguese ? "Download por link" : page.eyebrow}</p>
          <SeoCreditsBadge />
        </div>
        <h1>{title}</h1>
        <p>{description}</p>
      </section>

      <HomeTool toolMode="download" initialDownloadFormat={page.format} />

      <section className={styles.details} aria-label="FAQ">
        <h2>FAQ</h2>
        {isPortuguese ? (
          <>
            <p><strong>Como usar {providerLabel} para {formatLabel}?</strong> Cole um link publico suportado na ferramenta acima e escolha {formatLabel}. O PolarYix mantem as mesmas validacoes e limites do download principal.</p>
            <p><strong>Por que um link publico pode falhar?</strong> Plataformas como YouTube e TikTok podem bloquear downloads por regras externas, cookies, IP ou verificacao anti-bot. Quando isso acontece, o PolarYix mostra uma mensagem controlada.</p>
          </>
        ) : (
          <>
            <p><strong>How do I use {providerLabel} to {formatLabel}?</strong> Paste a supported public link in the tool above and choose {formatLabel}. PolarYix keeps the same backend checks and limits as the main download tool.</p>
            <p><strong>Why can a public link fail?</strong> Platforms like YouTube and TikTok may block downloads because of external rules, cookies, IP reputation or anti-bot checks. When that happens, PolarYix shows a controlled message.</p>
          </>
        )}
      </section>
    </div>
  );
}
