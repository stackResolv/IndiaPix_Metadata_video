"""
IndiaPix Metadata Automation System — Settings API Endpoints
Manage application settings, API keys, and configuration.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from services.settings_service import (
    get_all_settings,
    get_setting,
    set_setting,
    update_settings,
    delete_setting,
    get_api_key_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/")
async def settings_get_all():
    """Get all application settings."""
    return await get_all_settings()


@router.get("/keys/status")
async def settings_key_status():
    """Get API key configuration status."""
    return await get_api_key_status()


@router.get("/{key}")
async def settings_get(key: str):
    """Get a single setting by key."""
    value = await get_setting(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return {"key": key, "value": value}


@router.put("/{key}")
async def settings_update_single(key: str, request: Request):
    """Update a single setting."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    value = body.get("value")
    if value is None:
        raise HTTPException(status_code=400, detail="'value' field is required")

    await set_setting(key, str(value))
    return {"key": key, "value": str(value)}


@router.post("/bulk")
async def settings_update_bulk(request: Request):
    """Update multiple settings at once."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")

    # Convert all values to strings
    updates = {k: str(v) for k, v in body.items()}
    all_settings = await update_settings(updates)
    return all_settings


@router.delete("/{key}")
async def settings_delete(key: str):
    """Delete a setting."""
    deleted = await delete_setting(key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return {"deleted": True, "key": key}