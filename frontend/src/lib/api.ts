// IndiaPix Metadata Automation System — API Client
// Communicates with the FastAPI backend

import type { VideoProperties } from "@/types/metadata";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 120_000; // 120 seconds for metadata generation
const DEFAULT_UPLOAD_TIMEOUT_MS = 300_000; // 300 seconds for large uploads

/**
 * Custom error class that includes HTTP status and error type for better UX.
 */
export class ApiError extends Error {
  status: number;
  type: "network" | "timeout" | "server" | "validation" | "unknown";

  constructor(
    message: string,
    status: number = 0,
    type: "network" | "timeout" | "server" | "validation" | "unknown" = "unknown"
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.type = type;
  }

  get isRetryable(): boolean {
    return this.type === "network" || this.type === "timeout" || this.status >= 500;
  }
}

/**
 * Create an AbortController-based fetch with timeout.
 * Returns both the fetch promise and the abort controller.
 */
function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): { promise: Promise<Response>; abort: () => void } {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const promise = fetch(url, {
    ...options,
    signal: controller.signal,
  }).finally(() => clearTimeout(timeoutId));

  return {
    promise,
    abort: () => {
      clearTimeout(timeoutId);
      controller.abort();
    },
  };
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const { promise, abort } = fetchWithTimeout(url, options, timeoutMs);

  let response: Response;
  try {
    response = await promise;
  } catch (err: any) {
    if (err.name === "AbortError") {
      throw new ApiError(
        "Request timed out. The server took too long to respond.",
        0,
        "timeout"
      );
    }
    throw new ApiError(
      `Network error: ${err.message || "Unable to reach server"}`,
      0,
      "network"
    );
  }

  if (!response.ok) {
    const errorBody = await response.text();
    let detail = `HTTP ${response.status}: ${response.statusText}`;
    let errorType: ApiError["type"] = "server";

    if (response.status >= 400 && response.status < 500) {
      errorType = "validation";
    }

    try {
      const parsed = JSON.parse(errorBody);
      if (parsed.detail) detail = parsed.detail;
    } catch {
      if (errorBody) detail = errorBody;
    }

    throw new ApiError(detail, response.status, errorType);
  }

  // For CSV/text responses
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("text/csv")) {
    return (await response.text()) as unknown as T;
  }

  return response.json();
}

// ── Upload ────────────────────────────────────────────────────────────────

export interface UploadResponse {
  upload_id: string;
  filename: string;
  stored_path: string;
  is_video: boolean;
  file_size_bytes: number;
  duration_seconds?: number;
  duration_display?: string;
  frame_count?: number;
  date_created?: string | null;
  frame_rate?: string | null;
  resolution?: string | null;
  aspect_ratio?: string | null;
  bitrate_kbps?: number | null;
  audio?: string | null;
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return request<UploadResponse>(
    "/api/upload/",
    {
      method: "POST",
      body: formData,
    },
    DEFAULT_UPLOAD_TIMEOUT_MS
  );
}

// ── Metadata Generation ───────────────────────────────────────────────────

export interface GenerateResponse {
  job_id: string;
  filename: string;
  metadata: {
    title: string;
    description: string;
    keywords: string[];
    category: string;
    location: string;
    mood: string;
    shotType: string;
    editorial: boolean;
    keywordCategories: {
      people: string[];
      action: string[];
      location: string[];
      setting: string[];
      technical: string[];
      conceptual: string[];
    };
  };
  duration_seconds?: number;
  frames_extracted: number;
  video_properties?: VideoProperties | null;
}

/**
 * Generate metadata with abort support.
 * Returns both the promise and an abort function.
 */
