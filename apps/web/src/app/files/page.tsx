"use client";

import { useEffect, useMemo, useState } from "react";
import { downloadMyFile, listMyFiles, type ConvertedFile } from "@/lib/api";
import styles from "./page.module.css";

const statusLabels: Record<ConvertedFile["status"], string> = {
  queued: "Aguardando",
  processing: "Processando",
  completed: "Concluido",
  failed: "Erro",
  expired: "Expirado",
  deleted: "Removido",
};

function formatBytes(value: number) {
  if (!value) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value: string) {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function FilesPage() {
  const [files, setFiles] = useState<ConvertedFile[]>([]);
  const [status, setStatus] = useState("Carregando arquivos...");
  const [downloadingId, setDownloadingId] = useState("");

  const isLoggedIn = useMemo(() => {
    if (typeof window === "undefined") {
      return false;
    }

    return Boolean(window.localStorage.getItem("polaryix:auth-token"));
  }, []);

  useEffect(() => {
    if (!isLoggedIn) {
      setStatus("Entre na sua conta para ver seus arquivos convertidos.");
      return;
    }

    listMyFiles()
      .then((data) => {
        setFiles(data.files);
        setStatus(data.files.length ? "" : "Voce ainda nao tem conversoes salvas.");
      })
      .catch((error) => {
        setStatus(error instanceof Error ? error.message : "Nao foi possivel carregar seus arquivos.");
      });
  }, [isLoggedIn]);

  async function handleDownload(file: ConvertedFile) {
    setDownloadingId(file.id);
    setStatus("");
    try {
      await downloadMyFile(file);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel baixar este arquivo.");
    } finally {
      setDownloadingId("");
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.panel}>
        <div className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Meus arquivos</p>
            <h1>Arquivos convertidos</h1>
            <p>Seus ultimos arquivos ficam disponiveis por ate 12 horas apos a conversao.</p>
          </div>
          <a className={styles.primaryLink} href="/">
            Nova conversao
          </a>
        </div>

        {status ? <p className={styles.message}>{status}</p> : null}

        {files.length ? (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Arquivo</th>
                  <th>Formato</th>
                  <th>Status</th>
                  <th>Tamanho</th>
                  <th>Data</th>
                  <th>Qualidade</th>
                  <th aria-label="Acoes" />
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
                        {file.original_format} para {file.target_format}
                      </td>
                      <td>
                        <span className={`${styles.badge} ${styles[file.status]}`}>{statusLabels[file.status]}</span>
                      </td>
                      <td>{formatBytes(Number(file.file_size || 0))}</td>
                      <td>{formatDate(file.created_at)}</td>
                      <td>{file.quality_delivered || file.quality_requested || "-"}</td>
                      <td>
                        {canDownload ? (
                          <button type="button" onClick={() => handleDownload(file)} disabled={downloadingId === file.id}>
                            {downloadingId === file.id ? "Baixando..." : "Download"}
                          </button>
                        ) : (
                          <em>Indisponivel</em>
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
