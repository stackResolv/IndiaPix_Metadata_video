"""
IndiaPix Metadata Automation System — Storage Service
Manages uploaded files and their original filename metadata.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional, List

from config import settings

logger = logging.getLogger(__name__)

UPLOAD_META_SUFFIX = ".meta.json"


def save_upload_meta(upload_id: str, original_filename: str):
    """Save original filename metadata alongside the uploaded file."""
    meta_path = settings.upload_path / f"{upload_id}{UPLOAD_META_SUFFIX}"
    with open(meta_path, "w") as f:
        json.dump({"upload_id": upload_id, "original_filename": original_filename}, f)
    logger.debug(f"Saved upload meta: {upload_id} -> {original_filename}")


def get_original_filename(upload_id: str) -> Optional[str]:
    """Retrieve the original filename from the sidecar file."""
    meta_path = settings.upload_path / f"{upload_id}{UPLOAD_META_SUFFIX}"
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                data = json.load(f)
                return data.get("original_filename")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to read upload meta for {upload_id}: {e}")
    return None


def find_upload_file(upload_id: str) -> Optional[Path]:
    """Find a stored upload file by its upload_id (excluding meta sidecars)."""
    upload_dir = settings.upload_path
    if not upload_dir.exists():
        return None

    for f in upload_dir.iterdir():
        if f.is_file() and f.name.startswith(upload_id) and not f.name.endswith(UPLOAD_META_SUFFIX):
            return f
    return None


def clear_upload(upload_id: str):
    """Delete an uploaded file and its metadata sidecar."""
    upload_file = find_upload_file(upload_id)
    if upload_file and upload_file.exists():
        upload_file.unlink()
        logger.debug(f"Deleted upload file: {upload_file}")

    meta_path = settings.upload_path / f"{upload_id}{UPLOAD_META_SUFFIX}"
    if meta_path.exists():
        meta_path.unlink()
        logger.debug(f"Deleted upload meta: {meta_path}")

def list_stale_uploads() -> List[str]:
    """
    List upload IDs that are older than UPLOAD_TTL_HOURS.
    
    Returns a list of upload_ids whose files have exceeded the TTL.
    """
    ttl_seconds = settings.upload_ttl_hours * 3600
    now = time.time()
    stale_ids = []

    upload_dir = settings.upload_path
    if not upload_dir.exists():
        return stale_ids

    seen_ids = set()
    for f in upload_dir.iterdir():
        if not f.is_file():
            continue
        if f.name.endswith(UPLOAD_META_SUFFIX):
            continue

        name_parts = f.name.rsplit(".", 1)
        if len(name_parts) != 2:
            continue
        upload_id = name_parts[0]

        if upload_id in seen_ids:
            continue
        seen_ids.add(upload_id)

        file_age = now - f.stat().st_mtime
        if file_age > ttl_seconds:
            stale_ids.append(upload_id)

    logger.info(f"Found {len(stale_ids)} stale upload(s) older than {settings.upload_ttl_hours}h")
    return stale_ids


def cleanup_stale_uploads() -> int:
    """
    Delete all upload files and their meta sidecars that are older than TTL.
    
    Returns:
        Number of stale uploads cleaned up.
    """
    stale_ids = list_stale_uploads()
    for upload_id in stale_ids:
        clear_upload(upload_id)
    if stale_ids:
        logger.info(f"Cleaned up {len(stale_ids)} stale upload(s)")
    return len(stale_ids)
