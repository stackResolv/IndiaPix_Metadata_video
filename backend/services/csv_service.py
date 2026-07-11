"""
IndiaPix Metadata Automation System — CSV Export Service
Generates CSV files compatible with stock platform bulk upload tools.
"""

import csv
import io
import logging
from typing import List

from models.metadata import MetadataResult

logger = logging.getLogger(__name__)


# Column definitions — stock platform metadata + video technical properties
# Order matters — this is the expected column order.
# Note: 'title' stores what was previously 'caption' (one-sentence headline)
CSV_COLUMNS = [
    "filename",
    "title",
    "description",
    "keywords",
    "category",
    "editorial",
    "location",
    "shot_type",
    "mood",
    # Video technical properties
    "date_created",
    "duration_seconds",
    "frame_rate",
    "resolution",
    "aspect_ratio",
    "bitrate_kbps",
    "audio",
]


def generate_csv_row(filename: str, metadata: MetadataResult, video_properties: dict = None) -> dict:
    """
    Generate a single CSV row as a dictionary.
    
    Args:
        filename: Original file name.
        metadata: The validated MetadataResult from Claude.
        video_properties: Optional dictionary of video technical properties.
    
    Returns:
        Dictionary mapping column names to values.
    """
    row = {
        "filename": filename,
        "title": metadata.title,
        "description": metadata.description,
        "keywords": metadata.flatten_keywords(),
        "category": metadata.category,
        "editorial": "Yes" if metadata.editorial else "No",
        "location": metadata.location,
        "shot_type": metadata.shotType,
        "mood": metadata.mood,
        "date_created": "",
        "duration_seconds": "",
        "frame_rate": "",
        "resolution": "",
        "aspect_ratio": "",
        "bitrate_kbps": "",
        "audio": "",
    }
    
    if video_properties:
        row["date_created"] = video_properties.get("date_created") or ""
        dur = video_properties.get("duration_seconds")
        if dur:
            import math
            # Round up to next whole second
            total_secs = int(math.ceil(dur))
            # Format as HH:MM:SS (e.g., "0:01:19 sec")
            hours = total_secs // 3600
            minutes = (total_secs % 3600) // 60
            seconds = total_secs % 60
            row["duration_seconds"] = f"{hours}:{minutes:02d}:{seconds:02d} sec"
        else:
            row["duration_seconds"] = ""
        row["frame_rate"] = video_properties.get("frame_rate") or ""
        row["resolution"] = video_properties.get("resolution") or ""
        row["aspect_ratio"] = video_properties.get("aspect_ratio") or ""
        bitrate = video_properties.get("bitrate_kbps")
        row["bitrate_kbps"] = str(bitrate) if bitrate else ""
        row["audio"] = video_properties.get("audio") or ""
    
    return row


def generate_csv(
    rows: List[dict],
    include_bom: bool = True,
) -> str:
    """
    Generate CSV content as a string.
    
    Args:
        rows: List of row dictionaries with keys matching CSV_COLUMNS.
        include_bom: Whether to include UTF-8 BOM for Excel compatibility.
    
    Returns:
        CSV content as a string.
    """
    output = io.StringIO()
    
    # Write UTF-8 BOM for Excel compatibility on Windows
    if include_bom:
        output.write("\ufeff")
    
    writer = csv.DictWriter(
        output,
        fieldnames=CSV_COLUMNS,
        quoting=csv.QUOTE_ALL,  # Quote all fields to handle commas in descriptions
        lineterminator="\n",
    )
    
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    
    return output.getvalue()


def export_single_csv(filename: str, metadata: MetadataResult, video_properties: dict = None) -> str:
    """
    Export a single file's metadata as CSV.
    
    Args:
        filename: Original file name.
        metadata: The validated MetadataResult.
        video_properties: Optional dictionary of video technical properties.
    
    Returns:
        CSV content as a string.
    """
    row = generate_csv_row(filename, metadata, video_properties)
    return generate_csv([row])


def export_batch_csv(entries: List[tuple]) -> str:
    """
    Export multiple files' metadata as a single CSV (for Phase 2 batch mode).
    
    Args:
        entries: List of (filename, metadata) or (filename, metadata, video_properties) tuples.
    
    Returns:
        CSV content as a string.
    """
    rows = []
    for entry in entries:
        if len(entry) == 3:
            filename, metadata, video_properties = entry
        else:
            filename, metadata = entry
            video_properties = None
        rows.append(generate_csv_row(filename, metadata, video_properties))
    return generate_csv(rows)
