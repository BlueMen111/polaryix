import type { Dashboard, DatasetAnalysis } from "@/types";

const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
const API_BASE_URL = configuredApiUrl
  ? `${configuredApiUrl.replace(/\/api\/v1$/i, "")}/api/v1`
  : "/api/v1";
const CLIENT_ID_KEY = "polaryix:client-id";
const API_HTML_ERROR =
  "A API retornou uma página HTML em vez de JSON. Verifique se a URL da API/ngrok está correta e redeploye a Vercel.";

function shouldUseSameOriginApi() {
  if (typeof window === "undefined") {
    return false;
  }

  return !["localhost", "127.0.0.1"].includes(window.location.hostname);
}

function apiUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const baseUrl = shouldUseSameOriginApi() ? "/api/v1" : API_BASE_URL;

  return `${baseUrl}${normalizedPath}`;
}

function getClientId() {
  let clientId = window.localStorage.getItem(CLIENT_ID_KEY);
  if (!clientId) {
    clientId = crypto.randomUUID();
    window.localStorage.setItem(CLIENT_ID_KEY, clientId);
  }

  return clientId;
}

function apiHeaders(headers: HeadersInit = {}) {
  return {
    "ngrok-skip-browser-warning": "true",
    ...headers,
  };
}

function getAuthToken() {
  if (typeof window === "undefined") {
    return "";
  }

  return window.localStorage.getItem("polaryix:auth-token") ?? "";
}

