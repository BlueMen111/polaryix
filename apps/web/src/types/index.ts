export type Kpi = {
  id: string;
  title: string;
  value: number | string;
  type: string;
  suffix?: string;
  description?: string;
  source_column?: string;
};

export type ChartSuggestion = {
  type: string;
  title: string;
  description: string;
  x?: string;
  y?: string;
  aggregation?: string;
  recommended_for_dashboard?: boolean;
};

export type ColumnProfile = {
  name: string;
  dtype: string;
  semantic_type: string;
  type_confidence: number;
  type_reason: string;
  missing_count: number;
  missing_percentage: number;
  unique_count: number;
  sample_values: string[];
};

export type DatasetProfile = {
  rows: number;
  columns: number;
  duplicate_rows: number;
  column_profiles: ColumnProfile[];
  statistics: Record<string, unknown>;
  kpis: Kpi[];
  chart_suggestions: ChartSuggestion[];
  cleaning_suggestions: Record<string, unknown>[];
};

export type DatasetAnalysis = {
  dataset_id: string;
  original_filename: string;
  stored_filename: string;
  extension: string;
  content_type: string | null;
  size_bytes: number;
  profile: DatasetProfile;
  created_at: string;
};

export type DashboardWidget = {
  id: string;
  widget_type: "kpi" | "chart" | string;
  title: string;
  config: Record<string, unknown>;
};

export type Dashboard = {
  id: string;
  dataset_id: string;
  title: string;
  slug: string;
  is_public: boolean;
  widgets: DashboardWidget[];
  dataset: DatasetAnalysis;
  public_url: string;
  created_at: string;
  updated_at: string;
};