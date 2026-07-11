"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  uploadFile,
  generateMetadataWithAbort,
  exportCsv,
  ApiError,
  UploadResponse,
  GenerateResponse,
} from "@/lib/api";
import type { ProcessState, VideoProperties } from "@/types/metadata";

// Format duration seconds to HH:MM:SS sec (e.g., 78.72 → "0:01:19 sec")
function formatDuration(seconds?: number | null): string {
  if (seconds == null) return "";
  const totalSecs = Math.ceil(seconds);
  const h = Math.floor(totalSecs / 3600);
  const m = Math.floor((totalSecs % 3600) / 60);
  const s = totalSecs % 60;
  return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")} sec`;
}

type AIProvider = "claude" | "openai";

export default function HomePage() {
  // ── State ──────────────────────────────────────────────────────────────
  const [processState, setProcessState] = useState<ProcessState>("idle");
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [generateResult, setGenerateResult] =
    useState<GenerateResponse | null>(null);
  const [description, setDescription] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<string>("server");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [aiProvider, setAiProvider] = useState<AIProvider>("claude");
  const [claudeConfigured, setClaudeConfigured] = useState(false);
  const [openaiConfigured, setOpenaiConfigured] = useState(false);

  // Reference to the abort function for cancellation
  const abortGenerateRef = useRef<(() => void) | null>(null);

  // On mount, check the backend health to determine which providers are available
  useEffect(() => {
    (async () => {
      try {
        const { checkHealth } = await import("@/lib/api");
        const health = await checkHealth();
        setClaudeConfigured(health.claude_configured);
        setOpenaiConfigured(health.openai_configured);
        if (health.default_provider === "openai" && health.openai_configured) {
          setAiProvider("openai");
        } else if (health.default_provider === "claude" && health.claude_configured) {
          setAiProvider("claude");
        } else if (health.openai_configured) {
          setAiProvider("openai");
        } else if (health.claude_configured) {
          setAiProvider("claude");
        }
      } catch {
        // Backend unreachable — keep defaults
      }
    })();
  }, []);

  // Editable metadata state
  const [editableMetadata, setEditableMetadata] = useState<
    GenerateResponse["metadata"] | null
  >(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── File Handling ──────────────────────────────────────────────────────

  const handleFileSelect = useCallback(async (file: File | null) => {
    if (!file) return;

    // Validate file type
    const validExtensions = [
      ".mp4",
      ".mov",
      ".avi",
      ".mxf",
      ".m4v",
      ".wmv",
      ".jpg",
      ".jpeg",
      ".png",
      ".tiff",
      ".tif",
    ];
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!validExtensions.includes(ext)) {
      setErrorMessage(
        `Unsupported file type "${ext}". Supported: ${validExtensions.join(", ")}`
      );
      return;
    }

    setSelectedFile(file);
    setProcessState("uploading");
    setErrorMessage(null);
    setGenerateResult(null);
    setEditableMetadata(null);

    try {
      const result = await uploadFile(file);
      setUploadResult(result);
      setProcessState("uploaded");
      // User clicks "Generate Metadata" manually — no auto-generation
    } catch (err: any) {
      setErrorMessage(err.message || "Upload failed");
      setProcessState("error");
    }
  }, []);

  // ── Metadata Generation ─────────────────────────────────────────────────

  const handleGenerate = async (uploadId: string, desc: string) => {
    setIsGenerating(true);
    setProcessState("processing");
    setErrorMessage(null);

    const { promise, abort } = generateMetadataWithAbort(
      uploadId,
      desc,
      aiProvider
    );
    abortGenerateRef.current = abort;

    try {
      const result = await promise;
      setGenerateResult(result);
      // Deep copy for editing
      setEditableMetadata(JSON.parse(JSON.stringify(result.metadata)));
      setProcessState("complete");
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
        setErrorType(err.type);
        // If it was a timeout/network error and we're still in a retryable state,
        // show a retry hint
        if (err.isRetryable) {
          setErrorMessage(`${err.message} You can try again.`);
        }
      } else {
        setErrorMessage(err.message || "Metadata generation failed");
        setErrorType("unknown");
      }
      setProcessState("error");
    } finally {
      setIsGenerating(false);
      abortGenerateRef.current = null;
    }
  };

  // ── Cancel Generation ──────────────────────────────────────────────────

  const handleCancelGenerate = () => {
    if (abortGenerateRef.current) {
      abortGenerateRef.current();
      abortGenerateRef.current = null;
    }
    setIsGenerating(false);
    setProcessState("uploaded");
    setErrorMessage("Generation was cancelled.");
    setErrorType("cancelled");
  };

  // ── Regenerate ──────────────────────────────────────────────────────────

  const handleRegenerate = () => {
    if (uploadResult) {
      setProcessState("processing");
      handleGenerate(uploadResult.upload_id, description);
    }
  };

  // ── CSV Export ──────────────────────────────────────────────────────────

  const handleExportWithProps = async () => {
    if (!editableMetadata || !generateResult) return;
    setIsExporting(true);

    try {
      const videoProps: VideoProperties | undefined = generateResult.video_properties || undefined;
      const blob = await exportCsv(
        generateResult.filename,
        editableMetadata,
        videoProps,
      );
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download =
        generateResult.filename.replace(/\.[^/.]+$/, "") + "_metadata.csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setErrorMessage(err.message || "Export failed");
    } finally {
      setIsExporting(false);
    }
  };

  // ── Clear / Reset ───────────────────────────────────────────────────────

  const handleReset = () => {
    setProcessState("idle");
    setUploadResult(null);
    setGenerateResult(null);
    setEditableMetadata(null);
    setSelectedFile(null);
    setDescription("");
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // ── Editable field handlers ─────────────────────────────────────────────

  const updateMetadata = useCallback(
    (field: string, value: any) => {
      setEditableMetadata((prev) => {
        if (!prev) return prev;
        return { ...prev, [field]: value };
      });
    },
    []
  );

  const updateKeywordCategory = useCallback(
    (category: string, keywords: string[]) => {
      setEditableMetadata((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          keywordCategories: {
            ...prev.keywordCategories,
            [category]: keywords,
          },
        };
      });
    },
    []
  );

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Header Info */}
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900">
          Video & Image Metadata Generator
        </h2>
        <p className="mt-2 text-gray-600">
          Upload a file to automatically generate stock-optimized metadata
        </p>
      </div>

      {/* Step 1: Upload / File Selection */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            {processState === "idle" ? "1. Select File" : "Selected File"}
          </h3>
          {processState !== "idle" && (
            <button onClick={handleReset} className="btn-secondary text-sm py-2 px-4">
              Clear & Reset
            </button>
          )}
        </div>

        {processState === "idle" && (
          <div
            className="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center cursor-pointer hover:border-indiapix-400 hover:bg-indiapix-50/30 transition-colors"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              const files = e.dataTransfer.files;
              if (files.length > 0) handleFileSelect(files[0]);
            }}
          >
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="mt-4 text-gray-600 font-medium">
              Drag & drop or click to browse
            </p>
            <p className="mt-1 text-sm text-gray-400">
              Videos: MP4, MOV, AVI, MXF, M4V, WMV &nbsp;|&nbsp; Images: JPG,
              PNG, TIFF
            </p>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".mp4,.mov,.avi,.mxf,.m4v,.wmv,.jpg,.jpeg,.png,.tiff,.tif"
              onChange={(e) =>
                handleFileSelect(e.target.files?.[0] || null)
              }
            />
          </div>
        )}

        {selectedFile && uploadResult && (
          <div className="space-y-3">
            <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
              <div className="w-10 h-10 bg-indiapix-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <svg
                  className="w-5 h-5 text-indiapix-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {selectedFile.name}
                </p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB
                  {uploadResult.is_video && uploadResult.duration_seconds != null && (
                    <span> &middot; {formatDuration(uploadResult.duration_seconds)}</span>
                  )}
                  {uploadResult.is_video && uploadResult.frame_count && (
                    <span> &middot; {uploadResult.frame_count} frames</span>
                  )}
                </p>
                {/* Video properties badges */}
                {uploadResult.is_video && (
                  <div className="flex flex-wrap gap-1.5 mt-0.5">
                    {uploadResult.resolution && (
                      <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{uploadResult.resolution}</span>
                    )}
                    {uploadResult.frame_rate && (
                      <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{uploadResult.frame_rate}</span>
                    )}
                    {uploadResult.aspect_ratio && (
                      <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{uploadResult.aspect_ratio}</span>
                    )}
                    {uploadResult.bitrate_kbps && (
                      <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{uploadResult.bitrate_kbps} kbps</span>
                    )}
                    {uploadResult.audio != null && (
                      <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{uploadResult.audio}</span>
                    )}
                    {uploadResult.date_created && (
                      <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{uploadResult.date_created}</span>
                    )}
                    {uploadResult.duration_seconds != null && (
                      <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{formatDuration(uploadResult.duration_seconds)}</span>
                    )}
                  </div>
                )}
              </div>
              <span className="text-xs font-medium text-green-600 bg-green-50 px-3 py-1 rounded-full">
                Uploaded
              </span>
            </div>

              <div>
                <label className="section-label">
                  Description (optional context for AI)
                </label>
                <textarea
                  className="input-field"
                  rows={2}
                  placeholder={uploadResult?.is_video ? "e.g., Wedding ceremony in Jaipur, shot at sunset" : "e.g., Traditional Indian wedding in Jaipur during sunset"}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={isGenerating}
                />
              </div>

            {/* AI Provider Selector */}
            <div>
              <label className="section-label">AI Model</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  className={`flex-1 px-4 py-2.5 rounded-lg border-2 font-medium text-sm transition-all ${
                    !claudeConfigured
                      ? "border-gray-100 bg-gray-50 text-gray-300 cursor-not-allowed"
                      : aiProvider === "claude"
                        ? "border-indiapix-500 bg-indiapix-50 text-indiapix-700"
                        : "border-gray-200 bg-white text-gray-500 hover:border-gray-300"
                  }`}
                  onClick={() => claudeConfigured && setAiProvider("claude")}
                  disabled={isGenerating || !claudeConfigured}
                  title={!claudeConfigured ? "Claude API key not configured in .env" : "Use Claude (Anthropic)"}
                >
                  <div className="flex items-center justify-center gap-2">
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                    Claude (Anthropic)
                    {!claudeConfigured && <span className="text-[10px] ml-1">— no key</span>}
                  </div>
                </button>
                <button
                  type="button"
                  className={`flex-1 px-4 py-2.5 rounded-lg border-2 font-medium text-sm transition-all ${
                    !openaiConfigured
                      ? "border-gray-100 bg-gray-50 text-gray-300 cursor-not-allowed"
                      : aiProvider === "openai"
                        ? "border-green-500 bg-green-50 text-green-700"
                        : "border-gray-200 bg-white text-gray-500 hover:border-gray-300"
                  }`}
                  onClick={() => openaiConfigured && setAiProvider("openai")}
                  disabled={isGenerating || !openaiConfigured}
                  title={!openaiConfigured ? "OpenAI API key not configured in .env" : "Use GPT-4o (OpenAI)"}
                >
                  <div className="flex items-center justify-center gap-2">
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5095-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.9847 5.9847 0 0 0 .5157 4.9108 6.0462 6.0462 0 0 0 6.5095 2.9 6.0651 6.0651 0 0 0 10.7907-2.1819 5.9847 5.9847 0 0 0 3.9977-2.9 6.0462 6.0462 0 0 0-.7427-7.0966zM12.0145 19.366a7.3555 7.3555 0 0 1-5.0326-1.6367 1.4986 1.4986 0 0 1 .1518-2.2716 1.5002 1.5002 0 0 1 1.0833-.4093 1.4997 1.4997 0 0 1 1.0726.4477 4.3585 4.3585 0 0 0 2.7251.8693 4.3719 4.3719 0 0 0 2.7248-.8693 1.5 1.5 0 0 1 2.1557 2.0842 7.3555 7.3555 0 0 1-4.8801 1.7857zm.0224-4.3541a1.4895 1.4895 0 0 1-1.4176-.9918 4.3442 4.3442 0 0 0-3.2535-2.6523 1.5 1.5 0 0 1 .5889-2.9408 7.3379 7.3379 0 0 1 5.0023 1.6367 1.5 1.5 0 0 1-.92 2.9482z"/>
                    </svg>
                    GPT-4o (OpenAI)
                    {!openaiConfigured && <span className="text-[10px] ml-1">— no key</span>}
                  </div>
                </button>
              </div>
            </div>
          </div>
        )}

        {processState === "uploaded" && !isGenerating && (
          <div className="mt-4">
            <button
              className="btn-primary"
              onClick={() =>
                uploadResult &&
                handleGenerate(uploadResult.upload_id, description)
              }
            >
              Generate Metadata
            </button>
          </div>
        )}
      </div>

      {/* Step 2: Processing */}
      {isGenerating && (
        <div className="card text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-indiapix-200 border-t-indiapix-600 mx-auto mb-4"></div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            Generating Metadata
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            Extracting frames and analyzing with{" "}
            {aiProvider === "openai" ? "GPT-4o (OpenAI)" : "Claude (Anthropic)"}...
            <br />
            This typically takes 10-30 seconds.
          </p>
          {/* Cancel button for long-running generation */}
          <button
            onClick={handleCancelGenerate}
            className="px-4 py-2 text-sm font-medium text-red-600 border border-red-300 rounded-lg hover:bg-red-50 transition-colors"
          >
            Cancel Generation
          </button>
        </div>
      )}

      {/* Step 3: Results */}
      {processState === "complete" && editableMetadata && generateResult && (
        <div className="space-y-6">
          {/* Title (was caption) */}
          <div className="card">
            <label className="section-label">
              Title{" "}
              <span className="font-normal text-gray-400">
                (max 200 characters)
              </span>
            </label>
            <div className="relative">
              <textarea
                className="input-field pr-16 resize-none"
                rows={2}
                value={editableMetadata.title}
                onChange={(e) => updateMetadata("title", e.target.value)}
                maxLength={200}
              />
              <span
                className={`absolute right-3 top-3 text-xs font-medium ${
                  editableMetadata.title.length > 190
                    ? "text-red-500"
                    : "text-gray-400"
                }`}
              >
                {editableMetadata.title.length}/200
              </span>
            </div>
          </div>

          {/* Description */}
          <div className="card">
            <label className="section-label">Description</label>
            <textarea
              className="input-field resize-none"
              rows={4}
              value={editableMetadata.description}
              onChange={(e) => updateMetadata("description", e.target.value)}
            />
          </div>

          {/* Category / Editorial / Location / Shot Type / Mood */}
          <div className="card">
            <h3 className="section-label">Classification</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Category
                </label>
                <input
                  type="text"
                  className="input-field text-sm"
                  value={editableMetadata.category}
                  onChange={(e) => updateMetadata("category", e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Location
                </label>
                <input
                  type="text"
                  className="input-field text-sm"
                  value={editableMetadata.location}
                  onChange={(e) => updateMetadata("location", e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Mood
                </label>
                <input
                  type="text"
                  className="input-field text-sm"
                  value={editableMetadata.mood}
                  onChange={(e) => updateMetadata("mood", e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Shot Type
                </label>
                <input
                  type="text"
                  className="input-field text-sm"
                  value={editableMetadata.shotType}
                  onChange={(e) => updateMetadata("shotType", e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Editorial
                </label>
                <select
                  className="input-field text-sm"
                  value={editableMetadata.editorial ? "Yes" : "No"}
                  onChange={(e) =>
                    updateMetadata("editorial", e.target.value === "Yes")
                  }
                >
                  <option value="No">No (Commercial)</option>
                  <option value="Yes">Yes (Editorial)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Keywords by Category */}
          <div className="card">
            <h3 className="section-label mb-4">
              Keywords by Category ({editableMetadata.keywords.length} total)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[
                { key: "people", label: "People & Demographics", min: 5 },
                { key: "action", label: "Action & Activity", min: 5 },
                { key: "location", label: "Location & Geography", min: 5 },
                { key: "setting", label: "Setting & Environment", min: 5 },
                { key: "technical", label: "Technical & Shot Type", min: 3 },
                { key: "conceptual", label: "Conceptual & Thematic", min: 8 },
              ].map((cat) => (
                <div key={cat.key} className="bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-gray-700">
                      {cat.label}
                    </span>
                    <span className="text-xs text-gray-400">
                      {
                        (
                          editableMetadata.keywordCategories as any
                        )[cat.key]?.length || 0
                      }{" "}
                      keywords
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {(
                      (editableMetadata.keywordCategories as any)[cat.key] ||
                      []
                    ).map((kw: string, idx: number) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1 bg-white border border-gray-200 rounded-full px-2.5 py-0.5 text-xs text-gray-700"
                      >
                        {kw}
                        <button
                          className="text-gray-400 hover:text-red-500 ml-0.5"
                          onClick={() => {
                            const updated = (
                              (editableMetadata.keywordCategories as any)[
                                cat.key
                              ] || []
                            ).filter((_: string, i: number) => i !== idx);
                            updateKeywordCategory(cat.key, updated);
                          }}
                        >
                          &times;
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3">
          <button
            className="btn-primary flex-1"
            onClick={() => {
              if (!editableMetadata || !generateResult) return;
              handleExportWithProps();
            }}
            disabled={isExporting}
            >
              {isExporting ? (
                <>
                  <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></span>
                  Exporting...
                </>
              ) : (
                <>
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  Export CSV
                </>
              )}
            </button>
            <button
              className="btn-secondary"
              onClick={handleRegenerate}
              disabled={isGenerating}
            >
              Regenerate
            </button>
            <button className="btn-secondary" onClick={handleReset}>
              Process Next File
            </button>
          </div>

          {/* Video Properties Info */}
          {generateResult.video_properties && (
            <div className="card">
              <h3 className="section-label mb-3">Video Properties</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {generateResult.video_properties.date_created && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <label className="block text-xs text-gray-500 mb-0.5">Date Created</label>
                    <span className="text-sm font-medium text-gray-900">{generateResult.video_properties.date_created}</span>
                  </div>
                )}
                {generateResult.video_properties.resolution && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <label className="block text-xs text-gray-500 mb-0.5">Resolution</label>
                    <span className="text-sm font-medium text-gray-900">{generateResult.video_properties.resolution}</span>
                  </div>
                )}
                {generateResult.video_properties.frame_rate && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <label className="block text-xs text-gray-500 mb-0.5">Frame Rate</label>
                    <span className="text-sm font-medium text-gray-900">{generateResult.video_properties.frame_rate}</span>
                  </div>
                )}
                {generateResult.video_properties.aspect_ratio && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <label className="block text-xs text-gray-500 mb-0.5">Aspect Ratio</label>
                    <span className="text-sm font-medium text-gray-900">{generateResult.video_properties.aspect_ratio}</span>
                  </div>
                )}
                {generateResult.video_properties.bitrate_kbps && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <label className="block text-xs text-gray-500 mb-0.5">Bitrate</label>
                    <span className="text-sm font-medium text-gray-900">{generateResult.video_properties.bitrate_kbps} kbps</span>
                  </div>
                )}
                {generateResult.video_properties.audio != null && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <label className="block text-xs text-gray-500 mb-0.5">Audio</label>
                    <span className="text-sm font-medium text-gray-900">{generateResult.video_properties.audio}</span>
                  </div>
                )}
                {generateResult.video_properties.duration_seconds != null && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <label className="block text-xs text-gray-500 mb-0.5">Duration</label>
                    <span className="text-sm font-medium text-gray-900">{formatDuration(generateResult.video_properties.duration_seconds)}</span>
                  </div>
                )}
              </div>
              <p className="text-xs text-gray-400 mt-3">
                {generateResult.frames_extracted} frames extracted from video
                {generateResult.duration_seconds
                  ? ` (${formatDuration(generateResult.duration_seconds)})`
                  : ""}
              </p>
            </div>
          )}
          
          {/* Frames info (fallback if no video_properties) */}
          {!generateResult.video_properties && generateResult.frames_extracted > 0 && (
            <p className="text-xs text-gray-400 text-center">
              {generateResult.frames_extracted} frames extracted from video
              {generateResult.duration_seconds
                ? ` (${Math.round(generateResult.duration_seconds)}s)`
                : ""}
            </p>
          )}
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <svg
              className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
                errorType === "timeout" || errorType === "cancelled"
                  ? "text-yellow-500"
                  : errorType === "network"
                    ? "text-orange-500"
                    : "text-red-500"
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d={
                  errorType === "timeout" || errorType === "cancelled"
                    ? "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    : "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                }
              />
            </svg>
            <div className="flex-1">
              <p className="text-sm font-medium text-red-800">
                {errorMessage}
              </p>
              {/* Show retry hint for retryable errors */}
              {(errorType === "timeout" || errorType === "network") && uploadResult && (
                <button
                  onClick={() =>
                    handleGenerate(uploadResult.upload_id, description)
                  }
                  className="mt-2 text-sm font-medium text-indiapix-600 hover:text-indiapix-800 underline"
                >
                  Try again
                </button>
              )}
            </div>
            <button
              className={`${
                errorType === "cancelled" ? "text-yellow-400 hover:text-yellow-600" : "text-red-400 hover:text-red-600"
              }`}
              onClick={() => setErrorMessage(null)}
            >
              &times;
            </button>
          </div>
        </div>
      )}
    </div>
  );
}