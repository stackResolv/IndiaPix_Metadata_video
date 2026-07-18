"""
IndiaPix Metadata Automation System — Platform Export Presets
CSV format variants for different stock platforms.
Each platform has its own column mapping, naming conventions, and format rules.
"""

import csv
import io
import logging
from typing import Optional

from models.metadata import MetadataResult
from services.csv_service import CSV_COLUMNS as BASE_COLUMNS

logger = logging.getLogger(__name__)


# ── Platform Definitions ────────────────────────────────────────────────────

class PlatformPreset:
    """Defines the CSV format for a specific stock platform."""
    
    def __init__(
        self,
        name: str,
        columns: list[str],
        column_labels: Optional[dict[str, str]] = None,
        separator: str = ",",
        quote_all: bool = True,
        include_bom: bool = True,
        include_tech_props: bool = True,
    ):
        self.name = name
        self.columns = columns
        self.column_labels = column_labels or {}
        self.separator = separator
        self.quote_all = quote_all
        self.include_bom = include_bom
        self.include_tech_props = include_tech_props


# ── Platform Presets ────────────────────────────────────────────────────────

PLATFORMS = {
    "getty": PlatformPreset(
        name="Getty Images",
        columns=[
            "filename", "title", "caption", "description", "keywords",
            "category", "editorial", "location", "shot_type", "mood",
            "date_created", "duration_seconds", "frame_rate",
            "resolution", "aspect_ratio", "bitrate_kbps", "audio",
        ],
        column_labels={},
        include_tech_props=True,
    ),
    "adobe": PlatformPreset(
        name="Adobe Stock",
        columns=[
            "filename", "title", "description", "keywords",
            "category", "editorial", "location",
            "date_created",
        ],
        column_labels={
            "title": "Title",
            "description": "Description",
            "keywords": "Keywords",
            "category": "Category",
            "editorial": "Editorial",
            "location": "Location",
        },
        include_tech_props=False,
    ),
    "shutterstock": PlatformPreset(
        name="Shutterstock",
        columns=[
            "filename", "title", "description", "keywords",
            "category", "editorial", "location",
        ],
        column_labels={
            "title": "Title",
            "description": "Description",
            "keywords": "Keywords",
            "category": "Category",
            "editorial": "Is Editorial",
            "location": "Location",
        },
        include_tech_props=False,
    ),
    "pond5": PlatformPreset(
        name="Pond5",
        columns=[
            "filename", "title", "description", "keywords",
            "category", "editorial", "location", "shot_type", "mood",
        ],
        column_labels={
            "title": "Title",
            "description": "Description",
            "keywords": "Tags",
            "category": "Category",
            "editorial": "Editorial",
            "location": "Location",
        },
        include_tech_props=False,
    ),
}


def get_available_platforms() -> list[dict]:
    """Return list of available platform presets."""
    return [
        {"id": pid, "name": platform.name, "columns": platform.columns}
        for pid, platform in PLATFORMS.items()
    ]


def generate_platform_csv(
    rows: list[dict],
    platform_id: str = "getty",
) -> str:
    """
    Generate CSV in the format required by a specific platform.
    
    Args:
        rows: List of row dictionaries with keys matching the full column set.
        platform_id: One of "getty", "adobe", "shutterstock", "pond5".
    
    Returns:
        CSV content as a string in the platform's format.
    """
    preset = PLATFORMS.get(platform_id)
    if not preset:
        logger.warning(f"Unknown platform '{platform_id}', falling back to 'getty'")
        preset = PLATFORMS["getty"]

    output = io.StringIO()

    # Write UTF-8 BOM for Excel compatibility
    if preset.include_bom:
        output.write("\ufeff")

    # Determine columns for this platform
    if preset.include_tech_props:
        columns = preset.columns
    else:
        # Only include non-technical columns
        tech_cols = {
            "date_created", "duration_seconds", "frame_rate",
            "resolution", "aspect_ratio", "bitrate_kbps", "audio",
        }
        columns = [c for c in preset.columns if c not in tech_cols]

    # Use platform-specific column labels if provided
    labels = [preset.column_labels.get(c, c) for c in columns]

    writer = csv.DictWriter(
        output,
        fieldnames=columns,
        extrasaction="ignore",
        quoting=csv.QUOTE_ALL if preset.quote_all else csv.QUOTE_NONNUMERIC,
        delimiter=preset.separator,
        lineterminator="\n",
    )

    # Write header with platform-specific labels
    writer.writerow(dict(zip(columns, labels)))

    for row in rows:
        writer.writerow(row)

    return output.getvalue()


def generate_single_platform_csv(
    filename: str,
    metadata: MetadataResult,
    video_properties: Optional[dict] = None,
    platform_id: str = "getty",
) -> str:
    """
    Generate a CSV for a single file in the specified platform format.
    
    Args:
        filename: Original file name.
        metadata: The MetadataResult.
        video_properties: Optional dict of video technical properties.
        platform_id: Target platform preset.
    
    Returns:
        CSV content as a string.
    """
    from services.csv_service import generate_csv_row

    row = generate_csv_row(filename, metadata, video_properties)
    return generate_platform_csv([row], platform_id)