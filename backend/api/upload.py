"""
IndiaPix Metadata Automation System — Upload API Endpoints
Handles file upload, validation, and duration detection.
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from config import settings
from services.ffmpeg_service import get_video_duration, get_frame_count, get_video_properties
from services.storage_service import save_upload_meta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a video or image file.
    
    Validates the file extension and saves to temporary storage.
    For videos, also detects duration and calculates frame count.
    
    Returns:
        Dict with upload_id, original filename, duration_seconds (video only),
        frame_count (video only), and is_video flag.
    """
    # Validate file extension
    original_name = file.filename or "unknown"
    ext = Path(original_name).suffix.lower()
    
    if ext not in settings.all_allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. "
                   f"Supported types: {', '.join(settings.all_allowed_extensions)}",
        )
    
    # Generate unique ID to avoid filename collisions
    upload_id = str(uuid.uuid4())
    safe_filename = f"{upload_id}{ext}"
    upload_path = settings.upload_path / safe_filename
    
    # Save file to disk
    try:
        content = await file.read()
        
        # Check file size (2000 MB limit)
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB.",
            )
        
        with open(upload_path, "wb") as f:
            f.write(content)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")
    
    # Save original filename sidecar (so metadata endpoint can read it back)
    save_upload_meta(upload_id, original_name)
    
    is_video = ext in settings.allowed_video_extensions
    file_type = "video" if is_video else "image"
    result = {
        "upload_id": upload_id,
        "filename": original_name,  # ← Original filename preserved
        "stored_path": str(upload_path),
        "is_video": is_video,
        "file_size_bytes": len(content),
    }
    
    # For videos, detect duration and extract comprehensive properties
    if is_video:
        try:
            duration = get_video_duration(str(upload_path))
            frame_count = get_frame_count(duration)
            result["duration_seconds"] = round(duration, 1)
            result["duration_display"] = _format_duration(duration)
            result["frame_count"] = frame_count
            
            # Extract additional video properties
            props = get_video_properties(str(upload_path))
            result["date_created"] = props.get("date_created")
            result["frame_rate"] = props.get("frame_rate")
            result["resolution"] = props.get("resolution")
            result["aspect_ratio"] = props.get("aspect_ratio")
            result["bitrate_kbps"] = props.get("bitrate_kbps")
            result["audio"] = props.get("audio")
        except Exception as e:
            logger.warning(f"Could not probe video properties (may be corrupt): {e}")
            result["duration_seconds"] = None
            result["frame_count"] = None
            result["date_created"] = None
            result["frame_rate"] = None
            result["resolution"] = None
            result["aspect_ratio"] = None
            result["bitrate_kbps"] = None
            result["audio"] = None
    
    logger.info(
        f"Upload successful: {original_name} ({file_type}, "
        f"{(len(content) / (1024 * 1024)):.1f} MB, "
        f"id={upload_id})"
    )
    
    return result


def _format_duration(seconds: float) -> str:
    """Format duration for display (e.g., '2m 34s' or '1h 15m')."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"