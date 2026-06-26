"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { uploadDataset } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");

  async function handleUpload() {
    if (!file) {
      setError("Selecione um arquivo primeiro.");
      return;
    }

    setError("");
    setIsUploading(true);

    try {
      const response = await uploadDataset(file);
      router.push(`/datasets/${response.dataset.dataset_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao enviar arquivo.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <main className="container">
      <div className="header">
        <div>
          <h1>Enviar dataset</h1>
          <p className="muted">Envie um arquivo para gerar análise automática.</p>
        </div>
      </div>

      <section className="card">
        <input
          className="input"
          type="file"
          accept=".csv,.xls,.xlsx,.json,.txt,.parquet"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />

        {file && (
          <p className="muted">
            Arquivo selecionado: <strong>{file.name}</strong>
          </p>
        )}

        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

        <button
          className="button"
          style={{ marginTop: 16 }}
          onClick={handleUpload}
          disabled={isUploading}
        >
          {isUploading ? "Enviando..." : "Enviar e analisar"}
        </button>
      </section>
    </main>
  );
}