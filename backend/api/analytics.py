"""
IndiaPix Metadata Automation System — Analytics API Endpoints
Dashboard statistics: processing volume, success rates, top categories/locations.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query

from db.job_repository import get_job_stats, get_daily_stats, get_top_categories, get_top_locations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
async def analytics_summary(
    period: str = Query("all", description="Period: today, week, month, all"),
):
    """
    Get aggregate processing statistics for the dashboard.
    
    Returns counts of total, completed, failed jobs and total frames extracted.
    """
    stats = await get_job_stats(period)
    return stats


@router.get("/daily")
async def analytics_daily(
    days: int = Query(30, description="Number of days to look back", ge=1, le=365),
):
    """
    Get per-day processing counts for charts.
    Returns a time series of total, completed, and failed jobs per day.
    """
    data = await get_daily_stats(days)
    return {"days": days, "data": data}


@router.get("/categories")
async def analytics_categories(
    limit: int = Query(10, description="Number of top categories", ge=1, le=50),
):
    """Get the most frequently assigned categories."""
    data = await get_top_categories(limit)
    return {"categories": data}


@router.get("/locations")
async def analytics_locations(
    limit: int = Query(10, description="Number of top locations", ge=1, le=50),
):
    """Get the most frequently detected locations."""
    data = await get_top_locations(limit)
    return {"locations": data}


@router.get("/all")
async def analytics_all(
    days: int = Query(30, description="Days for daily stats", ge=1, le=365),
    category_limit: int = Query(10, description="Number of top categories", ge=1, le=50),
    location_limit: int = Query(10, description="Number of top locations", ge=1, le=50),
):
    """
    Get all analytics data in one call (for the analytics dashboard).
    Combines summary, daily, categories, and locations.
    """
    summary_all = await get_job_stats("all")
    summary_today = await get_job_stats("today")
    summary_week = await get_job_stats("week")
    summary_month = await get_job_stats("month")
    daily = await get_daily_stats(days)
    categories = await get_top_categories(category_limit)
    locations = await get_top_locations(location_limit)

    return {
        "summary": {
            "all": summary_all,
            "today": summary_today,
            "week": summary_week,
            "month": summary_month,
        },
        "daily": daily,
        "top_categories": categories,
        "top_locations": locations,
    }