"use client";

import { useState, useEffect } from "react";
import {
  getAllSettings,
  updateSettings,
  getApiKeyStatus,
  getCustomKeywords,
  addCustomKeyword,
  deleteCustomKeyword,
  listPlatforms,
} from "@/lib/api";
import type { CustomKeyword, PlatformPreset } from "@/types/metadata";

export default function SettingsPage() {
  // App settings
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  // API key status
  const [keyStatus, setKeyStatus] = useState<{
    claude: boolean;
    openai: boolean;
    claude_configured: boolean;
    openai_configured: boolean;
  } | null>(null);

  // Custom keywords
  const [keywords, setKeywords] = useState<CustomKeyword[]>([]);
  const [newKeyword, setNewKeyword] = useState("");
  const [newCategory, setNewCategory] = useState("general");
  const [addingKeyword, setAddingKeyword] = useState(false);
  const [keywordError, setKeywordError] = useState<string | null>(null);

  // Platforms
  const [platforms, setPlatforms] = useState<PlatformPreset[]>([]);

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getAllSettings(),
      getApiKeyStatus(),
      getCustomKeywords(),
      listPlatforms(),
    ])
      .then(([s, k, kw, p]) => {
        setSettings(s);
        setKeyStatus({
          claude: k.claude,
          openai: k.openai,
          claude_configured: k.claude_configured,
          openai_configured: k.openai_configured,
        });
        setKeywords(kw.keywords);
        setPlatforms(p.platforms);
      })
      .catch((err) => setError(err.message || "Failed to load settings"))
      .finally(() => setLoading(false));
  }, []);

  const handleSaveSettings = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateSettings(settings);
      setSettings(updated);
      setSuccess("Settings saved successfully.");
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleAddKeyword = async () => {
    const kw = newKeyword.trim();
    if (!kw) return;
    setAddingKeyword(true);
    setKeywordError(null);
    try {
      const result = await addCustomKeyword(kw, newCategory);
      setKeywords((prev) => [...prev, { ...result, is_active: true, created_at: "" }]);
      setNewKeyword("");
      setKeywordError(null);
    } catch (err: any) {
      setKeywordError(err.message || "Failed to add keyword");
    } finally {
      setAddingKeyword(false);
    }
  };

  const handleDeleteKeyword = async (id: number) => {
    try {
      await deleteCustomKeyword(id);
      setKeywords((prev) => prev.filter((k) => k.id !== id));
    } catch (err: any) {
      setKeywordError(err.message || "Failed to delete keyword");
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="text-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-indiapix-200 border-t-indiapix-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="text-center mb-4">
        <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
        <p className="mt-2 text-gray-600">
          Configure application preferences, API keys, and custom keywords
        </p>
      </div>

      {/* Success / Error messages */}
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700">
          {success}
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          {error}
          <button className="float-right text-red-400 hover:text-red-600" onClick={() => setError(null)}>
            &times;
          </button>
        </div>
      )}

      {/* ── API Key Status ─────────────────────────────────────────────── */}
      <div className="card">
        <h3 className="section-label mb-3">API Key Configuration</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className={`p-4 rounded-lg ${keyStatus?.claude ? "bg-green-50" : "bg-red-50"}`}>
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-2 h-2 rounded-full ${keyStatus?.claude ? "bg-green-500" : "bg-red-500"}`} />
              <span className="font-medium text-sm text-gray-900">Claude (Anthropic)</span>
            </div>
            <p className="text-xs text-gray-600">
              {keyStatus?.claude
                ? "API key is configured"
                : "API key is NOT configured"}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Set ANTHROPIC_API_KEY in .env file
            </p>
          </div>
          <div className={`p-4 rounded-lg ${keyStatus?.openai ? "bg-green-50" : "bg-red-50"}`}>
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-2 h-2 rounded-full ${keyStatus?.openai ? "bg-green-500" : "bg-red-500"}`} />
              <span className="font-medium text-sm text-gray-900">GPT-4o (OpenAI)</span>
            </div>
            <p className="text-xs text-gray-600">
              {keyStatus?.openai
                ? "API key is configured"
                : "API key is NOT configured"}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Set OPENAI_API_KEY in .env file
            </p>
          </div>
        </div>
      </div>

      {/* ── General Settings ───────────────────────────────────────────── */}
      <div className="card">
        <h3 className="section-label mb-4">General Preferences</h3>
        <div className="space-y-4">
          {/* Default Provider */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Default AI Provider
            </label>
            <select
              className="input-field max-w-xs"
              value={settings.default_provider || "claude"}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, default_provider: e.target.value }))
              }
            >
              <option value="claude">Claude (Anthropic)</option>
              <option value="openai">GPT-4o (OpenAI)</option>
            </select>
          </div>

          {/* Default Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Default Description (optional context for AI)
            </label>
            <textarea
              className="input-field"
              rows={2}
              placeholder="e.g., Indian cultural content shot in New Delhi"
              value={settings.default_description || ""}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, default_description: e.target.value }))
              }
            />
            <p className="text-xs text-gray-400 mt-1">
              This text will be pre-filled in the description field for every new job
            </p>
          </div>

          {/* Default Platform for Export */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Default Export Platform
            </label>
            <select
              className="input-field max-w-xs"
              value={settings.default_platform || "getty"}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, default_platform: e.target.value }))
              }
            >
              {platforms.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-400 mt-1">
              Platform preset used by default when exporting CSV
            </p>
          </div>

          {/* Frame count override */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Frame Count Override
            </label>
            <input
              type="number"
              className="input-field max-w-xs"
              min={0}
              max={20}
              placeholder="0 = auto"
              value={settings.frame_count_override || "0"}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, frame_count_override: e.target.value }))
              }
            />
            <p className="text-xs text-gray-400 mt-1">
              Set to 0 for automatic frame count based on video duration.
              Set to a fixed number (1-20) to override auto-detection.
            </p>
          </div>

          {/* Scene Detection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Scene Change Detection
            </label>
            <select
              className="input-field max-w-xs"
              value={settings.scene_detection_enabled || "true"}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, scene_detection_enabled: e.target.value }))
              }
            >
              <option value="true">Enabled (intelligent frame selection)</option>
              <option value="false">Disabled (fixed interval extraction)</option>
            </select>
          </div>

          {/* Max Batch Size */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Maximum Batch Size
            </label>
            <input
              type="number"
              className="input-field max-w-xs"
              min={1}
              max={500}
              value={settings.max_batch_size || "50"}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, max_batch_size: e.target.value }))
              }
            />
            <p className="text-xs text-gray-400 mt-1">
              Maximum number of files allowed in a single batch (default: 50)
            </p>
          </div>
        </div>

        <div className="mt-6">
          <button
            className="btn-primary"
            onClick={handleSaveSettings}
            disabled={saving}
          >
            {saving ? (
              <>
                <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                Saving...
              </>
            ) : (
              "Save Settings"
            )}
          </button>
        </div>
      </div>

      {/* ── Custom Keywords ────────────────────────────────────────────── */}
      <div className="card">
        <h3 className="section-label mb-2">Custom Keywords</h3>
        <p className="text-sm text-gray-500 mb-4">
          These IndiaPix standard terms are automatically appended to every job's keyword list
        </p>

        {/* Add keyword form */}
        <div className="flex flex-col sm:flex-row gap-2 mb-4">
          <input
            type="text"
            className="input-field flex-1"
            placeholder="Enter keyword..."
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddKeyword()}
          />
          <select
            className="input-field w-auto"
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
          >
            <option value="general">General</option>
            <option value="people">People</option>
            <option value="action">Action</option>
            <option value="location">Location</option>
            <option value="setting">Setting</option>
            <option value="technical">Technical</option>
            <option value="conceptual">Conceptual</option>
          </select>
          <button
            className="btn-primary whitespace-nowrap"
            onClick={handleAddKeyword}
            disabled={addingKeyword || !newKeyword.trim()}
          >
            {addingKeyword ? "Adding..." : "Add Keyword"}
          </button>
        </div>

        {keywordError && (
          <p className="text-sm text-red-600 mb-3">{keywordError}</p>
        )}

        {/* Keywords display */}
        {keywords.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">
            No custom keywords yet. Add your first keyword above.
          </p>
        ) : (
          <>
            {/* Grouped by category */}
            {["people", "location", "technical", "conceptual", "general", "action", "setting"].map(
              (cat) => {
                const catKeywords = keywords.filter(
                  (k) => k.category === cat && k.is_active
                );
                if (catKeywords.length === 0) return null;
                return (
                  <div key={cat} className="mb-3">
                    <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1.5">
                      {cat}
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {catKeywords.map((kw) => (
                        <span
                          key={kw.id}
                          className="inline-flex items-center gap-1 bg-white border border-gray-200 rounded-full px-2.5 py-0.5 text-xs text-gray-700"
                        >
                          {kw.keyword}
                          <button
                            className="text-gray-400 hover:text-red-500 ml-0.5"
                            onClick={() => handleDeleteKeyword(kw.id)}
                            title="Remove keyword"
                          >
                            &times;
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                );
              }
            )}
          </>
        )}
      </div>

      {/* ── Platform Info ──────────────────────────────────────────────── */}
      <div className="card">
        <h3 className="section-label mb-3">Platform Export Formats</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {platforms.map((p) => (
            <div key={p.id} className="bg-gray-50 rounded-lg p-3">
              <div className="font-medium text-sm text-gray-900">{p.name}</div>
              <div className="text-xs text-gray-500 mt-1">
                {p.columns.length} columns
              </div>
              <div className="text-[10px] text-gray-400 mt-0.5 truncate">
                {p.columns.join(", ")}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}