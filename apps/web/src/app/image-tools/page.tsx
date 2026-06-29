"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
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
import styles from "./page.module.css";

const tools: Array<{
  operation: ImageToolOperation;
  title: string;
  description: string;
  cost: number;
}> = [
  {
    operation: "remove_background",
    title: "Remover Fundo",
    description: "Gera PNG com transparencia mantendo o tamanho original.",
    cost: 1,
  },
  {
    operation: "optimize_image",
    title: "Otimizar Imagem",
    description: "Reduz peso removendo metadados e preservando proporcao.",
    cost: 2,
  },
  {
    operation: "remaster_image",
    title: "Remasterizar Imagem",
    description: "Melhora nitidez, contraste e aparencia visual.",
    cost: 5,
  },
];

type ToolState = {
  file: File | null;
  job: ImageToolJob | null;
  status: string;
  isSubmitting: boolean;
};

const initialState: ToolState = {
  file: null,
  job: null,
  status: "",
  isSubmitting: false,
};

export default function ImageToolsPage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [states, setStates] = useState<Record<ImageToolOperation, ToolState>>({
    remove_background: initialState,
    optimize_image: initialState,
    remaster_image: initialState,
  });

  const isPremium = Boolean(user?.is_premium);
  const activeJobs = useMemo(
    () =>
      Object.values(states)
        .map((state) => state.job)
        .filter((job): job is ImageToolJob => Boolean(job && (job.status === "queued" || job.status === "processing"))),
    [states]
  );

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
    if (activeJobs.length === 0) {
      return;
    }

    const interval = window.setInterval(async () => {
      const updates = await Promise.allSettled(activeJobs.map((job) => getImageToolJob(job.id)));
      updates.forEach((update) => {
        if (update.status === "fulfilled") {
          const job = update.value;
          setStates((current) => ({
            ...current,
            [job.operation]: {
              ...current[job.operation],
              job,
              status: statusLabel(job),
            },
          }));
        }
      });
    }, 2500);

    return () => window.clearInterval(interval);
  }, [activeJobs]);

  function updateTool(operation: ImageToolOperation, patch: Partial<ToolState>) {
    setStates((current) => ({
      ...current,
      [operation]: {
        ...current[operation],
        ...patch,
      },
    }));
  }

  function handleFile(operation: ImageToolOperation, event: ChangeEvent<HTMLInputElement>) {
    updateTool(operation, {
      file: event.target.files?.[0] ?? null,
      status: event.target.files?.[0] ? "Imagem pronta para enviar." : "",
    });
  }

  async function handleProcess(operation: ImageToolOperation) {
    const state = states[operation];
    if (!user) {
      updateTool(operation, { status: "Entre com Google ou e-mail para usar as ferramentas." });
      return;
    }
    if (!state.file) {
      updateTool(operation, { status: "Escolha uma imagem PNG, JPG ou WEBP." });
      return;
    }

    updateTool(operation, { isSubmitting: true, status: "Enviando para a fila..." });
    try {
      const job = await createImageToolJob({ operation, file: state.file });
      updateTool(operation, { job, status: statusLabel(job) });
    } catch (error) {
      updateTool(operation, { status: error instanceof Error ? error.message : "Nao foi possivel processar a imagem." });
    } finally {
      updateTool(operation, { isSubmitting: false });
    }
  }

  async function handleRefresh(job: ImageToolJob) {
    try {
      const updated = await getImageToolJob(job.id);
      updateTool(updated.operation, { job: updated, status: statusLabel(updated) });
    } catch (error) {
      updateTool(job.operation, { status: error instanceof Error ? error.message : "Nao foi possivel atualizar." });
    }
  }

  async function handleCancel(job: ImageToolJob) {
    try {
      const updated = await cancelImageToolJob(job.id);
      updateTool(updated.operation, { job: updated, status: "Job cancelado. Tokens devolvidos." });
    } catch (error) {
      updateTool(job.operation, { status: error instanceof Error ? error.message : "Nao foi possivel cancelar." });
    }
  }

  async function handleDownload(job: ImageToolJob) {
    try {
      const filename = await downloadImageToolJob(job);
      updateTool(job.operation, { status: `Download iniciado: ${filename}` });
    } catch (error) {
      updateTool(job.operation, { status: error instanceof Error ? error.message : "Nao foi possivel baixar." });
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.header}>
        <p>Ferramentas de Imagem</p>
        <h1>Processamento com fila e prioridade Premium</h1>
        <span>{isPremium ? "Premium priority queue enabled. No watermark." : "Free users receive a small PolarYix watermark on remastered images. Upgrade to Premium to remove it."}</span>
      </section>

      <section className={styles.grid}>
        {tools.map((tool) => {
          const state = states[tool.operation];
          const job = state.job;

          return (
            <article className={styles.card} key={tool.operation}>
              <div className={styles.cardHeader}>
                <span>{tool.cost} token{tool.cost > 1 ? "s" : ""}</span>
                <h2>{tool.title}</h2>
                <p>{tool.description}</p>
              </div>

              {tool.operation === "remaster_image" ? (
                <div className={isPremium ? styles.premiumNote : styles.freeNote}>
                  {isPremium ? "Premium priority queue enabled. No watermark." : "Free users receive a small PolarYix watermark on remastered images. Upgrade to Premium to remove it."}
                </div>
              ) : null}

              <label className={styles.uploadBox}>
                <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => handleFile(tool.operation, event)} />
                <strong>{state.file?.name ?? "Selecionar imagem"}</strong>
                <small>PNG, JPG ou WEBP</small>
              </label>

              <button type="button" className={styles.primaryButton} onClick={() => handleProcess(tool.operation)} disabled={state.isSubmitting}>
                {state.isSubmitting ? "Enviando..." : "Processar"}
              </button>

              {job ? (
                <div className={styles.jobBox}>
                  <strong>{statusLabel(job)}</strong>
                  {job.queue_position ? <span>Posicao: {job.queue_position}</span> : null}
                  {job.error_message ? <p>{job.error_message}</p> : null}
                  <div className={styles.actions}>
                    <button type="button" onClick={() => handleRefresh(job)}>
                      Atualizar status
                    </button>
                    {job.status === "queued" ? (
                      <button type="button" onClick={() => handleCancel(job)}>
                        Cancelar
                      </button>
                    ) : null}
                    {job.status === "completed" ? (
                      <button type="button" onClick={() => handleDownload(job)}>
                        Baixar
                      </button>
                    ) : null}
                  </div>
                </div>
              ) : null}

              {state.status ? <p className={styles.status}>{state.status}</p> : null}
            </article>
          );
        })}
      </section>
    </main>
  );
}

function statusLabel(job: ImageToolJob) {
  if (job.status === "queued") {
    return `Aguardando na fila${job.queue_position ? ` - Posicao: ${job.queue_position}` : ""}`;
  }
  if (job.status === "processing") {
    return "Processando";
  }
  if (job.status === "completed") {
    return "Concluido";
  }
  if (job.status === "cancelled") {
    return "Cancelado";
  }
  return "Falhou";
}
