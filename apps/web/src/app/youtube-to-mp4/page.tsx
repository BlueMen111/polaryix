import type { Metadata } from "next";
import Link from "next/link";
import styles from "../seo-page.module.css";

export const metadata: Metadata = {
  title: "YouTube to MP4 Converter | PolarYix",
  description: "Convert YouTube videos to MP4 online with PolarYix.",
  alternates: { canonical: "/youtube-to-mp4" },
};

export default function YoutubeToMp4Page() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Download by link</p>
        <h1>YouTube to MP4 Converter</h1>
        <p>Convert YouTube videos to MP4 online with PolarYix.</p>
        <div className={styles.actions}>
          <Link className={styles.primary} href="/#download-link">
            Use YouTube to MP4
          </Link>
          <Link className={styles.secondary} href="/youtube-to-mp3">
            YouTube to MP3
          </Link>
        </div>
      </section>
      <section className={styles.details}>
        <h2>Prepare MP4 downloads</h2>
        <p>Use PolarYix to prepare public YouTube videos as MP4 files when the platform allows server-side extraction.</p>
      </section>
    </main>
  );
}