export function generateMetadataWithAbort(
  uploadId: string,
  description: string = "",
  provider: string = ""
): { promise: Promise<GenerateResponse>; abort: () => void } {
  const params = new URLSearchParams();
  params.append("upload_id", uploadId);
  if (description) params.append("description", description);
  if (provider) params.append("provider", provider);

  const url = `${API_BASE}/api/metadata/generate?${params.toString()}`;
  const { promise, abort } = fetchWithTimeout(url, {
    method: "POST",
  });

  const wrappedPromise = (async () => {
    let response: Response;
    try {
      response = await promise;
    } catch (err: any) {
      if (err.name === "AbortError") {
        throw new ApiError(
          "Metadata generation timed out after 120 seconds.",
          0,
          "timeout"
        );
      }
      throw new ApiError(
        `Network error: ${err.message || "Unable to reach server"}`,
        0,
        "network"
      );
    }

    if (!response.ok) {
      const errorBody = await response.text();
      let detail = `HTTP ${response.status}: ${response.statusText}`;
      let errorType: ApiError["type"] = "server";
      if (response.status >= 400 && response.status < 500) {
        errorType = "validation";
      }
      try {
        const parsed = JSON.parse(errorBody);
        if (parsed.detail) detail = parsed.detail;
      } catch {
        if (errorBody) detail = errorBody;
      }
      throw new ApiError(detail, response.status, errorType);
    }

    return response.json();
  })();

  return { promise: wrappedPromise, abort };
}

export async function generateMetadata(
  uploadId: string,
  description: string = "",
  provider: string = ""
): Promise<GenerateResponse> {
  const { promise } = generateMetadataWithAbort(uploadId, description, provider);
  return promise;
}

// ── CSV Export ────────────────────────────────────────────────────────────

export async function exportCsv(
  filename: string,
  metadata: GenerateResponse["metadata"],
  videoProperties?: VideoProperties
): Promise<Blob> {
  const body: Record<string, unknown> = { filename, metadata };
  if (videoProperties) {
    body.video_properties = videoProperties;
  }
  const response = await fetch(`${API_BASE}/api/export/csv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    let detail = `Export failed: ${response.statusText}`;
    try {
      const parsed = JSON.parse(errorBody);
      if (parsed.detail) detail = parsed.detail;
    } catch {
      if (errorBody) detail = errorBody;
    }
    throw new Error(detail);
  }

  return response.blob();
}

// ── Health Check ──────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  ffmpeg_available: boolean;
  ffprobe_available: boolean;
  default_provider: string;
  claude_configured: boolean;
  openai_configured: boolean;
}

// ── Batch Processing ────────────────────────────────────────────────────────

export interface BatchJobStatus {
  upload_id: string;
  filename: string;
  status: "pending" | "processing" | "completed" | "failed";
  frames_extracted: number;
  error_message?: string | null;
  error_type?: string;
  metadata?: GenerateResponse["metadata"] | null;
  video_properties?: VideoProperties | null;
  duration_seconds?: number | null;
}

export interface BatchStatusResponse {
  batch_id: string;
  total_jobs: number;
  completed_count: number;
  failed_count: number;
  is_running: boolean;
  is_complete: boolean;
  jobs: BatchJobStatus[];
  created_at: number;
  completed_at?: number | null;
}

export interface BatchStartRequest {
  upload_ids: string[];
  descriptions?: Record<string, string>;
  provider?: string;
}

export async function batchStart(
  payload: BatchStartRequest
): Promise<BatchStatusResponse> {
  return request<BatchStatusResponse>("/api/batch/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function batchStatus(
  batchId: string
): Promise<BatchStatusResponse> {
  return request<BatchStatusResponse>(`/api/batch/status/${batchId}`);
}

export async function batchExportCsv(batchId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/batch/export-csv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ batch_id: batchId }),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    let detail = `Batch export failed: ${response.statusText}`;
    try {
      const parsed = JSON.parse(errorBody);
      if (parsed.detail) detail = parsed.detail;
    } catch {
      if (errorBody) detail = errorBody;
    }
    throw new Error(detail);
  }

  return response.blob();
}

export async function batchRetryFailed(
  batchId: string
): Promise<BatchStatusResponse> {
  return request<BatchStatusResponse>(`/api/batch/retry/${batchId}`, {
    method: "POST",
  });
}

export async function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}
