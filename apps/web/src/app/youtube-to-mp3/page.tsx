import type { Metadata } from "next";
import Link from "next/link";
import styles from "../seo-page.module.css";

export const metadata: Metadata = {
  title: "YouTube to MP3 Converter | PolarYix",
  description: "Convert YouTube videos to MP3 audio online with PolarYix.",
  alternates: { canonical: "/youtube-to-mp3" },
};

export default function YoutubeToMp3Page() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Download by link</p>
        <h1>YouTube to MP3 Converter</h1>
        <p>Convert YouTube videos to MP3 audio online with PolarYix.</p>
        <div className={styles.actions}>
          <Link className={styles.primary} href="/#download-link">
            Use YouTube to MP3
          </Link>
          <Link className={styles.secondary} href="/youtube-to-mp4">
            YouTube to MP4
          </Link>
        </div>
      </section>
      <section className={styles.details}>
        <h2>Extract audio from public links</h2>
        <p>Paste a supported YouTube link, choose MP3 and prepare the file. Availability may depend on YouTube restrictions and server access.</p>
      </section>
    </main>
  );
}
