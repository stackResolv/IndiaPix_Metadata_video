"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  uploadFile,
  batchStart,
  batchStatus,
  batchExportCsv,
  batchRetryFailed,
  ApiError,
  UploadResponse,
  BatchStatusResponse,
  BatchJobStatus,
} from "@/lib/api";

// ── Helpers ───────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getStatusBadgeClass(status: string): string {
  switch (status) {
    case "done":
      return "bg-green-100 text-green-700 border-green-200";
    case "processing":
      return "bg-blue-100 text-blue-700 border-blue-200 animate-pulse";
    case "uploading":
      return "bg-blue-100 text-blue-700 border-blue-200 animate-pulse";
    case "failed":
      return "bg-red-100 text-red-700 border-red-200";
    case "pending":
    default:
      return "bg-gray-100 text-gray-500 border-gray-200";
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case "done":
      return "Done";
    case "processing":
      return "Processing...";
    case "uploading":
      return "Uploading...";
    case "failed":
      return "Failed";
    case "pending":
    default:
      return "Pending";
  }
}

type QueueStatus = "pending" | "uploading" | "uploaded" | "processing" | "done" | "failed";

interface QueueItem {
  file: File;
  uploadResult?: UploadResponse;
  uploadError?: string;
  status: QueueStatus;
}

// ── Component ─────────────────────────────────────────────────────────────

