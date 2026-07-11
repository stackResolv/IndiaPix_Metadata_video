import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IndiaPix Metadata Automation System",
  description:
    "Generate professional stock metadata for video and image files using Claude AI.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <header className="bg-white border-b border-gray-200 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center gap-3">
                <a href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
                  <div className="w-10 h-10 bg-indiapix-600 rounded-lg flex items-center justify-center">
                    <svg
                      className="w-6 h-6 text-white"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                  <div>
                    <h1 className="text-lg font-bold text-gray-900">
                      IndiaPix
                    </h1>
                    <p className="text-xs text-gray-500">
                      Metadata Automation System
                    </p>
                  </div>
                </a>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href="/"
                  className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-indiapix-600 hover:bg-indiapix-50 rounded-lg transition-colors"
                >
                  Single File
                </a>
                <a
                  href="/batch"
                  className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-indiapix-600 hover:bg-indiapix-50 rounded-lg transition-colors"
                >
                  Batch
                </a>
                <a
                  href="/history"
                  className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-indiapix-600 hover:bg-indiapix-50 rounded-lg transition-colors"
                >
                  History
                </a>
                <span className="text-xs text-gray-400 hidden sm:inline ml-2">
                  Powered by AI
                </span>
              </div>
            </div>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="bg-white border-t border-gray-200 py-4">
          <div className="max-w-7xl mx-auto px-4 text-center text-xs text-gray-400">
            IndiaPix Visual Media Pvt. Ltd. &copy; {new Date().getFullYear()} &mdash; Confidential
          </div>
        </footer>
      </body>
    </html>
  );
}