"use client";

import styles from "./AnalysisProgress.module.css";

export type AnalysisStatus =
  | "idle"
  | "uploading"
  | "reading"
  | "detecting"
  | "planning"
  | "building"
  | "finished"
  | "error";

interface AnalysisProgressProps {
  status: AnalysisStatus;
  fileName?: string;
  error?: string;
}

const statusLabels: Record<AnalysisStatus, string> = {
  idle: "Aguardando arquivo...",
  uploading: "Enviando arquivo...",
  reading: "Lendo conteúdo...",
  detecting: "Detectando estrutura...",
  planning: "Planejando análise...",
  building: "Construindo resultado...",
  finished: "Finalizado!",
  error: "Erro no processamento.",
};

export function AnalysisProgress({ status, fileName, error }: AnalysisProgressProps) {
  return (
    <div className={styles.progressBox}>
      <div className={styles.spinner} />
      <div className={styles.content}>
        <span className={styles.label}>{statusLabels[status]}</span>
        {fileName && <span className={styles.fileName}>{fileName}</span>}
        {error && <span className={styles.error}>{error}</span>}
      </div>
    </div>
  );
}