"""
IndiaPix Metadata Automation System — Custom Keywords Service
Manages IndiaPix standard terms that are auto-appended to every job's keyword list.
Stored in the SQLite database via the settings/custom_keywords tables.
"""

import json
import logging
from typing import Optional

from db.database import fetch_one, fetch_all, _create_connection
from models.metadata import MetadataResult, KeywordCategories

logger = logging.getLogger(__name__)

# Default IndiaPix standard keywords (pre-populated on first run)
DEFAULT_CUSTOM_KEYWORDS = [
    # People & Demographics
    {"keyword": "Indian", "category": "people"},
    {"keyword": "South Asian", "category": "people"},
    {"keyword": "Asian", "category": "people"},
    # Location & Geography
    {"keyword": "India", "category": "location"},
    {"keyword": "South Asia", "category": "location"},
    # Technical & Shot Type
    {"keyword": "Real Time Footage", "category": "technical"},
    {"keyword": "HD Format", "category": "technical"},
    {"keyword": "Film – Moving Image", "category": "technical"},
    {"keyword": "Non US Film Location", "category": "technical"},
    # Conceptual & Thematic
    {"keyword": "Culture", "category": "conceptual"},
    {"keyword": "Tradition", "category": "conceptual"},
    {"keyword": "Modern India", "category": "conceptual"},
]


async def init_default_keywords():
    """Pre-populate the custom_keywords table with defaults if empty."""
    row = await fetch_one("SELECT COUNT(*) as cnt FROM custom_keywords")
    if row and row["cnt"] == 0:
        logger.info("Initialising default custom keywords...")
        conn = _create_connection()
        try:
            for kw in DEFAULT_CUSTOM_KEYWORDS:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO custom_keywords (keyword, category) VALUES (?, ?)",
                        (kw["keyword"], kw["category"]),
                    )
                except Exception as e:
                    logger.warning(f"Failed to insert default keyword '{kw['keyword']}': {e}")
            conn.commit()
            logger.info(f"Inserted {len(DEFAULT_CUSTOM_KEYWORDS)} default custom keywords.")
        finally:
            conn.close()


async def get_all_keywords(active_only: bool = True) -> list[dict]:
    """Get all custom keywords, optionally only active ones."""
    if active_only:
        rows = await fetch_all(
            "SELECT * FROM custom_keywords WHERE is_active = 1 ORDER BY category, keyword"
        )
    else:
        rows = await fetch_all(
            "SELECT * FROM custom_keywords ORDER BY category, keyword"
        )
    return [
        {
            "id": row["id"],
            "keyword": row["keyword"],
            "category": row["category"],
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


async def add_keyword(keyword: str, category: str = "general") -> dict:
    """Add a new custom keyword."""
    conn = _create_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO custom_keywords (keyword, category) VALUES (?, ?)",
            (keyword.strip(), category.strip().lower()),
        )
        conn.commit()
        logger.info(f"Added custom keyword: '{keyword}' in category '{category}'")
        return {"id": cursor.lastrowid, "keyword": keyword.strip(), "category": category.strip().lower(), "is_active": True}
    except Exception as e:
        logger.warning(f"Failed to add keyword '{keyword}': {e}")
        raise ValueError(f"Failed to add keyword: {str(e)}")
    finally:
        conn.close()


async def update_keyword(keyword_id: int, keyword: Optional[str] = None, category: Optional[str] = None, is_active: Optional[bool] = None) -> bool:
    """Update an existing custom keyword."""
    updates = []
    params = []
    if keyword is not None:
        updates.append("keyword = ?")
        params.append(keyword.strip())
    if category is not None:
        updates.append("category = ?")
        params.append(category.strip().lower())
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if is_active else 0)

    if not updates:
        return False

    params.append(keyword_id)
    sql = f"UPDATE custom_keywords SET {', '.join(updates)} WHERE id = ?"
    
    conn = _create_connection()
    try:
        cursor = conn.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


async def delete_keyword(keyword_id: int) -> bool:
    """Delete a custom keyword."""
    conn = _create_connection()
    try:
        cursor = conn.execute("DELETE FROM custom_keywords WHERE id = ?", (keyword_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


async def get_merged_keywords(metadata: MetadataResult) -> list[str]:
    """
    Merge AI-generated keywords with active custom keywords.
    Custom keywords are appended to the end of the list (not deduplicated,
    as they are standard IndiaPix terms that should always appear).
    
    Args:
        metadata: The MetadataResult from AI generation
    
    Returns:
        Combined list of keywords (AI-generated + custom).
    """
    # Get all active custom keywords
    rows = await fetch_all("SELECT keyword FROM custom_keywords WHERE is_active = 1")
    custom_kws = [row["keyword"] for row in rows]

    # Start with AI-generated keywords
    merged = list(metadata.keywords) if metadata.keywords else []

    # Append any custom keywords not already present
    existing_set = {kw.strip().lower() for kw in merged}
    for kw in custom_kws:
        if kw.strip().lower() not in existing_set:
            merged.append(kw.strip())
            existing_set.add(kw.strip().lower())

    return merged


async def get_keywords_by_category() -> dict[str, list[dict]]:
    """Get custom keywords grouped by category."""
    rows = await fetch_all(
        "SELECT * FROM custom_keywords WHERE is_active = 1 ORDER BY category, keyword"
    )
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        cat = row["category"]
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append({
            "id": row["id"],
            "keyword": row["keyword"],
            "category": cat,
        })
    return grouped