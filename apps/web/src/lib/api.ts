import type { Dashboard, DatasetAnalysis } from "@/types";

const API_BASE_URL = "/api/v1";
const CLIENT_ID_KEY = "polaryix:client-id";

function getClientId() {
  let clientId = window.localStorage.getItem(CLIENT_ID_KEY);
  if (!clientId) {
    clientId = crypto.randomUUID();
    window.localStorage.setItem(CLIENT_ID_KEY, clientId);
  }

  return clientId;
}

function usageHeaders() {
  return {
    "x-polaryix-client-id": getClientId(),
  };
}

export type AuthUser = {
  id: string;
  name: string;
  email: string;
  is_premium: boolean;
};

export type AuthResponse = {
  token: string;
  user: AuthUser;
};

export type UsageInfo = {
  used: number;
  limit: number;
  remaining: number;
  reset_at: string;
  plan: string;
  is_premium: boolean;
};

async function parseJsonError(response: Response, fallback: string): Promise<string> {
  try {
    const errorData = await response.json();
    return typeof errorData.detail === "string" ? errorData.detail : fallback;
  } catch {
    return fallback;
  }
}

export async function loginWithEmail(payload: { email: string; password: string }): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Não foi possível entrar."));
  }

  return response.json();
}

export async function signupWithEmail(payload: { name: string; email: string; password: string }): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/signup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Não foi possível criar a conta."));
  }

  return response.json();
}

export function persistAuthSession(data: AuthResponse) {
  window.localStorage.setItem("polaryix:auth-token", data.token);
  window.localStorage.setItem("polaryix:user", JSON.stringify(data.user));
  window.localStorage.setItem("polaryix:isPremium", String(data.user.is_premium));
}

export async function getUsage(payload: { isPremium?: boolean; premiumPlan?: string } = {}): Promise<UsageInfo> {
  const params = new URLSearchParams({
    is_premium: String(Boolean(payload.isPremium)),
    premium_plan: payload.premiumPlan ?? "basic",
  });

  const response = await fetch(`${API_BASE_URL}/converter/usage?${params.toString()}`, {
    headers: usageHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Não foi possível carregar seus tokens."));
  }

  return response.json();
}

async function downloadBlobResponse(response: Response, fallbackFilename: string): Promise<string> {
  if (!response.ok) {
    let detail = "Operação não concluída.";

    try {
      const errorData = await response.json();
      detail = typeof errorData.detail === "string" ? errorData.detail : detail;
    } catch {
      // Mantém mensagem padrão quando o erro não é JSON.
    }

    throw new Error(detail);
  }

  const disposition = response.headers.get("content-disposition") ?? "";
  const filenameMatch = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^"]+)"?/i);
  const filename = decodeURIComponent(filenameMatch?.[1] ?? filenameMatch?.[2] ?? fallbackFilename);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);

  return filename;
}

export async function convertFile(payload: {
  file: File;
  fromFormat: string;
  toFormat: string;
  isPremium?: boolean;
  premiumPlan?: string;
}): Promise<{ filename: string }> {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("from_format", payload.fromFormat);
  formData.append("to_format", payload.toFormat);
  formData.append("is_premium", String(Boolean(payload.isPremium)));
  formData.append("premium_plan", payload.premiumPlan ?? "basic");

  const response = await fetch(`${API_BASE_URL}/converter/convert-file`, {
    method: "POST",
    headers: usageHeaders(),
    body: formData,
  });

  const filename = await downloadBlobResponse(response, `polaryix-${payload.toFormat.toLowerCase()}`);

  return { filename };
}

export async function convertFiles(payload: {
  files: File[];
  fromFormat: string;
  toFormat: string;
  isPremium: boolean;
  premiumPlan?: string;
}): Promise<{ filename: string }> {
  const formData = new FormData();

  payload.files.forEach((file) => {
    formData.append("files", file);
  });

  formData.append("from_format", payload.fromFormat);
  formData.append("to_format", payload.toFormat);
  formData.append("is_premium", String(payload.isPremium));
  formData.append("premium_plan", payload.premiumPlan ?? "basic");

  const response = await fetch(`${API_BASE_URL}/converter/convert-batch`, {
    method: "POST",
    headers: usageHeaders(),
    body: formData,
  });

  const filename = await downloadBlobResponse(response, "polaryix-conversoes.zip");

  return { filename };
}

export async function downloadFromLink(payload: {
  url: string;
  mediaType: "video" | "audio";
  downloadFormat?: string;
  isPremium?: boolean;
  premiumPlan?: string;
}): Promise<{ filename: string }> {
  const formData = new FormData();
  formData.append("url", payload.url);
  formData.append("media_type", payload.mediaType);
  formData.append("download_format", payload.downloadFormat ?? payload.mediaType);
  formData.append("is_premium", String(Boolean(payload.isPremium)));
  formData.append("premium_plan", payload.premiumPlan ?? "basic");

  const response = await fetch(`${API_BASE_URL}/converter/download-link`, {
    method: "POST",
    headers: usageHeaders(),
    body: formData,
  });

  const filename = await downloadBlobResponse(response, "polaryix-download");

  return { filename };
}

export type LinkPreview = {
  title: string;
  thumbnail?: string | null;
  duration?: number | null;
  uploader?: string | null;
  webpage_url: string;
};

export async function getLinkPreview(url: string): Promise<LinkPreview> {
  const formData = new FormData();
  formData.append("url", url);

  const response = await fetch(`${API_BASE_URL}/converter/link-preview`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let detail = "Não foi possível carregar o preview.";

    try {
      const errorData = await response.json();
      detail = typeof errorData.detail === "string" ? errorData.detail : detail;
    } catch {
      // Mantém mensagem padrão quando o erro não é JSON.
    }

    throw new Error(detail);
  }

  return response.json();
}

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
