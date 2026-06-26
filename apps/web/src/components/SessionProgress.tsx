"use client";

import React from "react";
import type { SessionProgress } from "@/types/analysis";
import styles from "./SessionProgress.module.css";

interface SessionProgressProps {
  progress: SessionProgress | null;
  onRefresh?: () => void;
}

export function SessionProgress({ progress, onRefresh }: SessionProgressProps) {
  if (!progress) {
    return null;
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "#10b981";
      case "processing":
        return "#3b82f6";
      case "failed":
        return "#ef4444";
      case "ready":
        return "#f59e0b";
      default:
        return "#6b7280";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "draft":
        return "Rascunho";
      case "ready":
        return "Pronto";
      case "processing":
        return "Processando";
      case "completed":
        return "Concluído";
      case "failed":
        return "Falhou";
      case "archived":
        return "Arquivado";
      default:
        return status;
    }
  };

  const allProcessingSteps = [
    { id: "understanding", label: "Entendendo seu negócio", icon: "🧠" },
    { id: "reading", label: "Lendo arquivos", icon: "📖" },
    { id: "relating", label: "Relacionando dados", icon: "🔗" },
    { id: "detecting", label: "Detectando indicadores", icon: "📊" },
    { id: "planning", label: "Planejando Dashboard", icon: "📋" },
    { id: "building", label: "Construindo gráficos", icon: "🎨" },
    { id: "finalizing", label: "Finalizando", icon: "✨" },
  ];

  const getCurrentStepIndex = (): number => {
    if (progress.status === "completed") return allProcessingSteps.length;
    if (progress.status === "failed") return -1;
    
    const currentStepLower = progress.current_step.toLowerCase();
    for (let i = 0; i < allProcessingSteps.length; i++) {
      if (currentStepLower.includes(allProcessingSteps[i].label.toLowerCase().split(" ")[0])) {
        return i;
      }
    }
    return 0;
  };

  const currentStepIndex = getCurrentStepIndex();

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3>🤖 Processamento Inteligente</h3>
        <span 
          className={styles.statusBadge}
          style={{ backgroundColor: getStatusColor(progress.status) }}
        >
          {getStatusLabel(progress.status)}
        </span>
      </div>

      {progress.status === "processing" && (
        <div className={styles.progressSection}>
          <div className={styles.progressInfo}>
            <span className={styles.progressPercentage}>{Math.round(progress.progress_percentage)}%</span>
            <span className={styles.currentStep}>{progress.current_step}</span>
          </div>

          <div className={styles.progressBarContainer}>
            <div 
              className={styles.progressBar}
              style={{ 
                width: `${progress.progress_percentage}%`,
                backgroundColor: getStatusColor(progress.status)
              }}
            />
          </div>
        </div>
      )}

      <div className={styles.stepsSection}>
        <h4>Etapas do Processamento</h4>
        <div className={styles.processingSteps}>
          {allProcessingSteps.map((step, index) => {
            const isCompleted = index < currentStepIndex || progress.status === "completed";
            const isCurrent = index === currentStepIndex && progress.status === "processing";
            const isPending = index > currentStepIndex && progress.status !== "completed" && progress.status !== "failed";

            return (
              <div 
                key={step.id} 
                className={`${styles.processingStep} ${
                  isCompleted ? styles.stepCompleted : 
                  isCurrent ? styles.stepCurrent : 
                  styles.stepPending
                }`}
              >
                <div className={styles.stepIcon}>
                  {isCompleted ? "✓" : isCurrent ? step.icon : step.icon}
                </div>
                <div className={styles.stepContent}>
                  <div className={styles.stepLabel}>{step.label}</div>
                  {isCurrent && (
                    <div className={styles.stepSpinner}>
                      <div className={styles.spinner}></div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {progress.completed_steps.length > 0 && (
        <div className={styles.detailsSection}>
          <h4>Detalhes do Processamento</h4>
          <ul className={styles.detailsList}>
            {progress.completed_steps.map((step, index) => (
              <li key={index} className={styles.detailItem}>
                <span className={styles.detailCheck}>✓</span>
                <span className={styles.detailText}>{step}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {progress.status === "completed" && (
        <div className={styles.successMessage}>
          <div className={styles.successIcon}>🎉</div>
          <p><strong>Análise concluída com sucesso!</strong></p>
          <p className={styles.successSubtext}>
            Seu dashboard inteligente está pronto para visualização.
          </p>
        </div>
      )}

      {progress.error_message && (
        <div className={styles.errorMessage}>
          <strong>❌ Erro no processamento:</strong>
          <p>{progress.error_message}</p>
        </div>
      )}

      {onRefresh && progress.status === "processing" && (
        <button onClick={onRefresh} className={styles.refreshButton}>
          🔄 Atualizar Status
        </button>
      )}
    </div>
  );
}