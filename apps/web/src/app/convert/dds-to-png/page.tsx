import type { Metadata } from "next";
import Link from "next/link";
import styles from "../../seo-page.module.css";

export const metadata: Metadata = {
  title: "DDS to PNG Converter | PolarYix",
  description: "Convert DDS files to PNG online with PolarYix. Upload your DDS file and download a PNG version quickly.",
  alternates: { canonical: "/convert/dds-to-png" },
};

export default function DdsToPngPage() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Image converter</p>
        <h1>DDS to PNG Converter</h1>
        <p>Convert DDS files to PNG online with PolarYix. Upload your DDS file and download a PNG version quickly.</p>
        <div className={styles.actions}>
          <Link className={styles.primary} href="/#converter">
            Use DDS to PNG converter
          </Link>
          <Link className={styles.secondary} href="/convert/png-to-dds">
            PNG to DDS
          </Link>
        </div>
      </section>
      <section className={styles.details}>
        <h2>Convert game textures quickly</h2>
        <p>PolarYix helps you prepare DDS texture files for previews, sharing and editing by converting them to PNG in your browser workflow.</p>
      </section>
    </main>
  );
}
