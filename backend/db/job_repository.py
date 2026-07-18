"""
IndiaPix Metadata Automation System — Job Repository
CRUD operations for the job_history table.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from db.database import fetch_one, fetch_all, execute, commit, _create_connection
from models.metadata import MetadataResult

logger = logging.getLogger(__name__)


# ── Data Transfer Objects ──────────────────────────────────────────────────

class JobHistoryRecord:
    """Represents a row from the job_history table."""
    def __init__(self, row: dict):
        self.id: int = row["id"]
        self.filename: str = row["filename"]
        self.upload_id: str = row["upload_id"]
        self.batch_id: Optional[str] = row.get("batch_id")
        self.metadata_json: Optional[str] = row.get("metadata_json")
        self.video_props_json: Optional[str] = row.get("video_props_json")
        self.provider: str = row.get("provider", "")
        self.status: str = row.get("status", "completed")
        self.frames_extracted: int = row.get("frames_extracted", 0)
        self.duration_seconds: Optional[float] = row.get("duration_seconds")
        self.error_message: Optional[str] = row.get("error_message")
        self.created_at: str = row.get("created_at", "")

    def to_dict(self) -> dict:
        """Serialize to API response format."""
        result = {
            "id": self.id,
            "filename": self.filename,
            "upload_id": self.upload_id,
            "batch_id": self.batch_id,
            "status": self.status,
            "frames_extracted": self.frames_extracted,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "provider": self.provider,
        }
        # Parse metadata JSON
        if self.metadata_json:
            try:
                result["metadata"] = json.loads(self.metadata_json)
            except json.JSONDecodeError:
                result["metadata"] = None
        else:
            result["metadata"] = None
        # Parse video properties JSON
        if self.video_props_json:
            try:
                result["video_properties"] = json.loads(self.video_props_json)
            except json.JSONDecodeError:
                result["video_properties"] = None
        else:
            result["video_properties"] = None
        return result

    def get_metadata(self) -> Optional[MetadataResult]:
        """Deserialize metadata to MetadataResult model."""
        if not self.metadata_json:
            return None
        try:
            data = json.loads(self.metadata_json)
            return MetadataResult(**data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to deserialize metadata for job {self.id}: {e}")
            return None

    def get_video_properties(self) -> Optional[dict]:
        """Deserialize video properties."""
        if not self.video_props_json:
            return None
        try:
            return json.loads(self.video_props_json)
        except json.JSONDecodeError:
            return None


# ── CRUD Operations ────────────────────────────────────────────────────────

async def save_job(
    filename: str,
    upload_id: str,
    status: str,
    batch_id: Optional[str] = None,
    metadata: Optional[MetadataResult] = None,
    video_properties: Optional[dict] = None,
    provider: str = "",
    frames_extracted: int = 0,
    duration_seconds: Optional[float] = None,
    error_message: Optional[str] = None,
) -> int:
    """
    Save a job record to the database.
    
    Args:
        filename: Original file name
        upload_id: Upload UUID
        status: "completed" or "failed"
        batch_id: Optional batch UUID
        metadata: The MetadataResult object
        video_properties: Optional dict of video tech properties
        provider: AI provider used ("claude" or "openai")
        frames_extracted: Number of frames extracted
        duration_seconds: Video duration in seconds
        error_message: Error message if failed
    
    Returns:
        The auto-generated job history ID.
    """
    metadata_json = json.dumps(metadata.model_dump()) if metadata else None
    video_props_json = json.dumps(video_properties) if video_properties else None

    conn = _create_connection()
    try:
        cursor = await asyncio.to_thread(conn.execute,
            """INSERT INTO job_history 
               (filename, upload_id, batch_id, metadata_json, video_props_json,
                provider, status, frames_extracted, duration_seconds, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                filename,
                upload_id,
                batch_id,
                metadata_json,
                video_props_json,
                provider,
                status,
                frames_extracted,
                duration_seconds,
                error_message,
            ),
        )
        await asyncio.to_thread(conn.commit)
        job_id = cursor.lastrowid
    finally:
        conn.close()
    logger.info(f"Saved job #{job_id}: {filename} ({status})")
    return job_id


async def get_job(job_id: int) -> Optional[JobHistoryRecord]:
    """Get a single job by ID."""
    row = await fetch_one("SELECT * FROM job_history WHERE id = ?", (job_id,))
    if not row:
        return None
    return JobHistoryRecord(dict(row))