export default function BatchPage() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [aiProvider, setAiProvider] = useState<string>("claude");
  const [batchId, setBatchId] = useState<string | null>(null);
  const [batchData, setBatchData] = useState<BatchStatusResponse | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  // Update local queue status from batch data (polling callback)
  const updateQueueFromBatch = useCallback((status: BatchStatusResponse) => {
    setBatchData(status);
    setQueue((prev) =>
      prev.map((item) => {
        if (!item.uploadResult) return item;
        const job = status.jobs.find(
          (j: BatchJobStatus) => j.upload_id === item.uploadResult!.upload_id
        );
        if (!job) return item;

        let newStatus: QueueStatus = item.status;
        if (job.status === "completed") newStatus = "done";
        else if (job.status === "processing") newStatus = "processing";
        else if (job.status === "failed") newStatus = "failed";

        return { ...item, status: newStatus };
      })
    );
  }, []);

  // Start polling for batch status
  const startPolling = useCallback((bId: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);

    pollingRef.current = setInterval(async () => {
      try {
        const status = await batchStatus(bId);
        updateQueueFromBatch(status);

        if (status.is_complete) {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          setIsProcessing(false);
        }
      } catch {
        // Silent fail — will retry on next poll
      }
    }, 1500); // Poll every 1.5 seconds
  }, [updateQueueFromBatch]);

  // ── File Selection ────────────────────────────────────────────────────

  const handleFilesSelected = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return;

    const validExtensions = [
      ".mp4", ".mov", ".avi", ".mxf", ".m4v", ".wmv",
      ".jpg", ".jpeg", ".png", ".tiff", ".tif",
      ".cr2", ".nef", ".arw",
    ];

    const newItems: QueueItem[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (validExtensions.includes(ext)) {
        newItems.push({ file, status: "pending" });
      }
    }

    if (newItems.length === 0) {
      setErrorMessage(`No valid files selected. Supported: ${validExtensions.join(", ")}`);
      return;
    }

    setQueue((prev) => [...prev, ...newItems]);
    setErrorMessage(null);
    setBatchId(null);
    setBatchData(null);

    // Reset input values so the same folder can be selected again
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (folderInputRef.current) folderInputRef.current.value = "";
  }, []);

  const removeFromQueue = useCallback((index: number) => {
    setQueue((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearQueue = useCallback(() => {
    setQueue([]);
    setBatchId(null);
    setBatchData(null);
    setErrorMessage(null);
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  // ── Process Batch ─────────────────────────────────────────────────────

  const handleProcessBatch = async () => {
    if (queue.length === 0) return;

    setIsProcessing(true);
    setErrorMessage(null);

    // Upload files one by one with real-time status updates
    const uploadIds: string[] = [];

    for (let i = 0; i < queue.length; i++) {
      const item = queue[i];

      // Set to uploading
      setQueue((prev) =>
        prev.map((q, idx) => (idx === i ? { ...q, status: "uploading" as QueueStatus } : q))
      );

      try {
        const result = await uploadFile(item.file);
        uploadIds.push(result.upload_id);

        // Set to uploaded
        setQueue((prev) =>
          prev.map((q, idx) =>
            idx === i ? { ...q, status: "uploaded" as QueueStatus, uploadResult: result } : q
          )
        );
      } catch (err: any) {
        // Set to failed
        setQueue((prev) =>
          prev.map((q, idx) =>
            idx === i
              ? { ...q, status: "failed" as QueueStatus, uploadError: err.message || "Upload failed" }
              : q
          )
        );
      }
    }

    if (uploadIds.length === 0) {
      setErrorMessage("All files failed to upload. Check file types and try again.");
      setIsProcessing(false);
      return;
    }

    // Start backend batch processing
    try {
      const result = await batchStart({
        upload_ids: uploadIds,
        provider: aiProvider,
      });
      setBatchId(result.batch_id);
      setBatchData(result);

      // Set all uploaded items to processing status
      setQueue((prev) =>
        prev.map((q) =>
          q.status === "uploaded" ? { ...q, status: "processing" as QueueStatus } : q
        )
      );

      // Poll for progress (callback updates per-item status in real-time)
      startPolling(result.batch_id);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to start batch processing");
      setIsProcessing(false);
    }
  };

  // ── Retry Failed ──────────────────────────────────────────────────────

  const handleRetryFailed = async () => {
    if (!batchId) return;
    setIsProcessing(true);

    // Reset failed items back to pending so they retry
    setQueue((prev) => prev.map((q) => (q.status === "failed" ? { ...q, status: "pending" } : q)));

    try {
      const result = await batchRetryFailed(batchId);
      setBatchData(result);
      startPolling(batchId);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to retry");
      setIsProcessing(false);
    }
  };

  // ── Export Batch CSV ─────────────────────────────────────────────────

  const handleExportCsv = async () => {
    if (!batchId) return;
    setIsExporting(true);
    try {
      const blob = await batchExportCsv(batchId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `batch_${batchId.slice(0, 8)}_metadata.csv`;
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

  // ── Progress Calculation ─────────────────────────────────────────────

  const totalJobs = queue.length;
  const completedJobs = queue.filter((q) => q.status === "done" || q.status === "failed").length;
  const progressPercent = totalJobs > 0 ? Math.round((completedJobs / totalJobs) * 100) : 0;
  const hasFailed = queue.some((q) => q.status === "failed");
  const hasCompleted = queue.some((q) => q.status === "done");

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="text-center mb-4">
        <h2 className="text-2xl font-bold text-gray-900">
          Batch Processing
        </h2>
        <p className="mt-2 text-gray-600">
          Upload multiple video and image files to process them in one go
        </p>
      </div>

      {/* AI Provider Selector */}
      <div className="card">
        <label className="section-label">AI Model</label>
        <div className="flex gap-2 max-w-xs">
          <button
            type="button"
            className={`flex-1 px-4 py-2 rounded-lg border-2 font-medium text-sm transition-all ${
              aiProvider === "claude"
                ? "border-indiapix-500 bg-indiapix-50 text-indiapix-700"
                : "border-gray-200 bg-white text-gray-500 hover:border-gray-300"
            }`}
            onClick={() => setAiProvider("claude")}
            disabled={isProcessing}
          >
            Claude
          </button>
          <button
            type="button"
            className={`flex-1 px-4 py-2 rounded-lg border-2 font-medium text-sm transition-all ${
              aiProvider === "openai"
                ? "border-green-500 bg-green-50 text-green-700"
                : "border-gray-200 bg-white text-gray-500 hover:border-gray-300"
            }`}
            onClick={() => setAiProvider("openai")}
            disabled={isProcessing}
          >
            GPT-4o
          </button>
        </div>
      </div>

      {/* Upload Zone */}
      {!isProcessing && (
        <div>
          <div
            className="border-2 border-dashed border-gray-300 rounded-xl p-10 text-center cursor-pointer hover:border-indiapix-400 hover:bg-indiapix-50/30 transition-colors"
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              handleFilesSelected(e.dataTransfer.files);
            }}
          >
            <svg
              className="mx-auto h-10 w-10 text-gray-400"
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
            <p className="mt-3 text-gray-600 font-medium">
              Drag & drop files or a folder here
            </p>
            <p className="mt-1 text-sm text-gray-400">
              Videos: MP4, MOV, AVI, MXF, M4V, WMV &nbsp;|&nbsp; Images: JPG, PNG, TIFF, RAW (CR2, NEF, ARW)
            </p>

            <div className="mt-5 flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="px-5 py-2.5 bg-indiapix-600 text-white font-medium rounded-lg hover:bg-indiapix-700 transition-colors"
              >
                Select Files
              </button>
              <button
                type="button"
                onClick={() => folderInputRef.current?.click()}
                className="px-5 py-2.5 bg-white text-gray-700 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
              >
                Select Folder
              </button>
            </div>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            multiple
            accept=".mp4,.mov,.avi,.mxf,.m4v,.wmv,.jpg,.jpeg,.png,.tiff,.tif,.cr2,.nef,.arw"
            onChange={(e) => handleFilesSelected(e.target.files)}
          />

          <input
            ref={folderInputRef}
            type="file"
            className="hidden"
            multiple
            // @ts-ignore — webkitdirectory (Chrome/Safari/Edge)
            webkitdirectory=""
            directory=""
            onChange={(e) => handleFilesSelected(e.target.files)}
          />
        </div>
      )}

      {/* Queue Display */}
      {queue.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Upload Queue ({queue.length} file{queue.length !== 1 ? "s" : ""})
            </h3>
            {!isProcessing && (
              <button onClick={clearQueue} className="btn-secondary text-sm py-1.5 px-3">
                Clear All
              </button>
            )}
          </div>

          {/* File List with real-time per-item status */}
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {queue.map((item, idx) => (
              <div
                key={idx}
                className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                  item.status === "processing" || item.status === "uploading"
                    ? "bg-blue-50 border border-blue-200"
                    : item.status === "done"
                      ? "bg-green-50"
                      : item.status === "failed"
                        ? "bg-red-50"
                        : "bg-gray-50"
                }`}
              >
                {/* File icon by type */}
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    item.file.type.startsWith("video") ? "bg-purple-100" : "bg-amber-100"
                  }`}
                >
                  <svg
                    className={`w-4 h-4 ${
                      item.file.type.startsWith("video") ? "text-purple-600" : "text-amber-600"
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    {item.file.type.startsWith("video") ? (
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    ) : (
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    )}
                  </svg>
                </div>

                {/* File name and size */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {item.file.name}
                  </p>
                  <p className="text-xs text-gray-400">
                    {formatFileSize(item.file.size)}
                    {item.file.type.startsWith("video") ? " | Video" : " | Image"}
                  </p>
                </div>

                {/* Status badge — real-time per-item */}
                <span
                  className={`text-xs font-medium px-2.5 py-1 rounded-full border whitespace-nowrap ${getStatusBadgeClass(item.status)}`}
                >
                  {item.status === "processing" && item.uploadResult
                    ? metadataStatusLabel(batchData, item.uploadResult.upload_id)
                    : getStatusLabel(item.status)}
                </span>

                {/* Error tooltip for failed items */}
                {item.status === "failed" && item.uploadError && (
                  <span className="text-xs text-red-500 max-w-[140px] truncate" title={item.uploadError}>
                    {item.uploadError}
                  </span>
                )}

                {/* Remove button (only when not processing) */}
                {!isProcessing && (
                  <button
                    onClick={() => removeFromQueue(idx)}
                    className="text-gray-400 hover:text-red-500 p-1 flex-shrink-0"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Progress Bar — shows real-time progress from queue state */}
      {(isProcessing || hasCompleted) && (
        <div className="card">
          <h3 className="section-label mb-3">Progress</h3>
          <div className="flex items-center gap-4 mb-2">
            <div className="flex-1 bg-gray-200 rounded-full h-4 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ease-out ${
                  hasFailed ? "bg-amber-500" : "bg-indiapix-600"
                }`}
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className="text-sm font-semibold text-gray-700 whitespace-nowrap min-w-[3rem] text-right">
              {progressPercent}%
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">
              Uploading:{" "}
              <span className="font-medium text-gray-700">
                {queue.filter((q) => q.status === "uploading").length}
              </span>
            </span>
            <span className="text-gray-500">
              Processing:{" "}
              <span className="font-medium text-blue-600">
                {queue.filter((q) => q.status === "processing").length}
              </span>
            </span>
            <span className="text-gray-500">
              Done:{" "}
              <span className="font-medium text-green-600">
                {queue.filter((q) => q.status === "done").length}
              </span>
            </span>
            <span className="text-gray-500">
              Failed:{" "}
              <span className={`font-medium ${hasFailed ? "text-red-600" : "text-gray-700"}`}>
                {queue.filter((q) => q.status === "failed").length}
              </span>
            </span>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3">
        {!isProcessing && !batchData && queue.length > 0 && (
          <button className="btn-primary flex-1" onClick={handleProcessBatch}>
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Start Processing ({queue.length} file{queue.length !== 1 ? "s" : ""})
          </button>
        )}

        {/* Show export + retry when batch is complete */}
        {!isProcessing && hasCompleted && (
          <>
            <button
              className="btn-primary flex-1"
              onClick={handleExportCsv}
              disabled={isExporting}
            >
              {isExporting ? (
                <>
                  <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                  Exporting...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Export All as CSV ({queue.filter((q) => q.status === "done").length} file
                  {queue.filter((q) => q.status === "done").length !== 1 ? "s" : ""})
                </>
              )}
            </button>
            {hasFailed && (
              <button className="btn-secondary" onClick={handleRetryFailed} disabled={isProcessing}>
                Retry Failed ({queue.filter((q) => q.status === "failed").length})
              </button>
            )}
          </>
        )}
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 mt-0.5 flex-shrink-0 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <p className="text-sm font-medium text-red-800">{errorMessage}</p>
            </div>
            <button className="text-red-400 hover:text-red-600" onClick={() => setErrorMessage(null)}>
              &times;
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Show more descriptive label for processing items by looking up the backend status.
 */
function metadataStatusLabel(
  batchData: BatchStatusResponse | null,
  uploadId: string
): string {
  if (!batchData) return "Processing...";
  const job = batchData.jobs.find((j: BatchJobStatus) => j.upload_id === uploadId);
  if (!job) return "Processing...";
  if (job.status === "processing") return "Processing...";
  if (job.status === "completed") return "Done";
  if (job.status === "failed") return "Failed";
  return "Processing...";
}