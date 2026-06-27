import type { Dashboard, DatasetAnalysis } from "@/types";

const API_BASE_URL = "/api/v1";

export async function uploadDataset(file: File): Promise<{ dataset: DatasetAnalysis }> {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${API_BASE_URL}/datasets/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let detail = "Erro ao enviar dataset.";

      try {
        const errorData = await response.json();
        detail = typeof errorData.detail === "string" ? errorData.detail : detail;
      } catch {
        // Ignora erro ao parsear resposta não JSON.
      }

      throw new Error(detail);
    }

    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      throw new Error(
        "Não foi possível conectar à API de upload. Verifique se o backend está em execução e se a rota está disponível."
      );
    }

    throw error;
  }
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

export async function getDataset(datasetId: string): Promise<{ dataset: DatasetAnalysis }> {
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

  const data = await response.json();

  return "dashboard" in data ? data : { dashboard: data };
}
