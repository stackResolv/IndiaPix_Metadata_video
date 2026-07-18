"""
IndiaPix Metadata Automation System — Settings Service
Manages application settings stored in the SQLite database.
Provides API key management, default description, frame count override, etc.
"""

import json
import logging
from typing import Any, Optional

from db.database import fetch_one, fetch_all, _create_connection

logger = logging.getLogger(__name__)


# ── Default Settings ────────────────────────────────────────────────────────

DEFAULT_SETTINGS = {
    "default_provider": "claude",
    "default_description": "",
    "frame_count_override": "0",  # 0 = auto, otherwise fixed frame count
    "scene_detection_enabled": "true",
    "default_platform": "getty",
    "max_batch_size": "0",
}


async def init_default_settings():
    """Pre-populate the settings table with defaults if empty."""
    row = await fetch_one("SELECT COUNT(*) as cnt FROM settings")
    if row and row["cnt"] == 0:
        logger.info("Initialising default settings...")
        conn = _create_connection()
        try:
            for key, value in DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )
            conn.commit()
            logger.info(f"Inserted {len(DEFAULT_SETTINGS)} default settings.")
        finally:
            conn.close()


async def get_setting(key: str) -> Optional[str]:
    """Get a single setting value by key."""
    row = await fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row else None


async def set_setting(key: str, value: str) -> bool:
    """Set a single setting value. Creates or updates."""
    conn = _create_connection()
    try:
        conn.execute(
            """INSERT INTO settings (key, value, updated_at) 
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()
    logger.info(f"Setting updated: {key} = {value[:50]}{'...' if len(value) > 50 else ''}")
    return True


async def get_all_settings() -> dict[str, str]:
    """Get all settings as a flat dictionary."""
    rows = await fetch_all("SELECT key, value FROM settings")
    settings = {}
    for row in rows:
        settings[row["key"]] = row["value"]
    # Merge with defaults for any missing keys
    for key, default in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = default
    return settings


async def update_settings(updates: dict[str, str]) -> dict[str, str]:
    """Update multiple settings at once. Returns all settings after update."""
    for key, value in updates.items():
        await set_setting(key, value)
    return await get_all_settings()


async def delete_setting(key: str) -> bool:
    """Delete a setting by key."""
    conn = _create_connection()
    try:
        cursor = conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ── API Key Management ─────────────────────────────────────────────────────

async def get_api_key_status() -> dict[str, bool]:
    """
    Get the configuration status of API keys.
    Checks both the .env file and the database settings.
    
    Returns:
        Dict with provider -> boolean status.
    """
    from config import settings as app_settings
    
    # Check .env values
    claude_env = bool(app_settings.anthropic_api_key)
    openai_env = bool(app_settings.openai_api_key)
    
    # Check if DB has overrides
    db_claude = await get_setting("anthropic_api_key")
    db_openai = await get_setting("openai_api_key")
    
    return {
        "claude": bool(db_claude or claude_env),
        "openai": bool(db_openai or openai_env),
        "claude_configured": bool(claude_env),
        "openai_configured": bool(openai_env),
        "claude_db_override": bool(db_claude),
        "openai_db_override": bool(db_openai),
    }


async def get_effective_api_key(provider: str) -> Optional[str]:
    """
    Get the effective API key for a provider.
    Checks the database first (allows runtime override), then falls back to .env.
    """
    db_key = await get_setting(f"{provider}_api_key")
    if db_key:
        return db_key
    
    from config import settings as app_settings
    if provider == "claude":
        return app_settings.anthropic_api_key
    elif provider == "openai":
        return app_settings.openai_api_key
    return None