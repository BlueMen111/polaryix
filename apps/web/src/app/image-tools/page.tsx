"use client";

import Link from "next/link";
import { useLanguage } from "@/i18n/LanguageProvider";
import styles from "./page.module.css";

const tools = [
  {
    href: "/image/remove-background",
    titleKey: "image.removeBackground.title",
    descriptionKey: "image.removeBackground.description",
    cost: "1 token",
  },
  {
    href: "/image/optimize",
    titleKey: "image.optimize.title",
    descriptionKey: "image.optimize.description",
    cost: "2 tokens",
  },
  {
    href: "/image/upscale",
    titleKey: "image.upscale.title",
    descriptionKey: "image.upscale.description",
    cost: "5 ou 10 tokens",
  },
];

export default function ImageToolsPage() {
  const { t } = useLanguage();

  return (
    <main className={styles.page}>
      <section className={styles.header}>
        <p>{t("nav.imageEditing")}</p>
        <h1>{t("imageTools.title")}</h1>
        <span>{t("imageTools.subtitle")}</span>
      </section>

      <section className={styles.grid}>
        {tools.map((tool) => (
          <Link href={tool.href} className={styles.card} key={tool.href}>
            <div className={styles.cardHeader}>
              <span>{tool.cost}</span>
              <h2>{t(tool.titleKey)}</h2>
              <p>{t(tool.descriptionKey)}</p>
            </div>
            <strong>{t("imageTools.openTool")}</strong>
          </Link>
        ))}
      </section>
    </main>
  );
}
