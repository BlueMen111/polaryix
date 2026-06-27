"use client";

import React, { useState, useRef, useEffect } from "react";
import { useAnalysisSession } from "@/hooks/useAnalysisSession";
import {
  AnalysisObjectiveCategory,
  CreateAnalysisSessionRequest,
  OBJECTIVE_CATEGORIES,
  SUPPORTED_FORMATS,
} from "@/types/analysis";
import { SessionProgress } from "./SessionProgress";
import { AnalysisProgress, AnalysisStatus } from "./AnalysisProgress";
import styles from "./AnalysisSessionForm.module.css";

interface AnalysisSessionFormProps {
  onSessionCreated?: (sessionId: string) => void;
}

type FormStep = "info" | "upload" | "processing" | "complete";

export function AnalysisSessionForm({ onSessionCreated }: AnalysisSessionFormProps) {
  const { session, progress, isLoading, error, createSession, uploadFile, getProgress, reset } = useAnalysisSession();
  const [step, setStep] = useState<FormStep>("info");

  // Form state for session creation
  const [formData, setFormData] = useState({
    business_description: "",
    analysis_objective: "",
    objective_category: "comercial" as AnalysisObjectiveCategory,
    category: "",
  });

  // Upload state
  const [files, setFiles] = useState<File[]>([]);
  const [fileDescriptions, setFileDescriptions] = useState<Record<string, string>>({});
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedCount, setUploadedCount] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragOverRef = useRef(false);

  // Handle form input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Get file icon based on extension
  const getFileIcon = (filename: string): string => {
    const ext = filename.split(".").pop()?.toLowerCase();
    switch (ext) {
      case "csv":
        return "📊";
      case "xlsx":
      case "xls":
        return "📗";
      case "json":
        return "📋";
      case "txt":
        return "📄";
      case "parquet":
        return "🗜️";
      default:
        return "📁";
    }
  };

  // Validate file
  const isValidFile = (file: File): boolean => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!SUPPORTED_FORMATS.includes(ext)) {
      return false;
    }
    if (file.size > 150 * 1024 * 1024) {
      // 150MB limit
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
    setFileDescriptions((prev) => {
      const next = { ...prev };

      newFiles.forEach((file) => {
        next[file.name] = next[file.name] ?? "";
      });

      return next;
    });
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

    if (!formData.business_description.trim()) {
      setUploadError("Por favor, conte um pouco sobre seu negócio");
      return;
    }

    if (!formData.analysis_objective.trim()) {
      setUploadError("Por favor, informe o objetivo desta análise");
      return;
    }

    try {
      await createSession({
        business_description: formData.business_description,
        analysis_objective: formData.analysis_objective,
        objective_category: formData.objective_category,
        category: formData.category || undefined,
      });
      setStep("upload");
      setUploadError(null);
    } catch (err) {
      setUploadError(error || "Erro ao criar sessão");
    }
  };

  // Upload files one by one with progress
  const handleUploadFiles = async () => {
    if (!session || files.length === 0) return;

    setUploadError(null);
    let uploaded = 0;

    for (const file of files) {
      try {
        // Simular progresso visual (frontend)
        // O backend já está processando, aqui só mostramos o feedback
        await uploadFile(session.id, file, fileDescriptions[file.name]);
        uploaded++;
        setUploadedCount(uploaded);
      } catch (err) {
        setUploadError(`Erro ao fazer upload de ${file.name}: ${error}`);
        break;
      }
    }

    if (uploaded === files.length) {
      setStep("processing");
      if (onSessionCreated && session) {
        onSessionCreated(session.id);
      }
    }
  };

  // Auto-refresh progress when in processing step
  useEffect(() => {
    if (step !== "processing" || !session?.id) return;

    const fetchProgress = async () => {
      try {
        await getProgress(session.id);
      } catch (err) {
        // Silently fail, user can manually refresh
      }
    };

    // Initial fetch
    fetchProgress();

    // Poll every 3 seconds
    const interval = setInterval(fetchProgress, 3000);

    return () => clearInterval(interval);
  }, [step, session?.id, getProgress]);

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => {
      const removed = prev[index];
      setFileDescriptions((current) => {
        const next = { ...current };
        delete next[removed.name];
        return next;
      });

      return prev.filter((_, i) => i !== index);
    });
  };

  const handleReset = () => {
    reset();
    setStep("info");
    setFormData({
      business_description: "",
      analysis_objective: "",
      objective_category: "comercial",
      category: "",
    });
    setFiles([]);
    setFileDescriptions({});
    setUploadedCount(0);
    setUploadError(null);
  };

  return (
    <div className={styles.container}>
      {step === "info" && (
        <form onSubmit={handleCreateSession} className={styles.form}>
          <div className={styles.header}>
            <h2>👋 Olá! Vamos construir um dashboard inteligente</h2>
            <p className={styles.description}>
              Conte-me sobre seu negócio e seus objetivos. A IA irá analisar seus dados 
              e criar um dashboard personalizado para você.
            </p>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="business_description">
              📝 Conte um pouco sobre seu negócio <span className={styles.required}>*</span>
            </label>
            <textarea
              id="business_description"
              name="business_description"
              placeholder="Ex:&#10;• Sou dono de uma concessionária de veículos&#10;• clientes.csv: Cadastro de clientes com dados demográficos&#10;• vendas.csv: Histórico de vendas dos últimos 3 anos&#10;• estoque.csv: Veículos disponíveis e status&#10;• comentarios.csv: Avaliações e feedbacks dos clientes&#10;&#10;Quero entender: quais carros vendem mais, ticket médio, desempenho dos vendedores, sazonalidade e satisfação dos clientes"
              value={formData.business_description}
              onChange={handleInputChange}
              disabled={isLoading}
              rows={8}
              className={styles.textarea}
            />
            <span className={styles.hint}>
              Quanto mais detalhes você fornecer sobre seus dados e negócio, mais personalizado será seu dashboard
            </span>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="analysis_objective">
              O que você deseja que o dashboard faça? <span className={styles.required}>*</span>
            </label>
            <textarea
              id="analysis_objective"
              name="analysis_objective"
              placeholder="Ex: criar um dashboard com filtro de todas as vendas, top vendas, melhores lugares de vendas, piores lugares, vendedores que mais venderam, produtos mais vendidos, evolução por mês e comparação por estado/cidade."
              value={formData.analysis_objective}
              onChange={handleInputChange}
              disabled={isLoading}
              rows={4}
              className={styles.textarea}
            />
            <span className={styles.hint}>
              Descreva perguntas, filtros e rankings desejados. O sistema vai procurar colunas equivalentes em PT/EN nos arquivos.
            </span>
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label htmlFor="objective_category">🎯 Categoria da Análise</label>
              <select
                id="objective_category"
                name="objective_category"
                value={formData.objective_category}
                onChange={handleInputChange}
                disabled={isLoading}
                className={styles.select}
              >
                {OBJECTIVE_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="category">📂 Categoria (opcional)</label>
              <input
                id="category"
                type="text"
                name="category"
                placeholder="Ex: Vendas, Financeiro, RH"
                value={formData.category}
                onChange={handleInputChange}
                disabled={isLoading}
                className={styles.input}
              />
            </div>
          </div>

          {error && (
            <div className={styles.error}>
              ⚠️ {typeof error === 'string' ? error : 'Erro ao criar sessão'}
            </div>
          )}

          <button type="submit" disabled={isLoading} className={styles.primaryButton}>
            {isLoading ? "⏳ Criando sessão..." : "Próximo: Enviar Arquivos →"}
          </button>
        </form>
      )}

      {step === "upload" && session && (
        <div className={styles.uploadSection}>
          <div className={styles.uploadHeader}>
            <h2>📤 Envie seus arquivos</h2>
            <p className={styles.sessionInfo}>
              Sessão: <strong>{session.id.slice(0, 8)}...</strong>
            </p>
            <p className={styles.uploadDescription}>
              Envie todos os arquivos relevantes para sua análise. Quanto mais dados, 
              mais rica será a análise da IA.
            </p>
          </div>

          {isLoading && (
            <AnalysisProgress 
              status="uploading" 
              fileName={files[uploadedCount]?.name}
            />
          )}

          <div
            className={`${styles.dropZone} ${dragOverRef.current ? styles.dragActive : ""}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className={styles.dropZoneContent}>
              <div className={styles.uploadIcon}>📊</div>
              <h3>Arraste arquivos aqui</h3>
              <p>ou clique para selecionar múltiplos arquivos</p>
              <div className={styles.formatBadges}>
                {SUPPORTED_FORMATS.map((format) => (
                  <span key={format} className={styles.formatBadge}>
                    {format}
                  </span>
                ))}
              </div>
              <p className={styles.sizeLimit}>
                Tamanho máximo: 100MB por arquivo
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

          {uploadError && <div className={styles.error}>⚠️ {uploadError}</div>}

          {files.length > 0 && (
            <div className={styles.fileList}>
              <h3>📁 Arquivos Selecionados ({files.length})</h3>
              <ul>
                {files.map((file, index) => (
                  <li key={index} className={styles.fileItem}>
                    <div className={styles.fileIcon}>
                      {getFileIcon(file.name)}
                    </div>
                    <div className={styles.fileInfo}>
                      <div className={styles.fileText}>
                        <span className={styles.fileName}>{file.name}</span>
                        <span className={styles.fileSize}>
                          {(file.size / 1024 / 1024).toFixed(2)} MB
                        </span>
                        <input
                          type="text"
                          className={styles.fileDescriptionInput}
                          placeholder="O que este arquivo contém? Ex: pedidos, vendedores, clientes, pagamentos..."
                          value={fileDescriptions[file.name] ?? ""}
                          onChange={(event) =>
                            setFileDescriptions((current) => ({
                              ...current,
                              [file.name]: event.target.value,
                            }))
                          }
                          disabled={isLoading || uploadedCount > index}
                        />
                      </div>
                    </div>
                    {uploadedCount > index ? (
                      <span className={styles.uploadedBadge}>✓ Enviado</span>
                    ) : (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveFile(index);
                        }}
                        className={styles.removeButton}
                        title="Remover arquivo"
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
              {isLoading ? (
                <>⏳ Enviando {uploadedCount}/{files.length}...</>
              ) : (
                <>🚀 Gerar Dashboard Inteligente</>
              )}
            </button>
          </div>
        </div>
      )}

      {step === "processing" && session && (
        <div className={styles.processingSection}>
          <h2>Processando Análise</h2>
          <p className={styles.processingInfo}>
            Seus arquivos estão sendo analisados. Isso pode levar alguns instantes.
          </p>

          <SessionProgress 
            progress={progress} 
            onRefresh={() => getProgress(session.id)}
          />

          <div className={styles.buttonGroup}>
            <button
              type="button"
              onClick={handleReset}
              className={styles.secondaryButton}
              disabled={isLoading}
            >
              ← Nova Análise
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
              <strong>Descrição do Negócio:</strong> {session.description?.slice(0, 100)}...
            </p>
            <p>
              <strong>Objetivo:</strong> {session.objective?.slice(0, 100)}...
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
