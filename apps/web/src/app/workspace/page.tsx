"use client";

import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { useLanguage } from "@/i18n/LanguageProvider";
import {
  convertWorkspaceFile,
  deleteWorkspaceFile,
  downloadWorkspaceFile,
  favoriteWorkspaceFile,
  listWorkspaceFiles,
  processWorkspaceImage,
  uploadWorkspaceFiles,
  type StorageSummary,
  type WorkspaceFile,
} from "@/lib/api";
import styles from "./page.module.css";

const filters = [
  { id: "all", labelKey: "workspace.all" },
  { id: "favorites", labelKey: "workspace.favorites" },
  { id: "expired", labelKey: "workspace.expired" },
] as const;

function formatBytes(value?: number | null) {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value: string | null | undefined, locale: string) {
  if (!value) return "-";
  return new Intl.DateTimeFormat(locale, { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function statusLabel(status: WorkspaceFile["status"], t: (key: string) => string) {
  const labels: Record<WorkspaceFile["status"], string> = {
    queued: t("common.queued"),
    processing: t("common.processing"),
    completed: t("common.completed"),
    failed: t("common.failed"),
    expired: t("common.expired"),
    deleted: t("common.deleted"),
  };
  return labels[status] ?? status;
}

export default function WorkspacePage() {
  const { language, t } = useLanguage();
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [storage, setStorage] = useState<StorageSummary | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<(typeof filters)[number]["id"]>("all");
  const [status, setStatus] = useState(t("workspace.loading"));
  const [busyId, setBusyId] = useState("");
  const [targetFormats, setTargetFormats] = useState<Record<string, string>>({});
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);

  const storageText = useMemo(() => {
    if (!storage) return t("workspace.storageLoading");
    return t("workspace.storageUsage", { used: formatBytes(storage.used), limit: formatBytes(storage.limit) });
  }, [storage, t]);

  useEffect(() => {
    if (!window.localStorage.getItem("polaryix:auth-token")) {
      window.location.href = "/login";
      return;
    }
    refresh();
  }, [filter]);

  async function refresh(nextQuery = query) {
    try {
      const data = await listWorkspaceFiles({ q: nextQuery, filter });
      setFiles(data.files);
      setStorage(data.storage);
      setStatus(data.files.length ? "" : t("workspace.empty"));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("workspace.loadError"));
    }
  }

  async function handleFavorite(file: WorkspaceFile) {
    setBusyId(file.id);
    try {
      await favoriteWorkspaceFile(file.id, !file.is_favorite);
      await refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("workspace.favoriteError"));
    } finally {
      setBusyId("");
    }
  }

  async function handleDelete(file: WorkspaceFile) {
    setBusyId(file.id);
    try {
      const result = await deleteWorkspaceFile(file.id);
      setStorage(result.storage);
      setFiles((current) => current.filter((item) => item.id !== file.id));
      await refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("workspace.deleteError"));
    } finally {
      setBusyId("");
    }
  }

  async function handleDownload(file: WorkspaceFile) {
    setBusyId(file.id);
    try {
      await downloadWorkspaceFile(file);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("workspace.downloadError"));
    } finally {
      setBusyId("");
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!selected.length) return;
    setStatus(t("workspace.uploading"));
    try {
      const result = await uploadWorkspaceFiles(selected);
      setStorage(result.storage);
      await refresh();
      setStatus(t("workspace.uploaded", { count: selected.length }));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("workspace.uploadError"));
    }
  }

  async function handleConvert(file: WorkspaceFile) {
    const target = (targetFormats[file.id] || "").trim();
    if (!target) {
      setStatus(t("workspace.targetFormatRequired"));
      return;
    }
    setBusyId(file.id);
    try {
      await convertWorkspaceFile(file.id, target);
      await refresh();
      setStatus(t("workspace.conversionQueued", { format: target.toUpperCase() }));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("workspace.conversionError"));
    } finally {
      setBusyId("");
    }
  }

  async function handleImageTool(file: WorkspaceFile, operation: "remove_background" | "optimize_image" | "upscale_image") {
    setBusyId(file.id);
    try {
      await processWorkspaceImage(file.id, operation, 2);
      await refresh();
      setStatus(t("workspace.imageQueued"));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("workspace.imageError"));
    } finally {
      setBusyId("");
    }
  }

  function isImage(file: WorkspaceFile) {
    return ["png", "jpg", "jpeg", "webp"].includes(String(file.extension || file.target_format || "").toLowerCase());
  }

  return (
    <main className={styles.page}>
      <section className={styles.headerPanel}>
        <div>
          <p className={styles.eyebrow}>{t("workspace.eyebrow")}</p>
          <h1>{t("workspace.title")}</h1>
          <p>{t("workspace.subtitle")}</p>
        </div>
        <div className={styles.storageCard}>
          <strong>{t("dashboard.storage")}</strong>
          <span>{storageText}</span>
          <i style={{ width: `${Math.min(storage?.percent ?? 0, 100)}%` }} />
          <small>{storage?.retention_hours === 24 ? t("workspace.premiumRetention") : t("workspace.freeRetention")}</small>
        </div>
      </section>

      <section className={styles.toolbar}>
        <input ref={fileInputRef} className={styles.hiddenInput} type="file" multiple onChange={handleUpload} />
        <input ref={folderInputRef} className={styles.hiddenInput} type="file" multiple onChange={handleUpload} {...{ webkitdirectory: "", directory: "" }} />
        <input
          value={query}
          placeholder={t("workspace.searchPlaceholder")}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") refresh(event.currentTarget.value);
          }}
        />
        <button type="button" onClick={() => refresh()}>{t("common.search")}</button>
        <button type="button" onClick={() => fileInputRef.current?.click()}>{t("workspace.uploadFiles")}</button>
        <button type="button" onClick={() => folderInputRef.current?.click()}>{t("workspace.uploadFolder")}</button>
        <div>
          {filters.map((item) => (
            <button key={item.id} type="button" className={filter === item.id ? styles.activeFilter : undefined} onClick={() => setFilter(item.id)}>
              {t(item.labelKey)}
            </button>
          ))}
        </div>
      </section>

      {status ? <p className={styles.message}>{status}</p> : null}

      {files.length ? (
        <section className={styles.grid}>
          {files.map((file) => {
            const canDownload = file.status === "completed" && Boolean(file.download_url);
            return (
              <article key={file.id} className={styles.fileCard}>
                <div className={styles.fileTop}>
                  <span>{file.extension || file.target_format || t("common.file")}</span>
                  <button type="button" onClick={() => handleFavorite(file)} disabled={busyId === file.id} aria-label={file.is_favorite ? t("common.unfavorite") : t("common.favorite")}>
                    {file.is_favorite ? "★" : "☆"}
                  </button>
                </div>
                <strong>{file.original_filename}</strong>
                <p>{file.operation_type || file.target_format} - {formatBytes(file.size_bytes ?? file.file_size)}</p>
                <div className={styles.meta}>
                  <span className={styles[file.status]}>{statusLabel(file.status, t)}</span>
                  <span>{t("workspace.expiresAt", { date: formatDate(file.expires_at, language) })}</span>
                </div>
                <div className={styles.actions}>
                  <button type="button" onClick={() => handleDownload(file)} disabled={!canDownload || busyId === file.id}>{t("common.download")}</button>
                  <button type="button" onClick={() => handleDelete(file)} disabled={busyId === file.id}>{t("common.delete")}</button>
                </div>
                {file.status === "completed" ? (
                  <div className={styles.reuseBox}>
                    <div>
                      <input
                        value={targetFormats[file.id] ?? ""}
                        placeholder={t("workspace.convertTo")}
                        onChange={(event) => setTargetFormats((current) => ({ ...current, [file.id]: event.target.value }))}
                      />
                      <button type="button" onClick={() => handleConvert(file)} disabled={busyId === file.id}>{t("common.convert")}</button>
                    </div>
                    {isImage(file) ? (
                      <div>
                        <button type="button" onClick={() => handleImageTool(file, "optimize_image")} disabled={busyId === file.id}>{t("common.optimize")}</button>
                        <button type="button" onClick={() => handleImageTool(file, "remove_background")} disabled={busyId === file.id}>{t("common.removeBackground")}</button>
                        <button type="button" onClick={() => handleImageTool(file, "upscale_image")} disabled={busyId === file.id}>{t("common.upscale")}</button>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </article>
            );
          })}
        </section>
      ) : null}
    </main>
  );
}
