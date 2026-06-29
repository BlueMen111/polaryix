"use client";

import { ChangeEvent, CSSProperties, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/i18n/LanguageProvider";
import {
  ImageToolJob,
  ImageToolOperation,
  cancelImageToolJob,
  createImageToolJob,
  downloadImageToolJob,
  getCurrentUser,
  getImageToolJob,
  getImageToolJobResult,
  persistAuthSession,
  type AuthUser,
} from "@/lib/api";
import styles from "./ImageToolWorkspace.module.css";

type Props = {
  operation: Exclude<ImageToolOperation, "remaster_image">;
  title: string;
  eyebrow: string;
  description: string;
  cost: string;
};

type FileInfo = {
  width: number;
  height: number;
  format: string;
  size: number;
};

export function ImageToolWorkspace({ operation, title, eyebrow, description, cost }: Props) {
  const { t } = useLanguage();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [fileInfo, setFileInfo] = useState<FileInfo | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [resultUrl, setResultUrl] = useState("");
  const [resultFilename, setResultFilename] = useState("");
  const [job, setJob] = useState<ImageToolJob | null>(null);
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [scale, setScale] = useState<2 | 4>(2);
  const [keepOriginalSize, setKeepOriginalSize] = useState(false);
  const [sharpness, setSharpness] = useState(1.45);
  const [denoise, setDenoise] = useState(0.25);
  const [contrast, setContrast] = useState(1.08);
  const [detail, setDetail] = useState(1.2);
  const [intensity, setIntensity] = useState(1);

  const isPremium = Boolean(user?.is_premium);
  const active = job?.status === "queued" || job?.status === "processing";
  const costNumber = operation === "remove_background" ? 1 : operation === "optimize_image" ? 2 : isPremium && scale === 4 ? 10 : 5;
  const credits = user?.credits_remaining;
  const insufficientCredits = typeof credits === "number" && credits < costNumber;
  const statusText = job ? statusLabel(job, t) : status;
  const demoClass = operation === "remove_background" ? styles.removeDemo : operation === "optimize_image" ? styles.optimizeDemo : styles.upscaleDemo;

  const localUpscaleStyle = useMemo<CSSProperties>(
    () => ({
      filter: `contrast(${contrast}) saturate(${1 + intensity * 0.08}) brightness(${1 + (detail - 1) * 0.04})`,
      transform: `scale(${1 + Math.min(Math.max(sharpness - 1, 0), 1) * 0.025})`,
    }),
    [contrast, detail, intensity, sharpness]
  );

  const planMessage = useMemo(() => {
    if (isPremium) {
      return t("image.premiumActive");
    }
    if (operation === "upscale_image") {
      return t("image.freeUpscale");
    }
    return t("image.standardQueue");
  }, [isPremium, operation, t]);

  useEffect(() => {
    refreshUser();
  }, []);

  async function refreshUser() {
    const token = window.localStorage.getItem("polaryix:auth-token");
    if (!token) {
      return;
    }

    try {
      const data = await getCurrentUser();
      persistAuthSession({ token, user: data.user });
      setUser(data.user);
    } catch {
      setUser(null);
    }
  }

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      setFileInfo(null);
      return;
    }

    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    const image = new Image();
    image.onload = () => {
      setFileInfo({
        width: image.naturalWidth,
        height: image.naturalHeight,
        format: file.type.replace("image/", "").toUpperCase() || file.name.split(".").pop()?.toUpperCase() || "IMAGEM",
        size: file.size,
      });
    };
    image.src = url;

    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    setResultFilename("");
    setResultUrl((previous) => {
      if (previous) URL.revokeObjectURL(previous);
      return "";
    });
  }, [file, operation]);

  useEffect(() => {
    if (!active || !job) {
      return;
    }

    const interval = window.setInterval(async () => {
      try {
        const updated = await getImageToolJob(job.id);
        setJob(updated);
        setStatus(statusLabel(updated, t));
        if (updated.status === "completed" || updated.status === "failed" || updated.status === "cancelled") {
          refreshUser();
        }
      } catch (error) {
        setStatus(error instanceof Error ? error.message : t("image.statusError"));
      }
    }, 2500);

    return () => window.clearInterval(interval);
  }, [active, job, t]);

  useEffect(() => {
    if (job?.status !== "completed" || resultUrl) {
      return;
    }

    let cancelled = false;
    getImageToolJobResult(job)
      .then((result) => {
        if (cancelled) {
          URL.revokeObjectURL(result.url);
          return;
        }
        setResultUrl(result.url);
        setResultFilename(result.filename);
      })
      .catch((error) => setStatus(error instanceof Error ? error.message : t("image.resultError")));

    return () => {
      cancelled = true;
    };
  }, [job, resultUrl, t]);

  useEffect(() => {
    return () => {
      if (resultUrl) URL.revokeObjectURL(resultUrl);
    };
  }, [resultUrl]);

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
    setJob(null);
    setStatus(selected ? t("image.ready") : "");
  }

  async function handleProcess() {
    if (!user) {
      setStatus(t("image.loginRequired"));
      return;
    }
    if (!file) {
      setStatus(t("image.pickImage"));
      return;
    }
    if (insufficientCredits) {
      setStatus(t("image.insufficientCredits"));
      return;
    }

    setIsSubmitting(true);
    setStatus(t("image.sendingQueue"));
    try {
      const created = await createImageToolJob({
        operation,
        file,
        scale,
        keepOriginalSize,
        sharpness,
        denoise,
        contrast,
        detail,
        intensity,
      });
      setJob(created);
      setStatus(statusLabel(created, t));
      refreshUser();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("workspace.imageError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRefresh() {
    if (!job) return;
    const updated = await getImageToolJob(job.id);
    setJob(updated);
    setStatus(statusLabel(updated, t));
    refreshUser();
  }

  async function handleCancel() {
    if (!job) return;
    const updated = await cancelImageToolJob(job.id);
    setJob(updated);
    setStatus(t("image.cancelledRefund"));
    refreshUser();
  }

  async function handleDownload() {
    if (!job) return;
    const filename = await downloadImageToolJob(job);
    setStatus(t("image.downloadStarted", { filename }));
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <div>
          <p>{eyebrow}</p>
          <h1>{title}</h1>
          <span>{description}</span>
        </div>
        <Link href="/premium">{t("image.learnPremium")}</Link>
      </section>

      <section className={styles.layout}>
        <div className={styles.panel}>
          <div className={styles.topRow}>
            <div className={styles.badgeRow}>
              <strong>{cost}</strong>
              <strong>{typeof credits === "number" ? t("image.creditsRemaining", { credits }) : t("image.loginCredits")}</strong>
            </div>
            <span>{planMessage}</span>
          </div>

          {insufficientCredits ? <p className={styles.creditWarning}>{t("image.insufficientCredits")}</p> : null}

          <label className={styles.uploadBox}>
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={handleFile} />
            <strong>{file?.name ?? t("image.selectImage")}</strong>
            <small>PNG, JPG ou WEBP</small>
          </label>

          {fileInfo ? (
            <div className={styles.fileInfo}>
              <span>{fileInfo.format}</span>
              <span>{formatBytes(fileInfo.size)}</span>
              <span>{fileInfo.width}x{fileInfo.height}</span>
            </div>
          ) : null}

          {operation === "upscale_image" ? (
            <div className={styles.controls}>
              <div className={styles.segmented}>
                <button type="button" className={scale === 2 ? styles.active : undefined} onClick={() => setScale(2)} disabled={!isPremium}>
                  2x
                </button>
                <button type="button" className={scale === 4 ? styles.active : undefined} onClick={() => setScale(4)} disabled={!isPremium}>
                  4x
                </button>
              </div>
              <label className={styles.toggle}>
                <input type="checkbox" checked={keepOriginalSize} onChange={(event) => setKeepOriginalSize(event.target.checked)} disabled={!isPremium} />
                {t("image.keepOriginalSize")}
              </label>
              {isPremium ? (
                <div className={styles.sliders}>
                  <Range label={t("image.sharpness")} value={sharpness} min={0.7} max={2.4} step={0.05} onChange={setSharpness} />
                  <Range label={t("image.denoise")} value={denoise} min={0} max={1} step={0.05} onChange={setDenoise} />
                  <Range label={t("image.contrast")} value={contrast} min={0.8} max={1.6} step={0.05} onChange={setContrast} />
                  <Range label={t("image.details")} value={detail} min={0.8} max={1.8} step={0.05} onChange={setDetail} />
                  <Range label={t("image.intensity")} value={intensity} min={0.4} max={1.6} step={0.05} onChange={setIntensity} />
                  <small>{t("image.localPreviewNote")}</small>
                </div>
              ) : (
                <div className={styles.locked}>{t("image.lockedControls")}</div>
              )}
            </div>
          ) : null}

          <button type="button" className={styles.primaryButton} onClick={handleProcess} disabled={isSubmitting || insufficientCredits}>
            {isSubmitting ? t("image.sending") : t("image.processImage")}
          </button>

          {job ? (
            <div className={styles.jobBox}>
              <strong>{statusLabel(job, t)}</strong>
              {job.queue_position ? <span>{t("image.queuePosition", { position: job.queue_position })}</span> : null}
              {job.credits_cost ? <span>{t("image.tokensCharged", { count: job.credits_cost })}</span> : null}
              {job.original_size || job.final_size ? <span>{formatBytes(job.original_size)} {"->"} {formatBytes(job.final_size)}</span> : null}
              {typeof job.reduction_percent === "number" ? <span>{t("image.reduction", { percent: job.reduction_percent })}</span> : null}
              {resultFilename ? <span>{t("image.fileReady", { filename: resultFilename })}</span> : null}
              {job.message ? <p>{job.message}</p> : null}
              {job.error_message ? <p>{job.error_message}</p> : null}
              <div className={styles.actions}>
                <button type="button" onClick={handleRefresh}>{t("image.refreshStatus")}</button>
                {job.status === "queued" ? <button type="button" onClick={handleCancel}>{t("common.cancel")}</button> : null}
                {job.status === "completed" ? <button type="button" onClick={handleDownload}>{t("common.download")}</button> : null}
              </div>
            </div>
          ) : null}

          {statusText ? <p className={styles.status}>{statusText}</p> : null}
        </div>

        <div className={styles.previewPanel}>
          {previewUrl ? (
            <div className={styles.realPreview}>
              <div>
                <span>{t("image.before")}</span>
                <img src={previewUrl} alt="Imagem enviada" />
              </div>
              <div>
                <span>{t("image.after")}</span>
                {resultUrl ? (
                  <img src={resultUrl} alt={t("image.resultAlt")} />
                ) : operation === "upscale_image" && isPremium ? (
                  <div className={styles.localPreview}>
                    <img src={previewUrl} alt={t("image.upscalePreviewAlt")} style={localUpscaleStyle} />
                    <small>{t("image.localPreviewScale", { scale })}</small>
                  </div>
                ) : active ? (
                  <div className={styles.processingPreview}>
                    <img src={previewUrl} alt="" />
                    <i />
                    <small>{operation === "remove_background" ? t("image.removingBg") : operation === "optimize_image" ? t("image.optimizing") : t("image.upscaling")}</small>
                  </div>
                ) : (
                  <div className={styles.pending}>{t("image.resultAfterProcessing")}</div>
                )}
              </div>
            </div>
          ) : (
            <div className={`${styles.demo} ${demoClass}`} aria-hidden="true">
              <div />
              <span>{operation === "optimize_image" ? "2.8 MB -> 420 KB" : operation === "upscale_image" ? "512x512 -> 1024x1024" : t("image.demoRemoveBg")}</span>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

function Range({ label, value, min, max, step, onChange }: { label: string; value: number; min: number; max: number; step: number; onChange: (value: number) => void }) {
  return (
    <label>
      <span>{label}</span>
      <input type="range" value={value} min={min} max={max} step={step} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

function statusLabel(job: ImageToolJob, t: (key: string, values?: Record<string, string | number>) => string) {
  if (job.status === "queued") return job.queue_position ? t("image.statusQueuedPosition", { position: job.queue_position }) : t("image.statusQueued");
  if (job.status === "processing") return t("image.statusProcessing");
  if (job.status === "completed") return t("common.completed");
  if (job.status === "cancelled") return t("image.statusCancelled");
  return t("common.failed");
}

function formatBytes(value?: number | null) {
  if (!value) return "0 B";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}
