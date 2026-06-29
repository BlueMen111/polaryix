"use client";

import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
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
  { id: "all", label: "Todos" },
  { id: "favorites", label: "Favoritos" },
  { id: "expired", label: "Expirados" },
] as const;

function formatBytes(value?: number | null) {
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

export default function WorkspacePage() {
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [storage, setStorage] = useState<StorageSummary | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<(typeof filters)[number]["id"]>("all");
  const [status, setStatus] = useState("Carregando Workspace...");
  const [busyId, setBusyId] = useState("");
  const [targetFormats, setTargetFormats] = useState<Record<string, string>>({});
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);

  const storageText = useMemo(() => {
    if (!storage) return "Carregando armazenamento...";
    return `Voce esta usando ${formatBytes(storage.used)} de ${formatBytes(storage.limit)}.`;
  }, [storage]);

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
      setStatus(data.files.length ? "" : "Seu Workspace ainda esta vazio. Envie ou processe um arquivo para comecar.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel carregar o Workspace.");
    }
  }

  async function handleFavorite(file: WorkspaceFile) {
    setBusyId(file.id);
    try {
      await favoriteWorkspaceFile(file.id, !file.is_favorite);
      await refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel atualizar favorito.");
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
      setStatus(error instanceof Error ? error.message : "Nao foi possivel excluir o arquivo.");
    } finally {
      setBusyId("");
    }
  }

  async function handleDownload(file: WorkspaceFile) {
    setBusyId(file.id);
    try {
      await downloadWorkspaceFile(file);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel baixar o arquivo.");
    } finally {
      setBusyId("");
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!selected.length) return;
    setStatus("Enviando arquivos para o Workspace...");
    try {
      const result = await uploadWorkspaceFiles(selected);
      setStorage(result.storage);
      await refresh();
      setStatus(`${selected.length} arquivo(s) enviados para o Workspace.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel enviar os arquivos.");
    }
  }

  async function handleConvert(file: WorkspaceFile) {
    const target = (targetFormats[file.id] || "").trim();
    if (!target) {
      setStatus("Informe o formato de destino. Exemplo: png, jpg, pdf, mp4.");
      return;
    }
    setBusyId(file.id);
    try {
      await convertWorkspaceFile(file.id, target);
      await refresh();
      setStatus(`Conversao para ${target.toUpperCase()} enviada para a fila.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel criar a conversao.");
    } finally {
      setBusyId("");
    }
  }

  async function handleImageTool(file: WorkspaceFile, operation: "remove_background" | "optimize_image" | "upscale_image") {
    setBusyId(file.id);
    try {
      await processWorkspaceImage(file.id, operation, 2);
      await refresh();
      setStatus("Processamento de imagem enviado para a fila.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel processar a imagem.");
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
          <p className={styles.eyebrow}>Workspace</p>
          <h1>Sua Area de Trabalho</h1>
          <p>Organize seus arquivos, resultados e conversoes em um so lugar.</p>
        </div>
        <div className={styles.storageCard}>
          <strong>Armazenamento</strong>
          <span>{storageText}</span>
          <i style={{ width: `${Math.min(storage?.percent ?? 0, 100)}%` }} />
          <small>{storage?.retention_hours === 24 ? "Premium: arquivos armazenados por ate 24h." : "Free: arquivos armazenados por ate 2h."}</small>
        </div>
      </section>

      <section className={styles.toolbar}>
        <input ref={fileInputRef} className={styles.hiddenInput} type="file" multiple onChange={handleUpload} />
        <input ref={folderInputRef} className={styles.hiddenInput} type="file" multiple onChange={handleUpload} {...{ webkitdirectory: "", directory: "" }} />
        <input
          value={query}
          placeholder="Buscar por nome"
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") refresh(event.currentTarget.value);
          }}
        />
        <button type="button" onClick={() => refresh()}>Buscar</button>
        <button type="button" onClick={() => fileInputRef.current?.click()}>Enviar arquivos</button>
        <button type="button" onClick={() => folderInputRef.current?.click()}>Enviar pasta</button>
        <div>
          {filters.map((item) => (
            <button key={item.id} type="button" className={filter === item.id ? styles.activeFilter : undefined} onClick={() => setFilter(item.id)}>
              {item.label}
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
                  <span>{file.extension || file.target_format || "file"}</span>
                  <button type="button" onClick={() => handleFavorite(file)} disabled={busyId === file.id} aria-label={file.is_favorite ? "Desfavoritar" : "Favoritar"}>
                    {file.is_favorite ? "★" : "☆"}
                  </button>
                </div>
                <strong>{file.original_filename}</strong>
                <p>{file.operation_type || file.target_format} · {formatBytes(file.size_bytes ?? file.file_size)}</p>
                <div className={styles.meta}>
                  <span className={styles[file.status]}>{statusLabel(file.status)}</span>
                  <span>Expira em {formatDate(file.expires_at)}</span>
                </div>
                <div className={styles.actions}>
                  <button type="button" onClick={() => handleDownload(file)} disabled={!canDownload || busyId === file.id}>Baixar</button>
                  <button type="button" onClick={() => handleDelete(file)} disabled={busyId === file.id}>Excluir</button>
                </div>
                {file.status === "completed" ? (
                  <div className={styles.reuseBox}>
                    <div>
                      <input
                        value={targetFormats[file.id] ?? ""}
                        placeholder="Converter para..."
                        onChange={(event) => setTargetFormats((current) => ({ ...current, [file.id]: event.target.value }))}
                      />
                      <button type="button" onClick={() => handleConvert(file)} disabled={busyId === file.id}>Converter</button>
                    </div>
                    {isImage(file) ? (
                      <div>
                        <button type="button" onClick={() => handleImageTool(file, "optimize_image")} disabled={busyId === file.id}>Otimizar</button>
                        <button type="button" onClick={() => handleImageTool(file, "remove_background")} disabled={busyId === file.id}>Remover fundo</button>
                        <button type="button" onClick={() => handleImageTool(file, "upscale_image")} disabled={busyId === file.id}>Upscaling</button>
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
