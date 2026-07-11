"""
IndiaPix Metadata Automation System — Batch Processing API Endpoints
Handles batch upload, processing queue, progress tracking, and batch CSV export.
"""

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from config import settings
from services.batch_service import (
    create_batch,
    get_batch,
    start_batch_processing,
    Batch,
)
from services.csv_service import export_batch_csv
from services.storage_service import find_upload_file, clear_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["batch"])


@router.post("/start")
async def batch_start(request: Request):
    """
    Start a new batch processing job.
    
    Request body:
    {
        "upload_ids": ["uuid1", "uuid2", ...],
        "descriptions": { "uuid1": "optional desc", ... },  # optional
        "provider": "claude" | "openai" | ""  # optional
    }
    
    Returns:
        The batch object with batch_id and initial job statuses.
        The batch starts processing in the background immediately.
    """
    try:
        body = await request.json()
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    upload_ids = body.get("upload_ids", [])
    if not upload_ids:
        raise HTTPException(status_code=400, detail="upload_ids list is required and cannot be empty")
    
    if len(upload_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 files per batch")

    descriptions = body.get("descriptions", {})
    provider = body.get("provider", "")

    # Validate all upload_ids exist
    for uid in upload_ids:
        upload_path = find_upload_file(uid)
        if not upload_path:
            raise HTTPException(
                status_code=404,
                detail=f"Upload {uid} not found. Please upload the file first.",
            )

    # Create batch
    batch = await create_batch(upload_ids, descriptions, provider)
    
    # Start processing in the background
    asyncio.create_task(start_batch_processing(batch.batch_id))

    logger.info(
        f"Batch {batch.batch_id} started with {len(upload_ids)} files"
    )
    
    return batch.to_dict()


@router.get("/status/{batch_id}")
async def batch_status(batch_id: str):
    """
    Get the current status of a batch processing job.
    Used by the frontend to poll for progress updates.
    
    Args:
        batch_id: The batch ID returned from /api/batch/start.
    
    Returns:
        Batch object with current job statuses.
    """
    batch = await get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    
    return batch.to_dict()


@router.post("/export-csv")
async def batch_export_csv(request: Request):
    """
    Export the pre-built batch CSV file.
    The CSV is already on disk — each job's row was appended as it completed.
    
    Request body:
    {
        "batch_id": "batch-uuid"
    }
    
    Returns:
        CSV file download.
    """
    try:
        body = await request.json()
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    batch_id = body.get("batch_id")
    if not batch_id:
        raise HTTPException(status_code=400, detail="batch_id is required")

    batch = await get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    if not batch.csv_path or not batch.csv_path.exists():
        # Fallback: generate CSV from in-memory data if file doesn't exist
        entries = []
        for job in batch.jobs:
            if job.status == "completed" and job.metadata:
                entries.append((job.filename, job.metadata, job.video_properties))
        if not entries:
            raise HTTPException(
                status_code=400,
                detail="No completed jobs found in this batch.",
            )
        try:
            csv_content = export_batch_csv(entries)
        except Exception as e:
            logger.error(f"Batch CSV export failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to generate CSV: {str(e)}")
        csv_filename = f"batch_{batch_id[:8]}_metadata.csv"
        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{csv_filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )

    # Serve the pre-built CSV from disk
    try:
        csv_content = batch.csv_path.read_text(encoding="utf-8-sig")
    except Exception as e:
        logger.error(f"Failed to read batch CSV from disk: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read CSV file: {str(e)}")

    csv_filename = batch.csv_path.name

    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{csv_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/retry/{batch_id}")
async def batch_retry_failed(batch_id: str):
    """
    Retry all failed jobs in a batch.
    
    Args:
        batch_id: The batch ID to retry failed jobs for.
    
    Returns:
        Updated batch object.
    """
    batch = await get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    # Reset failed jobs to pending
    retry_count = 0
    for job in batch.jobs:
        if job.status == "failed":
            job.status = "pending"
            job.error_message = None
            job.error_type = ""
            retry_count += 1

    if retry_count == 0:
        raise HTTPException(status_code=400, detail="No failed jobs to retry")

    logger.info(f"Retrying {retry_count} failed jobs in batch {batch_id}")
    
    # Re-start processing in background
    asyncio.create_task(start_batch_processing(batch_id))

    return batch.to_dict()

@router.post("/cleanup/{batch_id}")
async def batch_cleanup(batch_id: str):
    """
    Clean up all uploaded files associated with a batch.
    
    Args:
        batch_id: The batch ID to clean up files for.
    
    Returns:
        Dict with count of cleaned files.
    """
    batch = await get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    cleaned = 0
    for job in batch.jobs:
        try:
            clear_upload(job.upload_id)
            cleaned += 1
        except Exception as e:
            logger.warning(f"Cleanup failed for upload {job.upload_id}: {e}")

    logger.info(f"Cleaned up {cleaned} upload(s) for batch {batch_id}")
    return {"batch_id": batch_id, "cleaned_count": cleaned}
