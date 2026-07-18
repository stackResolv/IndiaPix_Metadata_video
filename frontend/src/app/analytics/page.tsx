"use client";

import { useState, useEffect } from "react";
import { getAnalyticsAll } from "@/lib/api";
import type { AnalyticsAllResponse } from "@/types/metadata";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsAllResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);
  const [categoryLimit] = useState(10);
  const [locationLimit] = useState(10);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getAnalyticsAll(days, categoryLimit, locationLimit)
      .then(setData)
      .catch((err) => setError(err.message || "Failed to load analytics"))
      .finally(() => setLoading(false));
  }, [days, categoryLimit, locationLimit]);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="text-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-indiapix-200 border-t-indiapix-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">{error}</div>
      </div>
    );
  }

  if (!data) return null;

  const { summary, daily, top_categories, top_locations } = data;
  const maxDailyCount = Math.max(...daily.map((d) => d.total), 1);

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="text-center mb-4">
        <h2 className="text-2xl font-bold text-gray-900">Analytics</h2>
        <p className="mt-2 text-gray-600">
          Processing statistics and insights
        </p>
      </div>

      {/* Period selector */}
      <div className="flex items-center gap-2 justify-center">
        {[
          { label: "Today", key: "today" },
          { label: "Last 7 Days", key: "week" },
          { label: "Last 30 Days", key: "month" },
          { label: "All Time", key: "all" },
        ].map((period) => (
          <button
            key={period.key}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              (period.key === "today" && days === 1) ||
              (period.key === "week" && days === 7) ||
              (period.key === "month" && days === 30) ||
              (period.key === "all" && days === 365)
                ? "bg-indiapix-600 text-white"
                : "bg-white text-gray-600 border border-gray-200 hover:border-gray-300"
            }`}
            onClick={() => setDays(period.key === "all" ? 365 : period.key === "month" ? 30 : period.key === "week" ? 7 : 1)}
          >
            {period.label}
          </button>
        ))}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <SummaryCard
          label="Total Files"
          value={summary.all.total}
          icon="files"
          color="indigo"
        />
        <SummaryCard
          label="Completed"
          value={summary.all.completed}
          icon="check"
          color="green"
        />
        <SummaryCard
          label="Failed"
          value={summary.all.failed}
          icon="x"
          color="red"
        />
        <SummaryCard
          label="Frames Extracted"
          value={summary.all.total_frames}
          icon="frames"
          color="amber"
        />
      </div>

      {/* Per-period breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: "Today", stats: summary.today },
          { label: "This Week", stats: summary.week },
          { label: "This Month", stats: summary.month },
        ].map((period) => (
          <div key={period.label} className="card">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">{period.label}</h4>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div>
                <div className="text-lg font-bold text-gray-900">{period.stats.total}</div>
                <div className="text-[10px] text-gray-400">Total</div>
              </div>
              <div>
                <div className="text-lg font-bold text-green-600">{period.stats.completed}</div>
                <div className="text-[10px] text-gray-400">Done</div>
              </div>
              <div>
                <div className="text-lg font-bold text-red-500">{period.stats.failed}</div>
                <div className="text-[10px] text-gray-400">Failed</div>
              </div>
            </div>
            {period.stats.total > 0 && (
              <div className="mt-2 bg-gray-200 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full"
                  style={{
                    width: `${Math.round(
                      (period.stats.completed / period.stats.total) * 100
                    )}%`,
                  }}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Daily Chart (bar chart) */}
      <div className="card">
        <h3 className="section-label mb-3">Processing Volume (Last {daily.length} Days)</h3>
        {daily.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">No data yet</p>
        ) : (
          <div className="space-y-1">
            {daily.map((day) => (
              <div key={day.date} className="flex items-center gap-2">
                <span className="text-[10px] text-gray-500 w-20 text-right flex-shrink-0">
                  {formatDateShort(day.date)}
                </span>
                <div className="flex-1 bg-gray-100 rounded-full h-5 relative overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0 bg-green-400 rounded-full"
                    style={{ width: `${(day.completed / maxDailyCount) * 100}%` }}
                  />
                  <div
                    className="absolute inset-y-0 left-0 bg-red-400 rounded-full"
                    style={{
                      width: `${((day.completed + day.failed) / maxDailyCount) * 100}%`,
                      opacity: 0.6,
                    }}
                  />
                </div>
                <span className="text-[10px] text-gray-600 w-12 text-right flex-shrink-0">
                  {day.total}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Top Categories & Locations */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="section-label mb-3">Top Categories</h3>
          {top_categories.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">No data yet</p>
          ) : (
            <div className="space-y-2">
              {top_categories.map((cat, i) => (
                <div key={cat.name} className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 w-5">{i + 1}.</span>
                  <span className="text-sm text-gray-700 flex-1 truncate">{cat.name}</span>
                  <div className="w-20 bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full bg-indiapix-500 rounded-full"
                      style={{
                        width: `${Math.round(
                          (cat.count / Math.max(...top_categories.map((c) => c.count), 1)) * 100
                        )}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-8 text-right">{cat.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="section-label mb-3">Top Locations</h3>
          {top_locations.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">No data yet</p>
          ) : (
            <div className="space-y-2">
              {top_locations.map((loc, i) => (
                <div key={loc.name} className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 w-5">{i + 1}.</span>
                  <span className="text-sm text-gray-700 flex-1 truncate">{loc.name}</span>
                  <div className="w-20 bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full bg-teal-500 rounded-full"
                      style={{
                        width: `${Math.round(
                          (loc.count / Math.max(...top_locations.map((l) => l.count), 1)) * 100
                        )}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-8 text-right">{loc.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** Summary card component */
function SummaryCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: number;
  icon: string;
  color: string;
}) {
  const colorMap: Record<string, { bg: string; text: string; iconBg: string }> = {
    indigo: { bg: "bg-indigo-50", text: "text-indigo-700", iconBg: "bg-indigo-100" },
    green: { bg: "bg-green-50", text: "text-green-700", iconBg: "bg-green-100" },
    red: { bg: "bg-red-50", text: "text-red-700", iconBg: "bg-red-100" },
    amber: { bg: "bg-amber-50", text: "text-amber-700", iconBg: "bg-amber-100" },
  };
  const colors = colorMap[color] || colorMap.indigo;

  return (
    <div className={`${colors.bg} rounded-xl p-4`}>
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 ${colors.iconBg} rounded-lg flex items-center justify-center`}>
          <Icon name={icon} className={`w-5 h-5 ${colors.text}`} />
        </div>
        <div>
          <div className={`text-2xl font-bold ${colors.text}`}>{value.toLocaleString()}</div>
          <div className="text-xs text-gray-500">{label}</div>
        </div>
      </div>
    </div>
  );
}

function Icon({ name, className }: { name: string; className?: string }) {
  switch (name) {
    case "files":
      return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      );
    case "check":
      return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      );
    case "x":
      return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      );
    case "frames":
      return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      );
    default:
      return null;
  }
}

function formatDateShort(dateStr: string): string {
  try {
    const d = new Date(dateStr + "T00:00:00Z");
    return d.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
  } catch {
    return dateStr;
  }
}