"""
IndiaPix Metadata Automation System — Job History API Endpoints
Search, view, re-export, and delete past jobs.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from db.job_repository import (
    get_job,
    search_jobs,
    delete_job,
    JobHistoryRecord,
)
from services.csv_service import generate_csv_row, generate_csv
from services.presets import generate_platform_csv, get_available_platforms
from services.custom_keywords import get_merged_keywords
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/search")
async def history_search(
    query: str = Query("", description="Search query for filename or keywords"),
    status: Optional[str] = Query(None, description="Filter by status: completed or failed"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    batch_id: Optional[str] = Query(None, description="Filter by batch ID"),
    limit: int = Query(50, description="Results per page", ge=1, le=200),
    offset: int = Query(0, description="Paginated offset", ge=0),
):
    """
    Search job history with filters and full-text search.
    Supports searching by filename, keywords, or any metadata field.
    """
    records, total = await search_jobs(
        query=query,
        status_filter=status,
        date_from=date_from,
        date_to=date_to,
        batch_id=batch_id,
        limit=limit,
        offset=offset,
    )
    return {
        "results": [r.to_dict() for r in records],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{job_id}")
async def history_get(job_id: int):
    """Get a single job record by ID."""
    record = await get_job(job_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found")
    return record.to_dict()


@router.delete("/{job_id}")
async def history_delete(job_id: int):
    """Delete a job record by ID."""
    deleted = await delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found")
    return {"deleted": True, "job_id": job_id}


@router.post("/export/{job_id}")
async def history_export(job_id: int, request: Request):
    """
    Re-export a single job's metadata as CSV without reprocessing.
    
    Optionally specify platform in request body:
    {"platform": "getty"}  (default: "getty")
    """
    record = await get_job(job_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found")

    if record.status != "completed" or not record.metadata_json:
        raise HTTPException(
            status_code=400,
            detail=f"Job #{job_id} has no completed metadata to export",
        )

    metadata = record.get_metadata()
    if not metadata:
        raise HTTPException(status_code=500, detail="Failed to parse stored metadata")

    video_properties = record.get_video_properties()

    # Get platform from request body
    platform = "getty"
    try:
        body = await request.json()
        platform = body.get("platform", "getty")
    except Exception:
        pass

    # Merge custom keywords
    try:
        merged_keywords = await get_merged_keywords(metadata)
        metadata.keywords = merged_keywords
    except Exception as e:
        logger.warning(f"Failed to merge custom keywords for export: {e}")

    # Generate platform-specific CSV
    row = generate_csv_row(record.filename, metadata, video_properties)
    csv_content = generate_platform_csv([row], platform)

    csv_filename = f"{record.filename.rsplit('.', 1)[0]}_metadata_{platform}.csv"

    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{csv_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/export-batch")
async def history_batch_export(request: Request):
    """
    Export multiple job records as a single CSV.
    
    Request body:
    {"job_ids": [1, 2, 3], "platform": "getty"}
    """
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    job_ids = body.get("job_ids", [])
    if not job_ids:
        raise HTTPException(status_code=400, detail="job_ids list is required")

    platform = body.get("platform", "getty")

    rows = []
    filenames = []
    for jid in job_ids:
        record = await get_job(jid)
        if not record or record.status != "completed" or not record.metadata_json:
            continue
        metadata = record.get_metadata()
        video_properties = record.get_video_properties()
        if metadata:
            # Merge custom keywords
            try:
                merged_keywords = await get_merged_keywords(metadata)
                metadata.keywords = merged_keywords
            except Exception:
                pass
            rows.append(generate_csv_row(record.filename, metadata, video_properties))
            filenames.append(record.filename)

    if not rows:
        raise HTTPException(status_code=400, detail="No completed jobs found for the given IDs")

    csv_content = generate_platform_csv(rows, platform)
    csv_filename = f"batch_export_{len(rows)}files_{platform}.csv"

    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{csv_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/platforms/list")
async def list_platforms():
    """List all available platform export presets."""
    return {"platforms": get_available_platforms()}
