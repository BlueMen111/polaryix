"use client";

import { useEffect, useMemo, useState } from "react";
import { useLanguage } from "@/i18n/LanguageProvider";
import { downloadMyFile, listMyFiles, type ConvertedFile } from "@/lib/api";
import styles from "./page.module.css";

function formatBytes(value: number) {
  if (!value) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value: string, locale: string) {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(status: ConvertedFile["status"], t: (key: string) => string) {
  const labels: Record<ConvertedFile["status"], string> = {
    queued: t("common.queued"),
    processing: t("common.processing"),
    completed: t("common.completed"),
    failed: t("common.error"),
    expired: t("common.expired"),
    deleted: t("files.removed"),
  };
  return labels[status] ?? status;
}

export default function FilesPage() {
  const { language, t } = useLanguage();
  const [files, setFiles] = useState<ConvertedFile[]>([]);
  const [status, setStatus] = useState(t("files.loading"));
  const [downloadingId, setDownloadingId] = useState("");

  const isLoggedIn = useMemo(() => {
    if (typeof window === "undefined") {
      return false;
    }

    return Boolean(window.localStorage.getItem("polaryix:auth-token"));
  }, []);

  useEffect(() => {
    if (!isLoggedIn) {
      setStatus(t("files.loginRequired"));
      return;
    }

    listMyFiles()
      .then((data) => {
        setFiles(data.files);
        setStatus(data.files.length ? "" : t("files.empty"));
      })
      .catch((error) => {
        setStatus(error instanceof Error ? error.message : t("files.loadError"));
      });
  }, [isLoggedIn, t]);

  async function handleDownload(file: ConvertedFile) {
    setDownloadingId(file.id);
    setStatus("");
    try {
      await downloadMyFile(file);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("files.downloadError"));
    } finally {
      setDownloadingId("");
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.panel}>
        <div className={styles.header}>
          <div>
            <p className={styles.eyebrow}>{t("files.eyebrow")}</p>
            <h1>{t("files.title")}</h1>
            <p>{t("files.subtitle")}</p>
          </div>
          <a className={styles.primaryLink} href="/">
            {t("files.newConversion")}
          </a>
        </div>

        {status ? <p className={styles.message}>{status}</p> : null}

        {files.length ? (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>{t("files.file")}</th>
                  <th>{t("files.format")}</th>
                  <th>{t("files.status")}</th>
                  <th>{t("files.size")}</th>
                  <th>{t("files.date")}</th>
                  <th>{t("files.quality")}</th>
                  <th aria-label={t("files.actions")} />
                </tr>
              </thead>
              <tbody>
                {files.map((file) => {
                  const canDownload = file.status === "completed" && Boolean(file.download_url);
                  return (
                    <tr key={file.id}>
                      <td>
                        <strong>{file.original_filename}</strong>
                        {file.error_message ? <span>{file.error_message}</span> : null}
                      </td>
                      <td>
                        {file.original_format} {t("files.to")} {file.target_format}
                      </td>
                      <td>
                        <span className={`${styles.badge} ${styles[file.status]}`}>{statusLabel(file.status, t)}</span>
                      </td>
                      <td>{formatBytes(Number(file.file_size || 0))}</td>
                      <td>{formatDate(file.created_at, language)}</td>
                      <td>{file.quality_delivered || file.quality_requested || "-"}</td>
                      <td>
                        {canDownload ? (
                          <button type="button" onClick={() => handleDownload(file)} disabled={downloadingId === file.id}>
                            {downloadingId === file.id ? t("files.downloading") : t("common.download")}
                          </button>
                        ) : (
                          <em>{t("files.unavailable")}</em>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </main>
  );
}
