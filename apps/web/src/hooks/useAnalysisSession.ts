"use client";

import { useState, useEffect } from "react";
import { AnalysisSession, FileUploadResponse, CreateAnalysisSessionRequest, SessionProgress } from "@/types/analysis";

interface UseAnalysisSessionResult {
  session: AnalysisSession | null;
  progress: SessionProgress | null;
  isLoading: boolean;
  error: string | null;
  createSession: (data: CreateAnalysisSessionRequest) => Promise<AnalysisSession>;
  uploadFile: (sessionId: string, file: File) => Promise<FileUploadResponse>;
  getProgress: (sessionId: string) => Promise<SessionProgress>;
  reset: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useAnalysisSession(): UseAnalysisSessionResult {
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [progress, setProgress] = useState<SessionProgress | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createSession = async (data: CreateAnalysisSessionRequest): Promise<AnalysisSession> => {
    setIsLoading(true);
    setError(null);

    try {
      // Map frontend fields to backend fields
      const backendData = {
        description: data.business_description,
        objective: data.analysis_objective,
        objective_category: data.objective_category,
        category: data.category,
      };

      const response = await fetch(`${API_BASE_URL}/api/v1/analysis-sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(backendData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Erro ao criar sessão");
      }

      const newSession: AnalysisSession = await response.json();
      setSession(newSession);
      return newSession;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Erro desconhecido";
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const uploadFile = async (sessionId: string, file: File): Promise<FileUploadResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE_URL}/api/v1/analysis-sessions/${sessionId}/files`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Erro ao fazer upload");
      }

      const result: FileUploadResponse = await response.json();

      // Atualizar session com informações retornadas
      setSession((prev) =>
        prev
          ? {
              ...prev,
              files_count: result.session.files_count,
              status: result.session.status,
              updated_at: new Date().toISOString(),
            }
          : null
      );

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Erro desconhecido";
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const getProgress = async (sessionId: string): Promise<SessionProgress> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/analysis-sessions/${sessionId}/progress`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Erro ao buscar progresso");
      }

      const progressData: SessionProgress = await response.json();
      setProgress(progressData);
      return progressData;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Erro desconhecido";
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const reset = () => {
    setSession(null);
    setProgress(null);
    setError(null);
    setIsLoading(false);
  };

  return {
    session,
    progress,
    isLoading,
    error,
    createSession,
    uploadFile,
    getProgress,
    reset,
  };
}
