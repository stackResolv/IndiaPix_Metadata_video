"use client";

import Link from "next/link";

export default function HistoryPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900">
          Job History
        </h2>
        <p className="mt-2 text-gray-600">
          View and re-export previously processed files
        </p>
      </div>

      <div className="card text-center py-16">
        <svg
          className="mx-auto h-16 w-16 text-gray-300"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <h3 className="mt-4 text-lg font-semibold text-gray-700">
          Coming in Phase 3
        </h3>
        <p className="mt-2 text-sm text-gray-500 max-w-md mx-auto">
          Job history with SQLite database, search, re-export, and analytics
          will be available in Phase 3.
        </p>
        <Link
          href="/"
          className="mt-6 inline-block px-6 py-2.5 bg-indiapix-600 text-white font-medium rounded-lg hover:bg-indiapix-700 transition-colors"
        >
          Back to Single File Mode
        </Link>
      </div>
    </div>
  );
}