async def search_jobs(
    query: str = "",
    status_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    batch_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[JobHistoryRecord], int]:
    """
    Search job history with filters and full-text search.
    
    Args:
        query: Full-text search query (searches filename and metadata)
        status_filter: Filter by status ("completed" or "failed")
        date_from: ISO date string for start of range
        date_to: ISO date string for end of range
        batch_id: Filter by batch ID
        limit: Max results per page
        offset: Pagination offset
    
    Returns:
        Tuple of (list of JobHistoryRecord, total_count)
    """
    conditions = []
    params = []

    # Full-text search
    if query:
        conditions.append("""
            jh.id IN (
                SELECT rowid FROM job_history_fts 
                WHERE job_history_fts MATCH ?
            )
        """)
        # Escape special FTS5 characters and add prefix matching
        safe_query = query.replace('"', '""').replace("'", "''")
        # Use prefix matching for partial word search
        params.append(f'"{safe_query}"')
    else:
        # When no query, keyword_search-based fallback uses filename LIKE
        pass

    # Status filter
    if status_filter:
        conditions.append("jh.status = ?")
        params.append(status_filter)

    # Date range filter
    if date_from:
        conditions.append("jh.created_at >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("jh.created_at <= ?")
        params.append(date_to + " 23:59:59")

    # Batch ID filter
    if batch_id:
        conditions.append("jh.batch_id = ?")
        params.append(batch_id)

    # Non-FTS filename search (for when query is provided but needs broader match)
    if query and not conditions:
        conditions.append("jh.filename LIKE ?")
        params.append(f"%{query}%")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Get total count
    count_sql = f"SELECT COUNT(*) FROM job_history jh WHERE {where_clause}"
    count_row = await fetch_one(count_sql, tuple(params))
    total_count = count_row[0] if count_row else 0

    # Get paginated results
    query_sql = f"""
        SELECT jh.* FROM job_history jh 
        WHERE {where_clause}
        ORDER BY jh.created_at DESC
        LIMIT ? OFFSET ?
    """
    rows = await fetch_all(query_sql, tuple(params) + (limit, offset))
    
    records = [JobHistoryRecord(dict(row)) for row in rows]
    return records, total_count


async def delete_job(job_id: int) -> bool:
    """Delete a job record by ID. Returns True if deleted."""
    conn = _create_connection()
    try:
        cursor = await asyncio.to_thread(conn.execute, "DELETE FROM job_history WHERE id = ?", (job_id,))
        await asyncio.to_thread(conn.commit)
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Deleted job #{job_id}")
        return deleted
    finally:
        conn.close()


async def get_job_stats(
    period: str = "all",
) -> dict:
    """
    Get aggregate statistics for the dashboard.
    
    Args:
        period: "today", "week", "month", or "all"
    
    Returns:
        Dictionary with statistics.
    """
    date_filter = ""
    if period == "today":
        date_filter = "WHERE created_at >= datetime('now', 'start of day')"
    elif period == "week":
        date_filter = "WHERE created_at >= datetime('now', '-7 days')"
    elif period == "month":
        date_filter = "WHERE created_at >= datetime('now', '-30 days')"

    results = {}

    # Total count
    row = await fetch_one(f"SELECT COUNT(*) FROM job_history {date_filter}")
    results["total"] = row[0] if row else 0

    # Completed count
    row = await fetch_one(
        f"SELECT COUNT(*) FROM job_history {date_filter} " 
        f"{'AND' if date_filter else 'WHERE'} status = 'completed'"
    )
    results["completed"] = row[0] if row else 0

    # Failed count
    row = await fetch_one(
        f"SELECT COUNT(*) FROM job_history {date_filter} " 
        f"{'AND' if date_filter else 'WHERE'} status = 'failed'"
    )
    results["failed"] = row[0] if row else 0

    # Total frames extracted
    row = await fetch_one(
        f"SELECT COALESCE(SUM(frames_extracted), 0) FROM job_history {date_filter} "
        f"{'AND' if date_filter else 'WHERE'} status = 'completed'"
    )
    results["total_frames"] = row[0] if row else 0

    return results


async def get_daily_stats(
    days: int = 30,
) -> list[dict]:
    """
    Get per-day processing counts for the analytics chart.
    
    Args:
        days: Number of days to look back
    
    Returns:
        List of {date, total, completed, failed} dicts.
    """
    rows = await fetch_all("""
        SELECT 
            date(created_at) as day,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM job_history 
        WHERE created_at >= datetime('now', ? || ' days')
        GROUP BY date(created_at)
        ORDER BY day ASC
    """, (f"-{days}",))

    return [
        {
            "date": row["day"],
            "total": row["total"],
            "completed": row["completed"],
            "failed": row["failed"],
        }
        for row in rows
    ]


async def get_top_categories(limit: int = 10) -> list[dict]:
    """Get the most common categories from completed jobs."""
    rows = await fetch_all("""
        SELECT 
            json_extract(metadata_json, '$.category') as category,
            COUNT(*) as count
        FROM job_history 
        WHERE status = 'completed' 
          AND metadata_json IS NOT NULL
          AND json_extract(metadata_json, '$.category') IS NOT NULL
          AND json_extract(metadata_json, '$.category') != ''
        GROUP BY category
        ORDER BY count DESC
        LIMIT ?
    """, (limit,))

    return [{"name": row["category"], "count": row["count"]} for row in rows]


async def get_top_locations(limit: int = 10) -> list[dict]:
    """Get the most common locations from completed jobs."""
    rows = await fetch_all("""
        SELECT 
            json_extract(metadata_json, '$.location') as location,
            COUNT(*) as count
        FROM job_history 
        WHERE status = 'completed' 
          AND metadata_json IS NOT NULL
          AND json_extract(metadata_json, '$.location') IS NOT NULL
          AND json_extract(metadata_json, '$.location') != 'Unknown'
        GROUP BY location
        ORDER BY count DESC
        LIMIT ?
    """, (limit,))

    return [{"name": row["location"], "count": row["count"]} for row in rows]