export type AnalysisObjectiveCategory = 
  | "comercial"
  | "financeiro"
  | "marketing"
  | "rh"
  | "operacional"
  | "logistica"
  | "atendimento"
  | "outro";

export type AnalysisSessionStatus = 
  | "draft"
  | "ready"
  | "processing"
  | "completed"
  | "failed"
  | "archived";

export type AnalysisSessionFile = {
  file_id: string;
  filename: string;
  format: string;
  size_bytes: number;
  row_count: number | null;
  column_count: number | null;
  column_names: string[] | null;
  uploaded_at: string;
};

export type AnalysisSession = {
  id: string;
  title: string;
  description?: string;
  objective?: string;
  objective_category?: AnalysisObjectiveCategory;
  files_count: number;
  status: AnalysisSessionStatus;
  dashboard_id: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

export type CreateAnalysisSessionRequest = {
  title: string;
  description?: string;
  objective?: string;
  objective_category?: AnalysisObjectiveCategory;
};

export type FileUploadResponse = {
  message: string;
  session_id: string;
  file: AnalysisSessionFile;
  session: {
    id: string;
    title: string;
    files_count: number;
    status: AnalysisSessionStatus;
  };
};

export const OBJECTIVE_CATEGORIES: { label: string; value: AnalysisObjectiveCategory }[] = [
  { label: "Comercial", value: "comercial" },
  { label: "Financeiro", value: "financeiro" },
  { label: "Marketing", value: "marketing" },
  { label: "Recursos Humanos", value: "rh" },
  { label: "Operacional", value: "operacional" },
  { label: "Logística", value: "logistica" },
  { label: "Atendimento", value: "atendimento" },
  { label: "Outro", value: "outro" },
];

export const SUPPORTED_FORMATS = [".csv", ".xlsx", ".json", ".txt", ".parquet"];
