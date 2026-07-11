"""
IndiaPix Metadata Automation System — Pydantic Models
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class KeywordCategories(BaseModel):
    """Keywords organised by the 6 mandatory categories."""
    people: list[str] = Field(default_factory=list, description="People & Demographics (5-8)")
    action: list[str] = Field(default_factory=list, description="Action & Activity (5-8)")
    location: list[str] = Field(default_factory=list, description="Location & Geography (5-8)")
    setting: list[str] = Field(default_factory=list, description="Setting & Environment (5-7)")
    technical: list[str] = Field(default_factory=list, description="Technical & Shot Type (3-5)")
    conceptual: list[str] = Field(default_factory=list, description="Conceptual & Thematic (8-12)")


class MetadataResult(BaseModel):
    """The structured metadata returned from AI API.
    
    Removed separate 'title' field. 'caption' is renamed to 'title' 
    and serves as the main headline (max 200 chars).
    """
    title: str = Field(..., max_length=200, description="One-sentence headline (was caption)")
    description: str = Field(..., max_length=500)
    keywords: list[str] = Field(..., min_length=1)
    category: str = Field(default="")
    location: str = Field(default="Unknown")
    mood: str = Field(default="")
    shotType: str = Field(default="")
    editorial: bool = Field(default=False)
    keywordCategories: KeywordCategories = Field(default_factory=KeywordCategories)

    def flatten_keywords(self) -> str:
        """Return all keywords as a comma-separated string (for CSV).
        
        Deduplicates singular/plural variants — prefers singular form.
        Skips duplicate meaning keywords like 'cricketer' vs 'cricketers'.
        """
        seen_stems = set()
        unique = []
        # Common singular/plural mapping for deduplication
        import re
        
        def normalize(word: str) -> str:
            """Reduce a word to its singular stem for comparison."""
            w = word.strip().lower()
            # Handle common English plurals
            if w.endswith('ies') and len(w) > 4:
                return w[:-3] + 'y'
            if w.endswith('ves') and len(w) > 4:
                return w[:-3] + 'f'
            if w.endswith('es') and w[-4:-3] not in 'aeiou':
                return w[:-2]
            if w.endswith('s') and not w.endswith('ss') and len(w) > 3:
                return w[:-1]
            return w
        
        for kw in self.keywords:
            stem = normalize(kw)
            if stem not in seen_stems:
                seen_stems.add(stem)
                unique.append(kw.strip())
        return ", ".join(unique)


# ── API Request / Response Models ──────────────────────────────────────────

class GenerateRequest(BaseModel):
    """Request to generate metadata for a file."""
    filename: str
    description: str = Field(default="", max_length=500)


class GenerateResponse(BaseModel):
    """Response after metadata generation."""
    job_id: str
    filename: str
    metadata: MetadataResult
    duration_seconds: Optional[float] = None
    frames_extracted: int = 0


class ExportRequest(BaseModel):
    """Request to export metadata as CSV."""
    job_id: str
    filename: str
    metadata: MetadataResult
    platform: str = Field(default="getty", pattern="^(getty|adobe|shutterstock|pond5)$")


class ExportResponse(BaseModel):
    """Response containing CSV content."""
    csv_content: str
    filename: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    code: str = "UNKNOWN_ERROR"