"""
IndiaPix Metadata Automation System — Storage Service
Manages uploaded files and their original filename metadata.
"""

import json
import logging
from pathlib import Path
from typing import Optional

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