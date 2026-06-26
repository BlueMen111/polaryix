"use client";

import React, { useState, useRef } from "react";
import { useAnalysisSession } from "@/hooks/useAnalysisSession";
import {
  AnalysisObjectiveCategory,
  CreateAnalysisSessionRequest,
  OBJECTIVE_CATEGORIES,
  SUPPORTED_FORMATS,
} from "@/types/analysis";
import styles from "./AnalysisSessionForm.module.css";

interface AnalysisSessionFormProps {
  onSessionCreated?: (sessionId: string) => void;
}

type FormStep = "info" | "upload" | "complete";

export function AnalysisSessionForm({ onSessionCreated }: AnalysisSessionFormProps) {
  const { session, isLoading, error, createSession, uploadFile, reset } = useAnalysisSession();
  const [step, setStep] = useState<FormStep>("info");

  // Form state for session creation
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    objective: "",
    objective_category: "comercial" as AnalysisObjectiveCategory,
  });

  // Upload state
  const [files, setFiles] = useState<File[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedCount, setUploadedCount] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragOverRef = useRef(false);

  // Handle form input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Validate file
  const isValidFile = (file: File): boolean => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!SUPPORTED_FORMATS.includes(ext)) {
      return false;
    }
    if (file.size > 100 * 1024 * 1024) {
      // 100MB limit
      return false;
    }
    return true;
  };

  // Handle file selection
  const handleFileSelect = (selectedFiles: FileList | null) => {
    if (!selectedFiles) return;

    const newFiles: File[] = [];
    const errors: string[] = [];

    Array.from(selectedFiles).forEach((file) => {
      if (!isValidFile(file)) {
        const ext = "." + file.name.split(".").pop()?.toLowerCase();
        if (!SUPPORTED_FORMATS.includes(ext)) {
          errors.push(`${file.name}: formato não suportado`);
        } else {
          errors.push(`${file.name}: arquivo muito grande (máx 100MB)`);
        }
      } else {
        newFiles.push(file);
      }
    });

    if (errors.length > 0) {
      setUploadError(errors.join(", "));
    } else {
      setUploadError(null);
    }

    setFiles((prev) => [...prev, ...newFiles]);
  };

  // Handle drag and drop
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    dragOverRef.current = true;
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    dragOverRef.current = false;
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    dragOverRef.current = false;
    handleFileSelect(e.dataTransfer.files);
  };

  // Create session and proceed to upload
  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.title.trim()) {
      setUploadError("Por favor, digite um título para a análise");
      return;
    }

    try {
      await createSession({
        title: formData.title,
        description: formData.description || undefined,
        objective: formData.objective || undefined,
        objective_category: formData.objective_category,
      });
      setStep("upload");
      setUploadError(null);
    } catch (err) {
      setUploadError(error || "Erro ao criar sessão");
    }
  };

  // Upload files one by one
  const handleUploadFiles = async () => {
    if (!session || files.length === 0) return;

    setUploadError(null);
    let uploaded = 0;

    for (const file of files) {
      try {
        await uploadFile(session.id, file);
        uploaded++;
        setUploadedCount(uploaded);
      } catch (err) {
        setUploadError(`Erro ao fazer upload de ${file.name}: ${error}`);
        break;
      }
    }

    if (uploaded === files.length) {
      setStep("complete");
      if (onSessionCreated && session) {
        onSessionCreated(session.id);
      }
    }
  };

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleReset = () => {
    reset();
    setStep("info");
    setFormData({
      title: "",
      description: "",
      objective: "",
      objective_category: "comercial",
    });
    setFiles([]);
    setUploadedCount(0);
    setUploadError(null);
  };

  return (
    <div className={styles.container}>
      {step === "info" && (
        <form onSubmit={handleCreateSession} className={styles.form}>
          <h2>Nova Análise</h2>
          <p className={styles.description}>
            Crie uma nova sessão de análise e envie seus arquivos para começar
          </p>

          <div className={styles.formGroup}>
            <label htmlFor="title">
              Título da Análise <span className={styles.required}>*</span>
            </label>
            <input
              id="title"
              type="text"
              name="title"
              placeholder="ex: Análise de Vendas 2026"
              value={formData.title}
              onChange={handleInputChange}
              disabled={isLoading}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="description">Descrição</label>
            <textarea
              id="description"
              name="description"
              placeholder="Descreva brevemente o objetivo dessa análise..."
              value={formData.description}
              onChange={handleInputChange}
              disabled={isLoading}
              rows={3}
            />
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label htmlFor="objective_category">Categoria</label>
              <select
                id="objective_category"
                name="objective_category"
                value={formData.objective_category}
                onChange={handleInputChange}
                disabled={isLoading}
              >
                {OBJECTIVE_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="objective">Objetivo da Análise</label>
            <textarea
              id="objective"
              name="objective"
              placeholder="Qual é o objetivo principal dessa análise?"
              value={formData.objective}
              onChange={handleInputChange}
              disabled={isLoading}
              rows={2}
            />
          </div>

          {error && <div className={styles.error}>{error}</div>}

          <button type="submit" disabled={isLoading} className={styles.primaryButton}>
            {isLoading ? "Criando..." : "Próximo: Enviar Arquivos"}
          </button>
        </form>
      )}

      {step === "upload" && session && (
        <div className={styles.uploadSection}>
          <h2>Enviar Arquivos</h2>
          <p className={styles.sessionInfo}>
            Sessão: <strong>{session.title}</strong>
          </p>

          <div
            className={`${styles.dropZone} ${dragOverRef.current ? styles.dragActive : ""}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className={styles.dropZoneContent}>
              <div className={styles.uploadIcon}>📁</div>
              <h3>Arraste arquivos aqui</h3>
              <p>ou clique para selecionar</p>
              <p className={styles.supportedFormats}>
                Formatos suportados: {SUPPORTED_FORMATS.join(", ")}
              </p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={SUPPORTED_FORMATS.join(",")}
              onChange={(e) => handleFileSelect(e.target.files)}
              className={styles.hiddenInput}
            />
          </div>

          {uploadError && <div className={styles.error}>{uploadError}</div>}

          {files.length > 0 && (
            <div className={styles.fileList}>
              <h3>Arquivos Selecionados ({files.length})</h3>
              <ul>
                {files.map((file, index) => (
                  <li key={index} className={styles.fileItem}>
                    <div className={styles.fileInfo}>
                      <span className={styles.fileName}>{file.name}</span>
                      <span className={styles.fileSize}>
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </span>
                    </div>
                    {uploadedCount > index ? (
                      <span className={styles.uploadedBadge}>✓ Enviado</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleRemoveFile(index)}
                        className={styles.removeButton}
                      >
                        ✕
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className={styles.buttonGroup}>
            <button
              type="button"
              onClick={() => setStep("info")}
              disabled={isLoading}
              className={styles.secondaryButton}
            >
              ← Voltar
            </button>
            <button
              type="button"
              onClick={handleUploadFiles}
              disabled={isLoading || files.length === 0}
              className={styles.primaryButton}
            >
              {isLoading ? `Enviando ${uploadedCount}/${files.length}...` : "Enviar Arquivos"}
            </button>
          </div>
        </div>
      )}

      {step === "complete" && session && (
        <div className={styles.completeSection}>
          <div className={styles.successIcon}>✓</div>
          <h2>Análise Criada com Sucesso!</h2>
          <div className={styles.completionInfo}>
            <p>
              <strong>Título:</strong> {session.title}
            </p>
            <p>
              <strong>Arquivos:</strong> {session.files_count} arquivo(s) enviado(s)
            </p>
            <p>
              <strong>Status:</strong> {session.status}
            </p>
            <p className={styles.sessionIdInfo}>
              <strong>ID da Sessão:</strong> <code>{session.id}</code>
            </p>
          </div>

          <div className={styles.buttonGroup}>
            <button type="button" onClick={handleReset} className={styles.primaryButton}>
              ← Nova Análise
            </button>
            <button
              type="button"
              onClick={() => {
                /* TODO: Navigate to session details */
              }}
              className={styles.secondaryButton}
            >
              Ver Análise →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