function authHeaders(headers: HeadersInit = {}) {
  const token = getAuthToken();
  return {
    ...apiHeaders(headers),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function usageHeaders(headers: HeadersInit = {}) {
  const token = getAuthToken();
  return {
    ...apiHeaders(headers),
    "x-polaryix-client-id": getClientId(),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export type AuthUser = {
  id: string;
  name: string;
  email: string;
  is_premium: boolean;
  plan: string;
  billing: string;
  plan_started_at?: string | null;
  plan_expires_at?: string | null;
  credits_remaining?: number;
  monthly_credits?: number;
  max_file_size_mb?: number;
  max_concurrent_conversions?: number;
  priority_level?: number;
  avatar_url?: string | null;
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
  billing?: string;
  is_premium: boolean;
};

export type ConvertedFile = {
  id: string;
  original_filename: string;
  original_format: string;
  target_format: string;
  download_url?: string | null;
  file_size: number;
  status: "queued" | "processing" | "completed" | "failed" | "expired" | "deleted";
  error_message?: string | null;
  quality_requested?: string | null;
  quality_delivered?: string | null;
  is_premium_job?: boolean;
  priority_level?: number;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  expires_at?: string | null;
  deleted_at?: string | null;
};

export type WorkspaceFile = ConvertedFile & {
  size_bytes?: number;
  operation_type?: string;
  mime_type?: string | null;
  extension?: string;
  is_favorite?: boolean;
};

export type StorageSummary = {
  used: number;
  limit: number;
  percent: number;
  retention_hours: number;
};

export type DashboardSummary = {
  user: AuthUser;
  plan: string;
  credits: number;
  storage: StorageSummary;
  workspace_count: number;
  favorite_count: number;
  active_jobs: WorkspaceFile[];
  recent_jobs: WorkspaceFile[];
  favorite_files: WorkspaceFile[];
};

export type UserComment = {
  id: string;
  message: string;
  user_name: string;
  avatar_url?: string | null;
  created_at: string;
};

export type ConversionJob = {
  id: string;
  user_id: string;
  original_filename: string;
  input_format: string;
  output_format: string;
  status: "queued" | "processing" | "completed" | "failed" | "cancelled";
  priority: number;
  credits_cost: number;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  cancelled_at?: string | null;
  queue_position?: number | null;
  download_url?: string | null;
  is_priority?: boolean;
};

export type ImageToolOperation = "remove_background" | "optimize_image" | "upscale_image" | "remaster_image";

export type ImageToolJob = {
  id: string;
  operation: ImageToolOperation;
  status: "queued" | "processing" | "completed" | "failed" | "cancelled";
  queue_position?: number | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  error_message?: string | null;
  download_url?: string | null;
  credits_cost?: number;
  is_priority?: boolean;
  original_filename?: string;
  original_size?: number | null;
  final_size?: number | null;
  reduction_percent?: number | null;
  message?: string | null;
  tool_options?: Record<string, unknown>;
};

export type PaymentProvider = "mercadopago" | "paypal";
export type PaymentType = "donation" | "credits" | "premium";
export type PaymentStatus = "pending" | "approved" | "rejected" | "cancelled" | "expired" | "refunded" | "failed";

export type PaymentRecord = {
  id: string;
  user_id?: string | null;
  provider: PaymentProvider;
  type: PaymentType;
  amount: number;
  currency: string;
  status: PaymentStatus;
  external_payment_id?: string | null;
  checkout_url?: string | null;
  qr_code?: string | null;
  qr_code_base64?: string | null;
  created_at: string;
  updated_at: string;
  paid_at?: string | null;
  metadata: Record<string, unknown>;
};

export type PublicStats = {
  total_conversions: number;
  total_image_tools: number;
  total_downloads: number;
  updated_at: string;
};

async function parseJsonError(response: Response, fallback: string): Promise<string> {
  try {
    const errorData = await response.json();
    return typeof errorData.detail === "string" ? errorData.detail : fallback;
  } catch {
    return fallback;
  }
}

async function parseJsonResponse<T>(response: Response, fallback: string): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";

  if (!contentType.toLowerCase().includes("application/json")) {
    const body = await response.text();
    const preview = body.replace(/\s+/g, " ").trim().slice(0, 160);
    const detail = preview.startsWith("<!DOCTYPE") || preview.startsWith("<html") ? API_HTML_ERROR : fallback;

    throw new Error(preview ? `${detail} Trecho recebido: ${preview}` : detail);
  }

  return response.json();
}

export async function loginWithEmail(payload: { email: string; password: string }): Promise<AuthResponse> {
  const response = await fetch(apiUrl("/auth/login"), {
    method: "POST",
    headers: apiHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Não foi possível entrar."));
  }

  return parseJsonResponse<AuthResponse>(response, "Não foi possível entrar.");
}

export async function signupWithEmail(payload: { name: string; email: string; password: string; termsAccepted: boolean }): Promise<AuthResponse> {
  const response = await fetch(apiUrl("/auth/signup"), {
    method: "POST",
    headers: apiHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      name: payload.name,
      email: payload.email,
      password: payload.password,
      terms_accepted: payload.termsAccepted,
    }),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Não foi possível criar a conta."));
  }

  return parseJsonResponse<AuthResponse>(response, "Não foi possível criar a conta.");
}

export function persistAuthSession(data: AuthResponse) {
  window.localStorage.setItem("polaryix:auth-token", data.token);
  window.localStorage.setItem("polaryix:user", JSON.stringify(data.user));
  window.localStorage.setItem("polaryix:isPremium", String(data.user.is_premium));
  window.localStorage.setItem("polaryix:premiumPlan", data.user.plan ?? "free");
  window.localStorage.setItem("polaryix:premiumBilling", data.user.billing ?? "daily");
}

export function clearAuthSession() {
  window.localStorage.removeItem("polaryix:auth-token");
  window.localStorage.removeItem("polaryix:user");
  window.localStorage.removeItem("polaryix:isPremium");
  window.localStorage.removeItem("polaryix:premiumPlan");
  window.localStorage.removeItem("polaryix:premiumBilling");
}

export async function getCurrentUser(): Promise<{ user: AuthUser }> {
  const response = await fetch(apiUrl("/auth/me"), {
    headers: authHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Sessão expirada."));
  }

  return parseJsonResponse<{ user: AuthUser }>(response, "Não foi possível carregar sua conta.");
}

export async function logout() {
  await fetch(apiUrl("/auth/logout"), {
    method: "POST",
    headers: authHeaders(),
  });
  clearAuthSession();
}

export async function activatePremiumPlan(payload: { plan: "basic" | "pro"; billing: "monthly" | "annual" }): Promise<{ user: AuthUser }> {
  const response = await fetch(apiUrl("/auth/premium/activate"), {
    method: "POST",
    headers: authHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Não foi possível ativar o plano."));
  }

  const data = await parseJsonResponse<{ user: AuthUser }>(response, "Não foi possível ativar o plano.");
  persistAuthSession({ token: getAuthToken(), user: data.user });
  return data;
}

export async function createPayment(payload: {
  provider: PaymentProvider;
  type: PaymentType;
  amount?: number;
  currency?: string;
  plan?: "basic" | "pro";
  billing?: "monthly" | "annual";
  creditsPackage?: "starter" | "creator" | "studio";
  method?: "checkout" | "pix";
}): Promise<{ payment: PaymentRecord }> {
  const response = await fetch(apiUrl("/payments/create"), {
    method: "POST",
    headers: authHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      provider: payload.provider,
      type: payload.type,
      amount: payload.amount,
      currency: payload.currency ?? "BRL",
      plan: payload.plan,
      billing: payload.billing,
      credits_package: payload.creditsPackage,
      method: payload.method ?? "checkout",
    }),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel iniciar o pagamento."));
  }

  return parseJsonResponse<{ payment: PaymentRecord }>(response, "Nao foi possivel iniciar o pagamento.");
}

export async function getPaymentStatus(paymentId: string): Promise<{ payment: PaymentRecord }> {
  const response = await fetch(apiUrl(`/payments/${paymentId}/status`), {
    headers: authHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel consultar o pagamento."));
  }

  return parseJsonResponse<{ payment: PaymentRecord }>(response, "Nao foi possivel consultar o pagamento.");
}

export async function sandboxApprovePayment(paymentId: string): Promise<{ payment: PaymentRecord }> {
  const response = await fetch(apiUrl(`/payments/${paymentId}/sandbox/approve`), {
    method: "POST",
    headers: authHeaders(),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel simular a aprovacao."));
  }

  return parseJsonResponse<{ payment: PaymentRecord }>(response, "Nao foi possivel simular a aprovacao.");
}

export async function capturePayPalPayment(paymentId: string): Promise<{ payment: PaymentRecord }> {
  const response = await fetch(apiUrl(`/payments/paypal/${paymentId}/capture`), {
    method: "POST",
    headers: authHeaders(),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel capturar o pagamento PayPal."));
  }

  return parseJsonResponse<{ payment: PaymentRecord }>(response, "Nao foi possivel capturar o pagamento PayPal.");
}

export async function getPublicStats(): Promise<PublicStats> {
  const response = await fetch(apiUrl("/stats/public"), {
    headers: apiHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel carregar as estatisticas."));
  }

  return parseJsonResponse<PublicStats>(response, "Nao foi possivel carregar as estatisticas.");
}

export function startGoogleLogin() {
  window.location.href = apiUrl("/auth/oauth/google/start");
}

export async function exchangeGoogleCode(payload: { code: string; redirectUri: string }): Promise<AuthResponse> {
  const response = await fetch(apiUrl("/auth/oauth/google/exchange"), {
    method: "POST",
    headers: apiHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      code: payload.code,
      redirect_uri: payload.redirectUri,
    }),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Não foi possível concluir o login com Google."));
  }

  return parseJsonResponse<AuthResponse>(response, "Não foi possível concluir o login com Google.");
}

export async function getUsage(payload: { isPremium?: boolean; premiumPlan?: string } = {}): Promise<UsageInfo> {
  const params = new URLSearchParams({
    is_premium: String(Boolean(payload.isPremium)),
    premium_plan: payload.premiumPlan ?? "basic",
  });

  const response = await fetch(apiUrl(`/converter/usage?${params.toString()}`), {
    headers: usageHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Não foi possível carregar seus tokens."));
  }

  return parseJsonResponse<UsageInfo>(response, "Não foi possível carregar seus tokens.");
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

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.toLowerCase().includes("text/html")) {
    const body = await response.text();
    const preview = body.replace(/\s+/g, " ").trim().slice(0, 160);
    throw new Error(`${API_HTML_ERROR}${preview ? ` Trecho recebido: ${preview}` : ""}`);
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

async function blobResponse(response: Response, fallbackFilename: string): Promise<{ blob: Blob; filename: string }> {
  if (!response.ok) {
    const fallback = response.status === 401 ? "Voce nao tem permissao para baixar este arquivo." : "Operacao nao concluida.";
    throw new Error(await parseJsonError(response, fallback));
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.toLowerCase().includes("text/html")) {
    const body = await response.text();
    const preview = body.replace(/\s+/g, " ").trim().slice(0, 160);
    throw new Error(`${API_HTML_ERROR}${preview ? ` Trecho recebido: ${preview}` : ""}`);
  }

  const disposition = response.headers.get("content-disposition") ?? "";
  const filenameMatch = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^"]+)"?/i);
  const filename = decodeURIComponent(filenameMatch?.[1] ?? filenameMatch?.[2] ?? fallbackFilename);
  return { blob: await response.blob(), filename };
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

  const response = await fetch(apiUrl("/converter/convert-file"), {
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

  const response = await fetch(apiUrl("/converter/convert-batch"), {
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

  const response = await fetch(apiUrl("/converter/download-link"), {
    method: "POST",
    headers: usageHeaders(),
    body: formData,
  });

  const filename = await downloadBlobResponse(response, "polaryix-download");

  return { filename };
}

export type LinkDownloadJob = {
  id: string;
  status: "queued" | "running" | "ready" | "error";
  progress: number;
  message: string;
  filename?: string | null;
  download_url?: string | null;
  quality_delivered?: string | null;
};

export async function createLinkDownloadJob(payload: {
  url: string;
  mediaType: "video" | "audio";
  downloadFormat?: string;
  isPremium?: boolean;
  premiumPlan?: string;
}): Promise<LinkDownloadJob> {
  const formData = new FormData();
  formData.append("url", payload.url);
  formData.append("media_type", payload.mediaType);
  formData.append("download_format", payload.downloadFormat ?? payload.mediaType);
  formData.append("is_premium", String(Boolean(payload.isPremium)));
  formData.append("premium_plan", payload.premiumPlan ?? "basic");

  const response = await fetch(apiUrl("/converter/download-link/jobs"), {
    method: "POST",
    headers: usageHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Não foi possível iniciar o download."));
  }

  return parseJsonResponse<LinkDownloadJob>(response, "Não foi possível iniciar o download.");
}

export async function getLinkDownloadJob(jobId: string): Promise<LinkDownloadJob> {
  const response = await fetch(apiUrl(`/converter/download-link/jobs/${jobId}`), {
    headers: usageHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Não foi possível consultar o download."));
  }

  return parseJsonResponse<LinkDownloadJob>(response, "Não foi possível consultar o download.");
}

export async function downloadLinkJobFile(job: LinkDownloadJob): Promise<string> {
  if (!job.download_url) {
    throw new Error("O arquivo ainda não está pronto para download.");
  }

  const response = await fetch(job.download_url.startsWith("/api/v1") ? apiUrl(job.download_url.replace(/^\/api\/v1/i, "")) : job.download_url, {
    headers: usageHeaders(),
  });
  const filename = await downloadBlobResponse(response, job.filename ?? "polaryix-download");

  return filename;
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

  const response = await fetch(apiUrl("/converter/link-preview"), {
    method: "POST",
    headers: apiHeaders(),
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

  return parseJsonResponse<LinkPreview>(response, "Não foi possível carregar o preview.");
}

export async function listMyFiles(): Promise<{ files: ConvertedFile[] }> {
  const response = await fetch(apiUrl("/me/files"), {
    headers: authHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel carregar seus arquivos."));
  }

  return parseJsonResponse<{ files: ConvertedFile[] }>(response, "Nao foi possivel carregar seus arquivos.");
}

export async function downloadMyFile(file: ConvertedFile): Promise<string> {
  const response = await fetch(apiUrl(`/me/files/${file.id}/download`), {
    headers: authHeaders(),
  });

  return downloadBlobResponse(response, `${file.original_filename || "polaryix"}.${file.target_format?.toLowerCase() || "bin"}`);
}

export async function getDashboard(): Promise<DashboardSummary> {
  const response = await fetch(apiUrl("/dashboard"), {
    headers: authHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel carregar o dashboard."));
  }

  return parseJsonResponse<DashboardSummary>(response, "Nao foi possivel carregar o dashboard.");
}

export async function listWorkspaceFiles(payload: { q?: string; filter?: "all" | "favorites" | "expired" | "completed" | "queued" | "processing" | "failed" | "deleted" } = {}): Promise<{ files: WorkspaceFile[]; storage: StorageSummary }> {
  const params = new URLSearchParams();
  if (payload.q) params.set("q", payload.q);
  if (payload.filter) params.set("filter", payload.filter);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(apiUrl(`/workspace${suffix}`), {
    headers: authHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel carregar o Workspace."));
  }

  return parseJsonResponse<{ files: WorkspaceFile[]; storage: StorageSummary }>(response, "Nao foi possivel carregar o Workspace.");
}

export async function uploadWorkspaceFiles(files: File[]): Promise<{ files: WorkspaceFile[]; storage: StorageSummary }> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const response = await fetch(apiUrl("/workspace/upload"), {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel enviar os arquivos."));
  }

  return parseJsonResponse<{ files: WorkspaceFile[]; storage: StorageSummary }>(response, "Nao foi possivel enviar os arquivos.");
}

export async function convertWorkspaceFile(fileId: string, targetFormat: string): Promise<{ job: ConversionJob }> {
  const formData = new FormData();
  formData.append("target_format", targetFormat);
  const response = await fetch(apiUrl(`/workspace/${fileId}/convert`), {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel criar a conversao."));
  }

  return parseJsonResponse<{ job: ConversionJob }>(response, "Nao foi possivel criar a conversao.");
}

export async function processWorkspaceImage(fileId: string, operation: Exclude<ImageToolOperation, "remaster_image">, scale: 2 | 4 = 2): Promise<{ job: ImageToolJob }> {
  const formData = new FormData();
  formData.append("operation", operation);
  formData.append("scale", String(scale));
  const response = await fetch(apiUrl(`/workspace/${fileId}/image-tool`), {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel processar a imagem."));
  }

  return parseJsonResponse<{ job: ImageToolJob }>(response, "Nao foi possivel processar a imagem.");
}

export async function favoriteWorkspaceFile(fileId: string, favorite: boolean): Promise<{ file: WorkspaceFile }> {
  const response = await fetch(apiUrl(`/workspace/${fileId}/favorite`), {
    method: favorite ? "POST" : "DELETE",
    headers: authHeaders(),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel atualizar o favorito."));
  }

  return parseJsonResponse<{ file: WorkspaceFile }>(response, "Nao foi possivel atualizar o favorito.");
}

export async function deleteWorkspaceFile(fileId: string): Promise<{ file: WorkspaceFile; storage: StorageSummary }> {
  const response = await fetch(apiUrl(`/workspace/${fileId}`), {
    method: "DELETE",
    headers: authHeaders(),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel excluir o arquivo."));
  }

  return parseJsonResponse<{ file: WorkspaceFile; storage: StorageSummary }>(response, "Nao foi possivel excluir o arquivo.");
}

export async function downloadWorkspaceFile(file: WorkspaceFile): Promise<string> {
  const response = await fetch(apiUrl(`/workspace/${file.id}/download`), {
    headers: authHeaders(),
  });

  return downloadBlobResponse(response, file.original_filename ?? "polaryix-workspace");
}

export async function createConversionJob(payload: {
  file: File;
  fromFormat: string;
  toFormat: string;
}): Promise<{ job: ConversionJob }> {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("from_format", payload.fromFormat);
  formData.append("to_format", payload.toFormat);

  const response = await fetch(apiUrl("/conversions"), {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel criar a conversao."));
  }

  return parseJsonResponse<{ job: ConversionJob }>(response, "Nao foi possivel criar a conversao.");
}

export async function getConversionJob(jobId: string): Promise<{ job: ConversionJob }> {
  const response = await fetch(apiUrl(`/conversions/${jobId}`), {
    headers: authHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel consultar a conversao."));
  }

  return parseJsonResponse<{ job: ConversionJob }>(response, "Nao foi possivel consultar a conversao.");
}

export async function cancelConversionJob(jobId: string): Promise<{ job: ConversionJob }> {
  const response = await fetch(apiUrl(`/conversions/${jobId}`), {
    method: "DELETE",
    headers: authHeaders(),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel cancelar a conversao."));
  }

  return parseJsonResponse<{ job: ConversionJob }>(response, "Nao foi possivel cancelar a conversao.");
}

export async function downloadConversionJob(job: ConversionJob): Promise<string> {
  const response = await fetch(apiUrl(`/conversions/${job.id}/download`), {
    headers: authHeaders(),
  });

  return downloadBlobResponse(response, `${job.original_filename || "polaryix"}.${job.output_format?.toLowerCase() || "bin"}`);
}

function imageToolPath(operation: ImageToolOperation) {
  if (operation === "remove_background") {
    return "/image-tools/remove-background";
  }
  if (operation === "optimize_image") {
    return "/image-tools/optimize";
  }
  return "/image-tools/upscale";
}

function normalizeImageToolJob(payload: { job?: Partial<ImageToolJob> & { id?: string }; job_id?: string; operation?: ImageToolOperation; status?: ImageToolJob["status"]; queue_position?: number | null; download_url?: string | null; error_message?: string | null; created_at?: string; started_at?: string | null; finished_at?: string | null }): ImageToolJob {
  const job = payload.job ?? {};
  return {
    id: String(job.id ?? payload.job_id ?? ""),
    operation: ((job.operation ?? payload.operation ?? "optimize_image") === "remaster_image" ? "upscale_image" : (job.operation ?? payload.operation ?? "optimize_image")) as ImageToolOperation,
    status: (job.status ?? payload.status ?? "queued") as ImageToolJob["status"],
    queue_position: job.queue_position ?? payload.queue_position ?? null,
    created_at: String(job.created_at ?? payload.created_at ?? ""),
    started_at: job.started_at ?? payload.started_at ?? null,
    finished_at: job.finished_at ?? payload.finished_at ?? null,
    error_message: job.error_message ?? payload.error_message ?? null,
    download_url: payload.download_url ?? job.download_url ?? null,
    credits_cost: job.credits_cost,
    is_priority: job.is_priority,
    original_filename: job.original_filename,
    original_size: job.original_size ?? null,
    final_size: job.final_size ?? null,
    reduction_percent: job.reduction_percent ?? null,
    message: job.message ?? null,
    tool_options: job.tool_options ?? {},
  };
}

export async function createImageToolJob(payload: {
  operation: ImageToolOperation;
  file: File;
  scale?: 2 | 4;
  keepOriginalSize?: boolean;
  sharpness?: number;
  denoise?: number;
  contrast?: number;
  detail?: number;
  intensity?: number;
}): Promise<ImageToolJob> {
  const formData = new FormData();
  formData.append("file", payload.file);
  if (payload.operation === "upscale_image" || payload.operation === "remaster_image") {
    formData.append("scale", String(payload.scale ?? 2));
    formData.append("keep_original_size", String(Boolean(payload.keepOriginalSize)));
    for (const key of ["sharpness", "denoise", "contrast", "detail", "intensity"] as const) {
      const value = payload[key];
      if (typeof value === "number") {
        formData.append(key, String(value));
      }
    }
  }

  const response = await fetch(apiUrl(imageToolPath(payload.operation)), {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel criar o processamento."));
  }

  const data = await parseJsonResponse<{ job?: ImageToolJob; job_id?: string; operation?: ImageToolOperation; status?: ImageToolJob["status"]; queue_position?: number | null }>(response, "Nao foi possivel criar o processamento.");
  return normalizeImageToolJob(data);
}

export async function getImageToolJob(jobId: string): Promise<ImageToolJob> {
  const response = await fetch(apiUrl(`/image-tools/jobs/${jobId}`), {
    headers: authHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel consultar o processamento."));
  }

  const data = await parseJsonResponse<{ job?: ImageToolJob; job_id?: string; operation?: ImageToolOperation; status?: ImageToolJob["status"]; queue_position?: number | null; download_url?: string | null }>(response, "Nao foi possivel consultar o processamento.");
  return normalizeImageToolJob(data);
}

export async function cancelImageToolJob(jobId: string): Promise<ImageToolJob> {
  const response = await fetch(apiUrl(`/image-tools/jobs/${jobId}`), {
    method: "DELETE",
    headers: authHeaders(),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel cancelar o processamento."));
  }

  const data = await parseJsonResponse<{ job: ImageToolJob }>(response, "Nao foi possivel cancelar o processamento.");
  return normalizeImageToolJob(data);
}

export async function downloadImageToolJob(job: ImageToolJob): Promise<string> {
  const response = await fetch(apiUrl(`/image-tools/jobs/${job.id}/download`), {
    headers: authHeaders(),
  });

  return downloadBlobResponse(response, job.original_filename ?? "polaryix-image");
}

export async function getImageToolJobResult(job: ImageToolJob): Promise<{ url: string; filename: string; blob: Blob }> {
  const response = await fetch(apiUrl(`/image-tools/jobs/${job.id}/download`), {
    headers: authHeaders(),
    cache: "no-store",
  });

  const { blob, filename } = await blobResponse(response, job.original_filename ?? "polaryix-image");
  return { blob, filename, url: URL.createObjectURL(blob) };
}

export async function listComments(): Promise<{ comments: UserComment[] }> {
  const response = await fetch(apiUrl("/comments"), {
    headers: apiHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Nao foi possivel carregar os comentarios."));
  }

  return parseJsonResponse<{ comments: UserComment[] }>(response, "Nao foi possivel carregar os comentarios.");
}

export async function createComment(message: string): Promise<{ comment: UserComment }> {
  const response = await fetch(apiUrl("/comments"), {
    method: "POST",
    headers: authHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    throw new Error(await parseJsonError(response, "Faca login para comentar."));
  }

  return parseJsonResponse<{ comment: UserComment }>(response, "Nao foi possivel enviar seu comentario.");
}

export async function uploadDataset(file: File): Promise<{ dataset: DatasetAnalysis }> {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(apiUrl("/datasets/upload"), {
      method: "POST",
      headers: apiHeaders(),
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

    return parseJsonResponse<{ dataset: DatasetAnalysis }>(response, "Erro ao enviar dataset.");
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
  const response = await fetch(apiUrl("/datasets"), {
    headers: apiHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Erro ao listar datasets.");
  }

  return parseJsonResponse<{ datasets: DatasetAnalysis[] }>(response, "Erro ao listar datasets.");
}

export async function getDataset(datasetId: string): Promise<{ dataset: DatasetAnalysis }> {
  const response = await fetch(apiUrl(`/datasets/${datasetId}`), {
    headers: apiHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Erro ao buscar dataset.");
  }

  return parseJsonResponse<{ dataset: DatasetAnalysis }>(response, "Erro ao buscar dataset.");
}

export async function createDashboard(payload: {
  dataset_id: string;
  title: string;
  slug?: string;
  is_public?: boolean;
}): Promise<{ dashboard: Dashboard }> {
  const response = await fetch(apiUrl("/dashboards"), {
    method: "POST",
    headers: apiHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Erro ao criar dashboard.");
  }

  return parseJsonResponse<{ dashboard: Dashboard }>(response, "Erro ao criar dashboard.");
}

export async function listDashboards(): Promise<{ dashboards: Dashboard[] }> {
  const response = await fetch(apiUrl("/dashboards"), {
    headers: apiHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Erro ao listar dashboards.");
  }

  return parseJsonResponse<{ dashboards: Dashboard[] }>(response, "Erro ao listar dashboards.");
}

export async function getPublicDashboard(slug: string): Promise<{ dashboard: Dashboard }> {
  const response = await fetch(apiUrl(`/dashboards/public/${slug}`), {
    headers: apiHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Erro ao buscar dashboard público.");
  }

  const data = await parseJsonResponse<Dashboard | { dashboard: Dashboard }>(response, "Erro ao buscar dashboard público.");

  return "dashboard" in data ? data : { dashboard: data };
}
