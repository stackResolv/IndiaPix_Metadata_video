"use client";

import { useState, useEffect, useCallback } from "react";
import {
  searchJobHistory,
  exportJobHistoryCsv,
  exportBatchHistoryCsv,
  deleteJobHistoryItem,
  listPlatforms,
} from "@/lib/api";
import type { JobHistoryRecord, PlatformPreset } from "@/types/metadata";

export default function HistoryPage() {
  const [records, setRecords] = useState<JobHistoryRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [offset, setOffset] = useState(0);
  const [limit] = useState(25);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [exporting, setExporting] = useState<number | null>(null);
  const [exportingBatch, setExportingBatch] = useState(false);
  const [platform, setPlatform] = useState("getty");
  const [platforms, setPlatforms] = useState<PlatformPreset[]>([]);

  const fetchRecords = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await searchJobHistory({
        query: query || undefined,
        status: statusFilter || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit,
        offset,
      });
      setRecords(result.results);
      setTotal(result.total);
    } catch (err: any) {
      setError(err.message || "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, [query, statusFilter, dateFrom, dateTo, limit, offset]);

  useEffect(() => {
    fetchRecords();
  }, [fetchRecords]);

  useEffect(() => {
    listPlatforms()
      .then((res) => setPlatforms(res.platforms))
      .catch(() => {});
  }, []);

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  const handleExport = async (jobId: number) => {
    setExporting(jobId);
    try {
      const blob = await exportJobHistoryCsv(jobId, platform);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `history_job_${jobId}_${platform}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message || "Export failed");
    } finally {
      setExporting(null);
    }
  };

  const handleBatchExport = async () => {
    if (selectedIds.size === 0) return;
    setExportingBatch(true);
    try {
      const blob = await exportBatchHistoryCsv(Array.from(selectedIds), platform);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `batch_export_${selectedIds.size}files_${platform}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message || "Batch export failed");
    } finally {
      setExportingBatch(false);
    }
  };

  const handleDelete = async (jobId: number) => {
    if (!confirm(`Delete job #${jobId}? This cannot be undone.`)) return;
    try {
      await deleteJobHistoryItem(jobId);
      fetchRecords();
    } catch (err: any) {
      setError(err.message || "Failed to delete");
    }
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === records.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(records.map((r) => r.id)));
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr + "Z");
      return d.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="text-center mb-4">
        <h2 className="text-2xl font-bold text-gray-900">Job History</h2>
        <p className="mt-2 text-gray-600">
          View, search, re-export, and manage past metadata jobs
        </p>
      </div>

      {/* Search & Filters */}
      <div className="card">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Search */}
          <div className="sm:col-span-2 lg:col-span-2">
            <label className="block text-xs text-gray-500 mb-1">Search</label>
            <input
              type="text"
              className="input-field"
              placeholder="Filename or keyword..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setOffset(0);
              }}
            />
          </div>

          {/* Status filter */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Status</label>
            <select
              className="input-field"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setOffset(0);
              }}
            >
              <option value="">All Statuses</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          {/* Date from */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">From</label>
            <input
              type="date"
              className="input-field"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setOffset(0);
              }}
            />
          </div>

          {/* Date to */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">To</label>
            <input
              type="date"
              className="input-field"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setOffset(0);
              }}
            />
          </div>
        </div>
      </div>

      {/* Export controls */}
      {records.length > 0 && (
        <div className="card flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">
              {selectedIds.size > 0
                ? `${selectedIds.size} selected`
                : `${total} total records`}
            </span>
          </div>
          <div className="flex-1" />
          <select
            className="input-field w-auto text-sm"
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
          >
            {platforms.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <button
            className="btn-primary text-sm py-2 px-4"
            onClick={handleBatchExport}
            disabled={selectedIds.size === 0 || exportingBatch}
          >
            {exportingBatch
              ? "Exporting..."
              : `Export Selected (${selectedIds.size})`}
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          {error}
          <button className="float-right text-red-400 hover:text-red-600" onClick={() => setError(null)}>
            &times;
          </button>
        </div>
      )}

      {/* Results table */}
      <div className="card overflow-x-auto">
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-4 border-indiapix-200 border-t-indiapix-600 mx-auto mb-3" />
            <p className="text-sm text-gray-500">Loading history...</p>
          </div>
        ) : records.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="mt-3 text-gray-500">No records found</p>
            <p className="text-sm text-gray-400">Try adjusting your search or filters</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="p-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectedIds.size === records.length && records.length > 0}
                    onChange={toggleSelectAll}
                    className="rounded border-gray-300"
                  />
                </th>
                <th className="p-3 text-left text-gray-500 font-medium">Filename</th>
                <th className="p-3 text-left text-gray-500 font-medium">Status</th>
                <th className="p-3 text-left text-gray-500 font-medium">Provider</th>
                <th className="p-3 text-left text-gray-500 font-medium hidden md:table-cell">Frames</th>
                <th className="p-3 text-left text-gray-500 font-medium hidden lg:table-cell">Date</th>
                <th className="p-3 text-right text-gray-500 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id} className="border-b border-gray-100 hover:bg-gray-50/50">
                  <td className="p-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(record.id)}
                      onChange={() => toggleSelect(record.id)}
                      disabled={record.status !== "completed"}
                      className="rounded border-gray-300"
                    />
                  </td>
                  <td className="p-3">
                    <span className="font-medium text-gray-900">{record.filename}</span>
                    {record.batch_id && (
                      <span className="ml-2 text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                        batch
                      </span>
                    )}
                  </td>
                  <td className="p-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        record.status === "completed"
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {record.status === "completed" ? "Completed" : "Failed"}
                    </span>
                  </td>
                  <td className="p-3 text-gray-600">
                    {record.provider || "-"}
                  </td>
                  <td className="p-3 text-gray-600 hidden md:table-cell">
                    {record.frames_extracted || 0}
                  </td>
                  <td className="p-3 text-gray-500 text-xs hidden lg:table-cell">
                    {formatDate(record.created_at)}
                  </td>
                  <td className="p-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {record.status === "completed" && (
                        <button
                          className="px-2.5 py-1 text-xs font-medium text-indiapix-600 hover:bg-indiapix-50 rounded-md transition-colors"
                          onClick={() => handleExport(record.id)}
                          disabled={exporting === record.id}
                        >
                          {exporting === record.id ? "..." : "Export"}
                        </button>
                      )}
                      <button
                        className="px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-50 rounded-md transition-colors"
                        onClick={() => handleDelete(record.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500">
            Page {currentPage} of {totalPages} ({total} records)
          </span>
          <div className="flex gap-2">
            <button
              className="btn-secondary text-sm py-1.5 px-3"
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={offset === 0}
            >
              Previous
            </button>
            <button
              className="btn-secondary text-sm py-1.5 px-3"
              onClick={() => setOffset(offset + limit)}
              disabled={offset + limit >= total}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}