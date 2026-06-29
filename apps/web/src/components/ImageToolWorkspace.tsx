"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ImageToolJob,
  ImageToolOperation,
  cancelImageToolJob,
  createImageToolJob,
  downloadImageToolJob,
  getCurrentUser,
  getImageToolJob,
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

export function ImageToolWorkspace({ operation, title, eyebrow, description, cost }: Props) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
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
  const resultUrl = job?.status === "completed" ? `/api/v1/image-tools/jobs/${job.id}/download` : "";
  const statusText = job ? statusLabel(job) : status;
  const demoClass = operation === "remove_background" ? styles.removeDemo : operation === "optimize_image" ? styles.optimizeDemo : styles.upscaleDemo;

  const planMessage = useMemo(() => {
    if (isPremium) {
      return "Fila prioritária Premium ativada. Controles avançados liberados e resultado sem marca d'água.";
    }
    if (operation === "upscale_image") {
      return "Processamento em fila padrão. Usuários Free recebem marca d'água no Upscaling.";
    }
    return "Processamento em fila padrão. Atualize para Premium para prioridade na fila.";
  }, [isPremium, operation]);

  useEffect(() => {
    const token = window.localStorage.getItem("polaryix:auth-token");
    if (!token) {
      return;
    }
    getCurrentUser()
      .then(({ user }) => {
        persistAuthSession({ token, user });
        setUser(user);
      })
      .catch(() => setUser(null));
  }, []);

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    if (!active || !job) {
      return;
    }
    const interval = window.setInterval(async () => {
      const updated = await getImageToolJob(job.id);
      setJob(updated);
      setStatus(statusLabel(updated));
    }, 2500);
    return () => window.clearInterval(interval);
  }, [active, job]);

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
    setJob(null);
    setStatus(selected ? "Imagem pronta para enviar." : "");
  }

  async function handleProcess() {
    if (!user) {
      setStatus("Entre com Google ou e-mail para processar imagens.");
      return;
    }
    if (!file) {
      setStatus("Escolha uma imagem PNG, JPG ou WEBP.");
      return;
    }
    setIsSubmitting(true);
    setStatus("Enviando para a fila...");
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
      setStatus(statusLabel(created));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Não foi possível processar a imagem.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRefresh() {
    if (!job) return;
    const updated = await getImageToolJob(job.id);
    setJob(updated);
    setStatus(statusLabel(updated));
  }

  async function handleCancel() {
    if (!job) return;
    const updated = await cancelImageToolJob(job.id);
    setJob(updated);
    setStatus("Job cancelado. Tokens devolvidos.");
  }

  async function handleDownload() {
    if (!job) return;
    const filename = await downloadImageToolJob(job);
    setStatus(`Download iniciado: ${filename}`);
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <div>
          <p>{eyebrow}</p>
          <h1>{title}</h1>
          <span>{description}</span>
        </div>
        <Link href="/premium">Conhecer Premium</Link>
      </section>

      <section className={styles.layout}>
        <div className={styles.panel}>
          <div className={styles.topRow}>
            <strong>{cost}</strong>
            <span>{planMessage}</span>
          </div>

          <label className={styles.uploadBox}>
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={handleFile} />
            <strong>{file?.name ?? "Selecionar imagem"}</strong>
            <small>PNG, JPG ou WEBP</small>
          </label>

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
                Manter tamanho original
              </label>
              {isPremium ? (
                <div className={styles.sliders}>
                  <Range label="Nitidez" value={sharpness} min={0.7} max={2.4} step={0.05} onChange={setSharpness} />
                  <Range label="Redução de ruído" value={denoise} min={0} max={1} step={0.05} onChange={setDenoise} />
                  <Range label="Contraste" value={contrast} min={0.8} max={1.6} step={0.05} onChange={setContrast} />
                  <Range label="Detalhes" value={detail} min={0.8} max={1.8} step={0.05} onChange={setDetail} />
                  <Range label="Intensidade" value={intensity} min={0.4} max={1.6} step={0.05} onChange={setIntensity} />
                </div>
              ) : (
                <div className={styles.locked}>Assine Premium para liberar escala 4x, ajustes finos e remover a marca d'água.</div>
              )}
            </div>
          ) : null}

          <button type="button" className={styles.primaryButton} onClick={handleProcess} disabled={isSubmitting}>
            {isSubmitting ? "Enviando..." : "Processar imagem"}
          </button>

          {job ? (
            <div className={styles.jobBox}>
              <strong>{statusLabel(job)}</strong>
              {job.queue_position ? <span>Posição na fila: {job.queue_position}</span> : null}
              {job.credits_cost ? <span>Tokens cobrados: {job.credits_cost}</span> : null}
              {job.original_size || job.final_size ? <span>{formatBytes(job.original_size)} → {formatBytes(job.final_size)}</span> : null}
              {typeof job.reduction_percent === "number" ? <span>Redução: {job.reduction_percent}%</span> : null}
              {job.message ? <p>{job.message}</p> : null}
              {job.error_message ? <p>{job.error_message}</p> : null}
              <div className={styles.actions}>
                <button type="button" onClick={handleRefresh}>Atualizar status</button>
                {job.status === "queued" ? <button type="button" onClick={handleCancel}>Cancelar</button> : null}
                {job.status === "completed" ? <button type="button" onClick={handleDownload}>Baixar</button> : null}
              </div>
            </div>
          ) : null}

          {statusText ? <p className={styles.status}>{statusText}</p> : null}
        </div>

        <div className={styles.previewPanel}>
          {previewUrl ? (
            <div className={styles.realPreview}>
              <div>
                <span>Antes</span>
                <img src={previewUrl} alt="Imagem enviada" />
              </div>
              <div>
                <span>Depois</span>
                {resultUrl ? <img src={resultUrl} alt="Resultado processado" /> : <div className={styles.pending}>Resultado após o processamento</div>}
              </div>
            </div>
          ) : (
            <div className={`${styles.demo} ${demoClass}`} aria-hidden="true">
              <div />
              <span>{operation === "optimize_image" ? "2.8 MB → 420 KB" : operation === "upscale_image" ? "512x512 → 1024x1024" : "Antes / Depois"}</span>
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

function statusLabel(job: ImageToolJob) {
  if (job.status === "queued") return `Aguardando na fila${job.queue_position ? ` - posição ${job.queue_position}` : ""}`;
  if (job.status === "processing") return "Processando imagem";
  if (job.status === "completed") return "Concluído";
  if (job.status === "cancelled") return "Cancelado";
  return "Falhou";
}

function formatBytes(value?: number | null) {
  if (!value) return "0 B";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}
