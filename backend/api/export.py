"""
IndiaPix Metadata Automation System — CSV Export API Endpoint
Handles CSV generation and download.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from config import settings
from models.metadata import MetadataResult
from services.csv_service import export_single_csv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/csv")
async def export_csv(request: Request):
    """
    Export metadata as a CSV file.
    
    Accepts metadata in the same format returned by the generate endpoint,
    validates it, and returns a downloadable CSV file.
    
    Request body:
    {
        "filename": "example.mp4",
        "metadata": { ... metadata object from generate endpoint ... }
    }
    """
    # Read raw body to enforce size limit
    try:
        body = await request.body()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read request body: {str(e)}")
    
    if len(body) > settings.max_export_body_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Request body too large. Maximum size is {settings.max_export_body_bytes / 1024 / 1024:.0f}MB.",
        )
    
    # Parse JSON
    try:
        import json
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in request body: {str(e)}")
    
    filename = data.get("filename", "export.csv")
    metadata_dict = data.get("metadata")
    
    if not metadata_dict:
        raise HTTPException(status_code=400, detail="Metadata is required")
    
    try:
        # Rebuild MetadataResult from the dictionary
        metadata = MetadataResult(**metadata_dict)
    except Exception as e:
        logger.warning(f"Invalid metadata in export request: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metadata: {str(e)}",
        )
    
    # Extract video_properties if provided
    video_properties = data.get("video_properties")
    
    # Generate CSV
    try:
        csv_content = export_single_csv(filename, metadata, video_properties)
    except Exception as e:
        logger.error(f"CSV generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate CSV: {str(e)}")
    
    # Return as downloadable file
    csv_filename = Path(filename).stem + "_metadata.csv"
    
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{csv_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
