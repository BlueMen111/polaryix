import type { Metadata } from "next";
import Link from "next/link";
import styles from "../../seo-page.module.css";

export const metadata: Metadata = {
  title: "PNG to DDS Converter | PolarYix",
  description: "Convert PNG images to DDS online with PolarYix. Prepare textures and game assets directly in your browser.",
  alternates: { canonical: "/convert/png-to-dds" },
};

export default function PngToDdsPage() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Texture converter</p>
        <h1>PNG to DDS Converter</h1>
        <p>Convert PNG images to DDS online with PolarYix. Prepare textures and game assets directly in your browser.</p>
        <div className={styles.actions}>
          <Link className={styles.primary} href="/#converter">
            Use PNG to DDS converter
          </Link>
          <Link className={styles.secondary} href="/convert/dds-to-png">
            DDS to PNG
          </Link>
        </div>
      </section>
      <section className={styles.details}>
        <h2>Prepare texture assets</h2>
        <p>Use PolarYix to convert common image files into DDS format for texture workflows, previews and asset pipelines.</p>
      </section>
    </main>
  );
}
