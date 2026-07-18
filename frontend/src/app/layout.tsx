import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "IndiaPix Metadata Automation System",
  description:
    "Generate professional stock metadata for video and image files using Claude AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gradient-to-br from-gray-50 to-indigo-50/30">
        {/* Navigation Header */}
        <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
          <nav className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
            {/* Logo / Brand */}
            <Link href="/" className="flex items-center gap-3 group">
              <div className="w-8 h-8 bg-indiapix-600 rounded-lg flex items-center justify-center group-hover:bg-indiapix-700 transition-colors">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <span className="font-semibold text-gray-900 text-sm hidden sm:block">
                IndiaPix Metadata
              </span>
            </Link>

            {/* Navigation Links */}
            <div className="flex items-center gap-1 sm:gap-2">
              <NavLink href="/" icon="single" label="Single File" />
              <NavLink href="/batch" icon="batch" label="Batch" />
              <NavLink href="/history" icon="history" label="History" />
              <NavLink href="/analytics" icon="analytics" label="Analytics" />
              <NavLink href="/settings" icon="settings" label="Settings" />
            </div>
          </nav>
        </header>

        {/* Main Content */}
        <main className="pb-12">{children}</main>
      </body>
    </html>
  );
}

/**
 * Navigation link component with active state detection and icons.
 */
function NavLink({
  href,
  icon,
  label,
}: {
  href: string;
  icon: "single" | "batch" | "history" | "analytics" | "settings";
  label: string;
}) {
  // Simple client component for active state isn't possible in server component,
  // so we use a simple anchor with a global class
  return (
    <Link
      href={href}
      className={`
        flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-xs font-medium
        transition-all duration-150
        text-gray-600 hover:text-indiapix-700 hover:bg-indiapix-50
        border border-transparent hover:border-indiapix-200
      `}
    >
      <Icon name={icon} />
      <span className="hidden sm:inline">{label}</span>
    </Link>
  );
}

/** Simple SVG icons for navigation */
function Icon({ name }: { name: string }) {
  switch (name) {
    case "single":
      return (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      );
    case "batch":
      return (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      );
    case "history":
      return (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    case "analytics":
      return (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      );
    case "settings":
      return (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      );
    default:
      return null;
  }
}