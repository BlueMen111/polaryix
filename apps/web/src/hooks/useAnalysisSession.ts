
"use client";

import { useCallback, useState } from "react";
import { AnalysisSession, FileUploadResponse, CreateAnalysisSessionRequest, SessionProgress } from "@/types/analysis";

interface UseAnalysisSessionResult {
  session: AnalysisSession | null;
  progress: SessionProgress | null;
  isLoading: boolean;
  error: string | null;
  createSession: (data: CreateAnalysisSessionRequest) => Promise<AnalysisSession>;
  uploadFile: (sessionId: string, file: File, description?: string) => Promise<FileUploadResponse>;
  getProgress: (sessionId: string) => Promise<SessionProgress>;
  reset: () => void;
}

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

function apiUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const baseUrl = API_BASE_URL
    ? `${API_BASE_URL.replace(/\/api\/v1$/i, "")}/api/v1`
    : "/api/v1";

  return `${baseUrl}${normalizedPath}`;
}

export function useAnalysisSession(): UseAnalysisSessionResult {
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [progress, setProgress] = useState<SessionProgress | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createSession = useCallback(async (data: CreateAnalysisSessionRequest): Promise<AnalysisSession> => {
    setIsLoading(true);
    setError(null);

    try {
      // Generate title from category and timestamp
      const categoryName = data.objective_category || "análise";
      const timestamp = new Date().toLocaleDateString("pt-BR");
      const autoTitle = `Dashboard ${categoryName} - ${timestamp}`;

      // Map frontend fields to backend fields
      const backendData = {
        title: autoTitle,
        description: data.business_description,
        objective: data.analysis_objective,
        objective_category: data.objective_category,
        category: data.category,
      };

      const response = await fetch(apiUrl("/analysis-sessions"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(backendData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        const errorMsg = typeof errorData.detail === 'string' 
          ? errorData.detail 
          : JSON.stringify(errorData.detail);
        throw new Error(errorMsg || "Erro ao criar sessão");
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
  }, []);

  const uploadFile = useCallback(async (sessionId: string, file: File, description?: string): Promise<FileUploadResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      // Validação de tamanho no frontend (100MB)
      const MAX_FILE_SIZE_MB = 100;
      const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
      
      if (file.size > MAX_FILE_SIZE_BYTES) {
        throw new Error(`Arquivo muito grande. Limite máximo: ${MAX_FILE_SIZE_MB}MB.`);
      }

      const formData = new FormData();
      formData.append("file", file);
      if (description?.trim()) {
        formData.append("file_description", description.trim());
      }

      console.log(`Uploading file: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)}MB) to session: ${sessionId}`);

      const response = await fetch(apiUrl(`/analysis-sessions/${sessionId}/files`), {
        method: "POST",
        body: formData,
      });

      const responseData = await response.json();
      console.log("Upload response:", responseData);

      if (!response.ok) {
        console.error("Upload error - Status:", response.status);
        console.error("Upload error - Full Response:", responseData);
        console.error("Upload error - Response JSON:", JSON.stringify(responseData, null, 2));
        
        let errorMsg = "";
        if (responseData.detail) {
          errorMsg = typeof responseData.detail === 'string' 
            ? responseData.detail 
            : JSON.stringify(responseData.detail);
        } else if (responseData.message) {
          errorMsg = responseData.message;
        } else if (responseData.error) {
          errorMsg = responseData.error;
        } else {
          errorMsg = `Erro HTTP ${response.status}: ${response.statusText || 'Erro desconhecido'}`;
        }
        
        throw new Error(errorMsg);
      }

      const result: FileUploadResponse = responseData;

      // Atualizar session com informações retornadas
      setSession((prev) =>
        prev
          ? {
              ...prev,
              files_count: result.session.files_count,
              status: result.session.status,
              dashboard_id: result.session.dashboard_id ?? prev.dashboard_id,
              updated_at: new Date().toISOString(),
            }
          : null
      );

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Erro ao fazer upload";
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getProgress = useCallback(async (sessionId: string): Promise<SessionProgress> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(apiUrl(`/analysis-sessions/${sessionId}/progress`));

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
  }, []);

  const reset = useCallback(() => {
    setSession(null);
    setProgress(null);
    setError(null);
    setIsLoading(false);
  }, []);

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
