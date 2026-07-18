// IndiaPix Metadata Automation System — TypeScript Type Definitions

export interface KeywordCategories {
  people: string[];
  action: string[];
  location: string[];
  setting: string[];
  technical: string[];
  conceptual: string[];
}

export interface MetadataResult {
  title: string;
  description: string;
  keywords: string[];
  category: string;
  location: string;
  mood: string;
  shotType: string;
  editorial: boolean;
  keywordCategories: KeywordCategories;
}

export interface VideoProperties {
  date_created?: string | null;
  duration_seconds?: number | null;
  frame_rate?: string | null;
  resolution?: string | null;
  aspect_ratio?: string | null;
  bitrate_kbps?: number | null;
  audio?: string | null;
}

export interface UploadResult {
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

export interface GenerateResult {
  job_id: string;
  filename: string;
  metadata: MetadataResult;
  duration_seconds?: number;
  frames_extracted: number;
  video_properties?: VideoProperties | null;
}

export type ProcessState =
  | "idle"
  | "uploading"
  | "uploaded"
  | "processing"
  | "complete"
  | "error";

// ── Phase 3 Types ───────────────────────────────────────────────────────────

export interface JobHistoryRecord {
  id: number;
  filename: string;
  upload_id: string;
  batch_id?: string | null;
  status: "completed" | "failed";
  metadata?: MetadataResult | null;
  video_properties?: VideoProperties | null;
  provider: string;
  frames_extracted: number;
  duration_seconds?: number | null;
  error_message?: string | null;
  created_at: string;
}

export interface JobHistorySearchResult {
  results: JobHistoryRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface AnalyticsSummary {
  total: number;
  completed: number;
  failed: number;
  total_frames: number;
}

export interface AnalyticsAllResponse {
  summary: {
    all: AnalyticsSummary;
    today: AnalyticsSummary;
    week: AnalyticsSummary;
    month: AnalyticsSummary;
  };
  daily: { date: string; total: number; completed: number; failed: number }[];
  top_categories: { name: string; count: number }[];
  top_locations: { name: string; count: number }[];
}

export interface CustomKeyword {
  id: number;
  keyword: string;
  category: string;
  is_active: boolean;
  created_at: string;
}

export interface AppSettings {
  [key: string]: string;
}

export interface PlatformPreset {
  id: string;
  name: string;
  columns: string[];
}