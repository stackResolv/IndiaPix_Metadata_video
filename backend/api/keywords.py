"""
IndiaPix Metadata Automation System — Custom Keywords API Endpoints
Manage the IndiaPix standard keyword list that is auto-appended to every job.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from services.custom_keywords import (
    get_all_keywords,
    add_keyword,
    update_keyword,
    delete_keyword,
    get_keywords_by_category,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/keywords", tags=["keywords"])


@router.get("/")
async def keywords_list(
    active_only: bool = Query(True, description="Only return active keywords"),
):
    """Get all custom keywords, optionally only active ones."""
    keywords = await get_all_keywords(active_only=active_only)
    return {"keywords": keywords, "total": len(keywords)}


@router.get("/categories")
async def keywords_by_category():
    """Get custom keywords grouped by category."""
    grouped = await get_keywords_by_category()
    return {"categories": grouped}


@router.post("/")
async def keywords_add(request: Request):
    """Add a new custom keyword."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    keyword = body.get("keyword", "").strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="'keyword' is required")

    category = body.get("category", "general").strip().lower()

    try:
        result = await add_keyword(keyword, category)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{keyword_id}")
async def keywords_update(keyword_id: int, request: Request):
    """Update an existing custom keyword."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    updated = await update_keyword(
        keyword_id,
        keyword=body.get("keyword"),
        category=body.get("category"),
        is_active=body.get("is_active"),
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Keyword #{keyword_id} not found")
    return {"updated": True, "keyword_id": keyword_id}


@router.delete("/{keyword_id}")
async def keywords_delete(keyword_id: int):
    """Delete a custom keyword."""
    deleted = await delete_keyword(keyword_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Keyword #{keyword_id} not found")
    return {"deleted": True, "keyword_id": keyword_id}