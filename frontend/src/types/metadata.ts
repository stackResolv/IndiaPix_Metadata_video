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
