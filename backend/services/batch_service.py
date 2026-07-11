"""
IndiaPix Metadata Automation System — Batch Processing Service
Manages concurrent batch job queues with per-file status tracking.
Supports mixed video and image files in a single batch.

IMPORTANT: All blocking work (FFmpeg, API calls) runs in a thread pool
via asyncio.to_thread() to keep the event loop free for status polling.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import settings
from models.metadata import MetadataResult
from services.ffmpeg_service import (
    extract_frames,
    extract_frames_at_scenes,
    get_video_duration,
    get_frame_count,
    get_video_properties,
)
from services.claude_service import generate_metadata as claude_generate, ClaudeAPIError
from services.openai_service import generate_metadata as openai_generate, OpenAIAPIError
from services.csv_service import generate_csv_row, CSV_COLUMNS
from services.storage_service import find_upload_file, get_original_filename, clear_upload

logger = logging.getLogger(__name__)


# ── Batch Job Status Constants ─────────────────────────────────────────────

class JobStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Batch State ────────────────────────────────────────────────────────────

class BatchJob:
    """Represents a single file within a batch."""
    def __init__(
        self,
        upload_id: str,
        filename: str,
        description: str = "",
        provider: str = "",
    ):
        self.upload_id = upload_id
        self.filename = filename
        self.description = description
        self.provider = provider
        self.status = JobStatus.PENDING
        self.metadata: Optional[MetadataResult] = None
        self.video_properties: Optional[dict] = None
        self.frames_extracted: int = 0
        self.duration_seconds: Optional[float] = None
        self.error_message: Optional[str] = None
        self.error_type: str = ""

    def to_dict(self) -> dict:
        """Serialize job state for API responses."""
        result = {
            "upload_id": self.upload_id,
            "filename": self.filename,
            "status": self.status,
            "frames_extracted": self.frames_extracted,
            "error_message": self.error_message,
            "error_type": self.error_type,
        }
        if self.metadata:
            result["metadata"] = self.metadata.model_dump()
        if self.video_properties:
            result["video_properties"] = self.video_properties
        if self.duration_seconds is not None:
            result["duration_seconds"] = self.duration_seconds
        return result


class Batch:
    """Represents a batch processing session."""
    def __init__(self, batch_id: str, jobs: list, csv_path: Optional[Path] = None):
        self.batch_id = batch_id
        self.jobs = jobs
        self.total_jobs = len(jobs)
        self.completed_count = 0
        self.failed_count = 0
        self.created_at = time.time()
        self.completed_at: Optional[float] = None
        self.is_running = False
        self.csv_path = csv_path  # Path to the progressive CSV on disk

    @property
    def is_complete(self) -> bool:
        return self.completed_count + self.failed_count == self.total_jobs

    def to_dict(self) -> dict:
        """Serialize batch state for API responses."""
        result = {
            "batch_id": self.batch_id,
            "total_jobs": self.total_jobs,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "is_running": self.is_running,
            "is_complete": self.is_complete,
            "jobs": [job.to_dict() for job in self.jobs],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }
        if self.csv_path:
            result["csv_path"] = str(self.csv_path.name)
        return result


# ── In-Memory Batch Registry ──────────────────────────────────────────────

_batches: dict[str, Batch] = {}
_batch_lock = asyncio.Lock()


def _generate_batch_filename() -> str:
    """Generate a human-readable batch CSV filename with date and time."""
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"batch_{now}.csv"


async def create_batch(
    upload_ids: list[str],
    descriptions: Optional[dict[str, str]] = None,
    provider: str = "",
) -> Batch:
    """
    Create a new batch from a list of upload IDs.
    
    Args:
        upload_ids: List of upload IDs to process.
        descriptions: Optional mapping of upload_id -> description.
        provider: AI provider to use ("claude", "openai", or "" for default).
    
    Returns:
        The created Batch object with a CSV file created on disk.
    """
    batch_id = str(uuid.uuid4())
    jobs = []

    for upload_id in upload_ids:
        upload_path = find_upload_file(upload_id)
        original_filename = get_original_filename(upload_id) or (upload_path.name if upload_path else "unknown")
        desc = (descriptions or {}).get(upload_id, "")
        jobs.append(BatchJob(upload_id, original_filename, desc, provider))

    # Create the results directory and an empty CSV with header
    results_dir = settings.results_path
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_filename = _generate_batch_filename()
    csv_path = results_dir / csv_filename

    # Write CSV header
    import csv as csv_module
    import io
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv_module.writer(f)
        writer.writerow(CSV_COLUMNS)

    logger.info(f"Created batch CSV: {csv_path.name}")

    batch = Batch(batch_id, jobs, csv_path=csv_path)
    async with _batch_lock:
        _batches[batch_id] = batch

    logger.info(f"Created batch {batch_id} with {len(jobs)} jobs, CSV: {csv_filename}")
    return batch


async def get_batch(batch_id: str) -> Optional[Batch]:
    """Get a batch by its ID."""
    async with _batch_lock:
        return _batches.get(batch_id)


async def start_batch_processing(batch_id: str):
    """
    Start processing all jobs in a batch sequentially in a thread pool.
    Each job's metadata is appended to the batch CSV immediately after completion.
    """
    async with _batch_lock:
        batch = _batches.get(batch_id)
        if not batch:
            logger.error(f"Batch {batch_id} not found for processing")
            return
        if batch.is_running:
            logger.warning(f"Batch {batch_id} is already running")
            return
        batch.is_running = True

    logger.info(f"Starting batch processing for {batch_id} ({batch.total_jobs} jobs)")

    for job in batch.jobs:
        if job.status == JobStatus.COMPLETED:
            continue

        job.status = JobStatus.PROCESSING
        await asyncio.sleep(0)

        try:
            await asyncio.to_thread(_process_single_job_sync, job)
            job.status = JobStatus.COMPLETED
            async with _batch_lock:
                batch.completed_count += 1

            # Append this job's row to the batch CSV on disk
            _append_job_to_csv(batch.csv_path, job)

            logger.info(f"Job completed: {job.filename} in batch {batch_id}")
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            async with _batch_lock:
                batch.failed_count += 1
            logger.error(f"Job failed: {job.filename} in batch {batch_id}: {e}")

        await asyncio.sleep(0)

    async with _batch_lock:
        batch.is_running = False
        batch.completed_at = time.time()

    # Clean up all uploaded files associated with this batch
    _cleanup_batch_uploads(batch)

    logger.info(
        f"Batch {batch_id} complete: "
        f"{batch.completed_count}/{batch.total_jobs} succeeded, "
        f"{batch.failed_count} failed"
    )


def _append_job_to_csv(csv_path: Optional[Path], job: BatchJob):
    """
    Append a single completed job's metadata as a row to the batch CSV.
    This runs synchronously in the thread pool.
    """
    if not csv_path or not job.metadata:
        return

    import csv as csv_module
    try:
        row = generate_csv_row(job.filename, job.metadata, job.video_properties)
        with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv_module.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writerow(row)
        logger.debug(f"Appended to batch CSV: {job.filename}")
    except Exception as e:
        logger.error(f"Failed to append to batch CSV: {e}")


def _process_single_job_sync(job: BatchJob):
    """
    Process a single job synchronously.
    This runs in a thread pool via asyncio.to_thread().
    All blocking calls (FFmpeg, API) are safe here.
    """
    upload_path = find_upload_file(job.upload_id)
    if not upload_path:
        raise FileNotFoundError(f"Upload {job.upload_id} not found")

    ai_provider = (job.provider or settings.default_provider).lower()
    is_video = upload_path.suffix.lower() in settings.allowed_video_extensions

    job_id = str(uuid.uuid4())
    frames_dir = settings.upload_path / f"batch_frames_{job_id}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    try:
        if is_video:
            duration = get_video_duration(str(upload_path))
            frame_count = get_frame_count(duration)
            job.duration_seconds = duration
            job.frames_extracted = frame_count

            try:
                job.video_properties = get_video_properties(str(upload_path))
            except Exception as e:
                logger.warning(f"Could not extract video properties for {job.filename}: {e}")

            if settings.scene_detection_enabled:
                frame_paths = extract_frames_at_scenes(
                    str(upload_path),
                    str(frames_dir),
                    max_width=settings.frame_max_width,
                    sensitivity=settings.scene_sensitivity,
                    max_frames=frame_count,
                )
            else:
                frame_paths = extract_frames(
                    str(upload_path),
                    frame_count,
                    str(frames_dir),
                    max_width=settings.frame_max_width,
                )

            if not frame_paths:
                raise RuntimeError("Failed to extract any frames from the video")

            if ai_provider == "openai":
                metadata = openai_generate(frame_paths, description=job.description)
            else:
                metadata = claude_generate(frame_paths, description=job.description)

            job.frames_extracted = len(frame_paths)
        else:
            import shutil
            image_copy = frames_dir / f"frame_00{upload_path.suffix}"
            shutil.copy2(str(upload_path), str(image_copy))
            frame_paths = [str(image_copy)]
            job.frames_extracted = 1

            if ai_provider == "openai":
                metadata = openai_generate(frame_paths, description=job.description)
            else:
                metadata = claude_generate(frame_paths, description=job.description)

        job.metadata = metadata

    finally:
        try:
            import shutil as sh
            if frames_dir.exists():
                sh.rmtree(frames_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up frames dir {frames_dir}: {e}")

def _cleanup_batch_uploads(batch: Batch):
    """
    Delete all uploaded files that were associated with a batch.
    Called automatically when the batch completes processing.
    """
    cleaned = 0
    for job in batch.jobs:
        try:
            clear_upload(job.upload_id)
            cleaned += 1
        except Exception as e:
            logger.warning(f"Failed to clean up upload {job.upload_id}: {e}")
    if cleaned > 0:
        logger.info(f"Cleaned up {cleaned} upload(s) for batch {batch.batch_id}")
