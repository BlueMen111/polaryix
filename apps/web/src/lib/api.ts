import type { Dashboard, DatasetAnalysis } from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

export async function uploadDataset(file: File): Promise<{ dataset_id: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/datasets/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Erro ao enviar dataset.");
  }

  return response.json();
}

export async function listDatasets(): Promise<{ datasets: DatasetAnalysis[] }> {
  const response = await fetch(`${API_BASE_URL}/datasets`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Erro ao listar datasets.");
  }

  return response.json();
}

export async function getDataset(datasetId: string): Promise<DatasetAnalysis> {
  const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Erro ao buscar dataset.");
  }

  return response.json();
}

export async function createDashboard(payload: {
  dataset_id: string;
  title: string;
  slug?: string;
  is_public?: boolean;
}): Promise<{ dashboard: Dashboard }> {
  const response = await fetch(`${API_BASE_URL}/dashboards`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Erro ao criar dashboard.");
  }

  return response.json();
}

export async function listDashboards(): Promise<{ dashboards: Dashboard[] }> {
  const response = await fetch(`${API_BASE_URL}/dashboards`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Erro ao listar dashboards.");
  }

  return response.json();
}

export async function getPublicDashboard(slug: string): Promise<{ dashboard: Dashboard }> {
  const response = await fetch(`${API_BASE_URL}/dashboards/public/${slug}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Erro ao buscar dashboard público.");
  }

  return response.json();
}