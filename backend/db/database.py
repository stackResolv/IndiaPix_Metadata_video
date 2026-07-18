"""
IndiaPix Metadata Automation System — Database Connection & Schema Management
SQLite operations. Connections are opened per-operation and closed automatically.
Uses 'check_same_thread=False' so the connection can be used across async contexts.
"""

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Database file path
DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "indiapix.db"


def get_db_path() -> Path:
    """Get the database file path, ensuring the directory exists."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def _create_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with recommended pragmas."""
    conn = sqlite3.connect(str(get_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema Definition ──────────────────────────────────────────────────────

SCHEMA_SQL = """
-- Job History: stores all completed/failed metadata jobs
CREATE TABLE IF NOT EXISTS job_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    filename        TEXT    NOT NULL,
    upload_id       TEXT    NOT NULL,
    batch_id        TEXT,
    metadata_json   TEXT,
    video_props_json TEXT,
    provider        TEXT    NOT NULL DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'completed',
    frames_extracted INTEGER DEFAULT 0,
    duration_seconds REAL,
    error_message   TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Full-text search virtual table for job_history
CREATE VIRTUAL TABLE IF NOT EXISTS job_history_fts USING fts5(
    filename,
    metadata_json,
    keyword_search,
    content='job_history',
    content_rowid='id'
);

-- Triggers to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS job_history_ai AFTER INSERT ON job_history BEGIN
    INSERT INTO job_history_fts(rowid, filename, metadata_json, keyword_search)
    VALUES (new.id, new.filename, new.metadata_json, 
            COALESCE(new.metadata_json, ''));
END;

CREATE TRIGGER IF NOT EXISTS job_history_ad AFTER DELETE ON job_history BEGIN
    INSERT INTO job_history_fts(job_history_fts, rowid, filename, metadata_json, keyword_search)
    VALUES ('delete', old.id, old.filename, old.metadata_json, 
            COALESCE(old.metadata_json, ''));
END;

CREATE TRIGGER IF NOT EXISTS job_history_au AFTER UPDATE ON job_history BEGIN
    INSERT INTO job_history_fts(job_history_fts, rowid, filename, metadata_json, keyword_search)
    VALUES ('delete', old.id, old.filename, old.metadata_json, 
            COALESCE(old.metadata_json, ''));
    INSERT INTO job_history_fts(rowid, filename, metadata_json, keyword_search)
    VALUES (new.id, new.filename, new.metadata_json, 
            COALESCE(new.metadata_json, ''));
END;

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_job_history_created_at ON job_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_history_status ON job_history(status);
CREATE INDEX IF NOT EXISTS idx_job_history_batch_id ON job_history(batch_id);
CREATE INDEX IF NOT EXISTS idx_job_history_filename ON job_history(filename);

-- Settings: key-value store for application settings
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Custom keywords: IndiaPix standard terms auto-appended to every job
CREATE TABLE IF NOT EXISTS custom_keywords (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword     TEXT NOT NULL UNIQUE,
    category    TEXT NOT NULL DEFAULT 'general',
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Migration tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT NOT NULL
);
"""


def _apply_schema(conn: sqlite3.Connection):
    """Execute the schema creation SQL."""
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def init_database():
    """
    Initialize the database: create tables, indexes, and apply migrations.
    Called once at application startup.
    """
    db_path = get_db_path()
    logger.info(f"Initializing database at: {db_path}")

    conn = _create_connection()
    try:
        _apply_schema(conn)
        logger.info("Database schema created/verified successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise
    finally:
        conn.close()


# ── Async Connection Helpers ───────────────────────────────────────────────

async def execute(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    """Execute a SQL query."""
    conn = _create_connection()
    try:
        cursor = await asyncio.to_thread(conn.execute, sql, params)
        return cursor
    finally:
        conn.close()


async def fetch_one(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    """Fetch a single row."""
    conn = _create_connection()
    try:
        cursor = await asyncio.to_thread(conn.execute, sql, params)
        return await asyncio.to_thread(cursor.fetchone)
    finally:
        conn.close()


async def fetch_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Fetch all rows."""
    conn = _create_connection()
    try:
        cursor = await asyncio.to_thread(conn.execute, sql, params)
        return await asyncio.to_thread(cursor.fetchall)
    finally:
        conn.close()


async def commit():
    """No-op: connections are auto-committed on close, or use execute with auto-commit."""
    pass
