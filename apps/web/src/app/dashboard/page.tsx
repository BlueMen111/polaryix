"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getDashboard, type DashboardSummary, type WorkspaceFile } from "@/lib/api";
import styles from "./page.module.css";

function formatBytes(value: number) {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function statusLabel(status: WorkspaceFile["status"]) {
  const labels: Record<WorkspaceFile["status"], string> = {
    queued: "Aguardando",
    processing: "Processando",
    completed: "Concluido",
    failed: "Falhou",
    expired: "Expirado",
    deleted: "Excluido",
  };
  return labels[status] ?? status;
}

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [status, setStatus] = useState("Carregando dashboard...");

  useEffect(() => {
    if (!window.localStorage.getItem("polaryix:auth-token")) {
      window.location.href = "/login";
      return;
    }

    getDashboard()
      .then((data) => {
        setDashboard(data);
        setStatus("");
      })
      .catch((error) => setStatus(error instanceof Error ? error.message : "Nao foi possivel carregar o dashboard."));
  }, []);

  if (!dashboard) {
    return (
      <main className={styles.page}>
        <section className={styles.panel}>
          <p className={styles.message}>{status}</p>
        </section>
      </main>
    );
  }

  const storageText = `${formatBytes(dashboard.storage.used)} de ${formatBytes(dashboard.storage.limit)}`;

  return (
    <main className={styles.page}>
      <section className={styles.heroPanel}>
        <div>
          <p className={styles.eyebrow}>Dashboard</p>
          <h1>Ola, {dashboard.user.name}</h1>
          <p>Aqui esta um resumo da sua conta PolarYix.</p>
        </div>
        <Link href="/workspace">Abrir Workspace</Link>
      </section>

      <section className={styles.statsGrid}>
        <Stat label="Creditos disponiveis" value={String(dashboard.credits)} detail="Tokens da sua conta" />
        <Stat label="Plano atual" value={dashboard.plan === "free" ? "Free" : dashboard.plan.toUpperCase()} detail={dashboard.user.is_premium ? "Fila prioritaria ativa" : "Upgrade libera mais limites"} />
        <Stat label="Armazenamento" value={storageText} detail={`${dashboard.storage.percent}% usado`} />
        <Stat label="Arquivos no Workspace" value={String(dashboard.workspace_count)} detail={`${dashboard.favorite_count} favoritos`} />
      </section>

      <section className={styles.quickPanel}>
        <div>
          <p className={styles.eyebrow}>Acoes rapidas</p>
          <h2>Comece uma nova tarefa</h2>
        </div>
        <div className={styles.quickActions}>
          <Link href="/#converter">Nova conversao</Link>
          <Link href="/image/remove-background">Remover fundo</Link>
          <Link href="/image/optimize">Otimizar imagem</Link>
          <Link href="/image/upscale">Upscaling</Link>
        </div>
      </section>

      <section className={styles.contentGrid}>
        <ActivityList title="Ultimas atividades" files={dashboard.recent_jobs} />
        <ActivityList title="Favoritos" files={dashboard.favorite_files} empty="Nenhum favorito ainda." />
      </section>
    </main>
  );
}

function Stat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className={styles.statCard}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function ActivityList({ title, files, empty = "Nenhum arquivo encontrado." }: { title: string; files: WorkspaceFile[]; empty?: string }) {
  return (
    <section className={styles.listPanel}>
      <div className={styles.listHeader}>
        <h2>{title}</h2>
        <Link href="/workspace">Ver todos</Link>
      </div>
      {files.length ? (
        <div className={styles.activityList}>
          {files.map((file) => (
            <article key={file.id}>
              <div>
                <strong>{file.original_filename}</strong>
                <span>{file.operation_type || file.target_format} · {formatDate(file.created_at)}</span>
              </div>
              <small className={styles[file.status]}>{statusLabel(file.status)}</small>
            </article>
          ))}
        </div>
      ) : (
        <p className={styles.message}>{empty}</p>
      )}
    </section>
  );
}
