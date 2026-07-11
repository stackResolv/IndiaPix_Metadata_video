"""
IndiaPix Metadata Automation System — Metadata Generation API Endpoints
Handles frame extraction, AI API calls, and returning metadata.
Supports both Claude (Anthropic) and GPT-4o (OpenAI).
"""

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import settings
from services.ffmpeg_service import extract_frames, get_video_duration, get_frame_count, get_video_properties
from services.claude_service import generate_metadata as claude_generate, ClaudeAPIError
from services.openai_service import generate_metadata as openai_generate, OpenAIAPIError
from services.csv_service import generate_csv_row, CSV_COLUMNS
from services.storage_service import (
    find_upload_file,
    get_original_filename,
    clear_upload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


@router.post("/generate")
async def generate_metadata_endpoint(
    upload_id: str,
    description: str = "",
    provider: str = "",
):
    """
    Generate metadata for a previously uploaded file.

    Steps:
    1. Locate the uploaded file
    2. If video: detect duration, calculate frame count, extract frames via FFmpeg
    3. Send frames + prompt to selected AI provider
    4. Return parsed metadata

    Args:
        upload_id: The upload_id returned from the upload endpoint.
        description: Optional operator description/context.
        provider: AI provider to use — "claude", "openai", or "" for default.

    Returns:
        Dict with job_id, filename (original), metadata, provider, frames_extracted, etc.
    """
    # Determine which AI provider to use
    ai_provider = (provider or settings.default_provider).lower()
    if ai_provider not in ("claude", "openai"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported AI provider '{provider}'. Use 'claude' or 'openai'.",
        )

    # Find the stored file for this upload_id
    upload_path = find_upload_file(upload_id)
    if not upload_path:
        raise HTTPException(
            status_code=404,
            detail=f"Upload {upload_id} not found. Please upload the file first.",
        )

    # Validate file is still present and readable
    if not upload_path.exists() or not upload_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Uploaded file {upload_id} is no longer available on disk.",
        )
    if upload_path.stat().st_size == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file {upload_id} appears to be empty (0 bytes).",
        )

    # Use the original uploaded filename (not the UUID filename on disk)
    original_filename = get_original_filename(upload_id) or upload_path.name
    is_video = upload_path.suffix.lower() in settings.allowed_video_extensions
    job_id = str(uuid.uuid4())

    try:
        video_properties = {}
        frames_attempted = 0
        if is_video:
            logger.info(f"Processing video: {original_filename} using {ai_provider}")

            duration = get_video_duration(str(upload_path))
            frame_count = get_frame_count(duration)
            frames_attempted = frame_count
            
            # Extract comprehensive video properties
            try:
                video_properties = get_video_properties(str(upload_path))
            except Exception as e:
                logger.warning(f"Could not extract video properties: {e}")

            # Create temp directory for this job's frames
            frames_dir = settings.upload_path / f"frames_{job_id}"
            frames_dir.mkdir(parents=True, exist_ok=True)

            try:
                frame_paths = extract_frames(
                    str(upload_path),
                    frame_count,
                    str(frames_dir),
                    max_width=settings.frame_max_width,
                )

                if not frame_paths:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to extract any frames from the video.",
                    )

                failed_count = frame_count - len(frame_paths)
                if failed_count > 0:
                    logger.warning(
                        f"Partial frame extraction: {len(frame_paths)}/{frame_count} frames "
                        f"extracted ({failed_count} failed). "
                        f"Proceeding with {len(frame_paths)} frames."
                    )
                else:
                    logger.info(f"Extracted {len(frame_paths)}/{frame_count} frames")

                # Send to selected AI provider
                if ai_provider == "openai":
                    metadata = openai_generate(
                        frame_paths,
                        description=description,
                    )
                else:
                    metadata = claude_generate(
                        frame_paths,
                        description=description,
                    )

            finally:
                _cleanup_dir(frames_dir)
        else:
            logger.info(f"Processing image: {original_filename} using {ai_provider}")
            # For images, we send the image directly as a single frame
            # No FFmpeg extraction needed — just encode and send to AI
            # Create temp directory for this job's frame(s)
            frames_dir = settings.upload_path / f"frames_{job_id}"
            frames_dir.mkdir(parents=True, exist_ok=True)

            frames_attempted = 1
            frame_paths = []

            try:
                # For images, copy or use the uploaded file directly
                import shutil
                image_copy = frames_dir / f"frame_00{upload_path.suffix}"
                shutil.copy2(str(upload_path), str(image_copy))
                frame_paths.append(str(image_copy))

                # Send to selected AI provider
                if ai_provider == "openai":
                    metadata = openai_generate(
                        frame_paths,
                        description=description,
                    )
                else:
                    metadata = claude_generate(
                        frame_paths,
                        description=description,
                    )

            finally:
                _cleanup_dir(frames_dir)

            duration = None

        # Keep uploaded file for Regenerate — user clears explicitly
        # Write single-file CSV to disk immediately
        _write_single_csv(original_filename, metadata, video_properties if is_video else None)

        return {
            "job_id": job_id,
            "filename": original_filename,
            "provider": ai_provider,
            "metadata": metadata.model_dump(),
            "duration_seconds": round(duration, 1) if is_video else None,
            "frames_extracted": len(frame_paths),
            "video_properties": video_properties if is_video else None,
        }

    except ClaudeAPIError as e:
        logger.error(f"Claude API error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except OpenAIAPIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metadata generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate metadata: {str(e)}",
        )


@router.post("/clear")
async def clear_upload_endpoint(upload_id: str):
    """
    Delete an uploaded file and its metadata sidecar.
    Called when the user clicks "Process Next File" or "Clear & Reset".
    """
    clear_upload(upload_id)
    return {"status": "cleared", "upload_id": upload_id}



def _write_single_csv(filename: str, metadata, video_properties: dict = None):
    """Write a single file's metadata CSV to the results directory."""
    try:
        from datetime import datetime
        results_dir = settings.results_path
        results_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(filename).stem.replace(" ", "_")
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        csv_path = results_dir / f"{safe_name}_{now}.csv"
        row = generate_csv_row(filename, metadata, video_properties)
        import csv as csv_module
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv_module.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerow(row)
        logger.info(f"Saved single-file CSV: {csv_path.name}")
    except Exception as e:
        logger.warning(f"Failed to write single-file CSV: {e}")


def _cleanup_dir(dir_path: Path):
    """Remove a directory and its contents."""
    try:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            logger.debug(f"Cleaned up directory: {dir_path}")
    except Exception as e:
        logger.warning(f"Failed to clean up directory {dir_path}: {e}")